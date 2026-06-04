#!/usr/bin/env python3
"""
Simulador de CLP — EH Brewing
Simula 8 panelas de armazenamento enviando leituras de temperatura para a API.
Suporta controle ativo (cooling / heating / idle) via consulta à API.
"""

import argparse
import logging
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

DEFAULT_SETPOINTS = {
    1: 15.0,
    2: 12.0,
    3: 18.0,
    4: 14.0,
    5: 16.0,
    6: 13.0,
    7: 17.0,
    8: 15.5,
}

CONTROL_TOLERANCE = 0.3


@dataclass
class TankSimulator:
    """Simula a dinâmica de temperatura de uma única panela."""

    tank_id: int
    default_setpoint: float
    noise_std: float = 0.3
    current_temp: float = field(init=False)

    def __post_init__(self):
        self.current_temp = self.default_setpoint + random.gauss(0, self.noise_std)

    def step(
        self,
        mode: str,
        setpoint: float,
        cooling_rate: float,
        heating_rate: float,
        fault_temp: Optional[float] = None,
    ) -> float:
        if fault_temp is not None:
            return round(fault_temp + random.gauss(0, 0.1), 2)

        near_setpoint = abs(self.current_temp - setpoint) <= CONTROL_TOLERANCE

        if near_setpoint:
            self.current_temp += random.gauss(0, 0.05)
        elif mode == "cooling":
            self.current_temp -= cooling_rate
            self.current_temp += random.gauss(0, 0.1)
        elif mode == "heating":
            self.current_temp += heating_rate
            self.current_temp += random.gauss(0, 0.1)
        else:
            self.current_temp = (
                0.95 * self.current_temp
                + 0.05 * self.default_setpoint
                + random.gauss(0, self.noise_std)
            )

        return round(self.current_temp, 2)


class CLPSimulator:
    """Gerencia o loop de simulação e comunicação com a API."""

    def __init__(
        self,
        api_url: str,
        interval: float,
        fault_tank: Optional[int],
        fault_temp: Optional[float],
        username: str,
        password: str,
        cooling_rate: float,
        heating_rate: float,
    ):
        self.api_url = api_url.rstrip("/")
        self.interval = interval
        self.fault_tank = fault_tank
        self.fault_temp = fault_temp
        self.username = username
        self.password = password
        self.cooling_rate = cooling_rate
        self.heating_rate = heating_rate

        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.running = True
        self.retry_delay = 1.0
        self.max_retry_delay = 30.0

        self.tanks = {i: TankSimulator(i, DEFAULT_SETPOINTS[i]) for i in range(1, 9)}

    # ------------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------------

    def _login(self) -> bool:
        try:
            response = self.session.post(
                f"{self.api_url}/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.session.headers.update(
                    {"Authorization": f"Bearer {self.access_token}"}
                )
                logging.info("Autenticado com sucesso.")
                return True

            logging.error(
                "Falha no login: HTTP %d — %s",
                response.status_code,
                response.text[:200],
            )
            return False

        except requests.RequestException as exc:
            logging.error("Erro de conexão no login: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Consulta de controle
    # ------------------------------------------------------------------

    def _get_control(self, tank_id: int) -> tuple[str, float]:
        """Retorna (mode, setpoint) para a panela. Usa idle e setpoint padrão em caso de erro."""
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/tanks/{tank_id}/control",
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("mode", "idle"), data.get("setpoint", DEFAULT_SETPOINTS[tank_id])

            if response.status_code == 401:
                logging.warning("Token expirado ao consultar controle — re-autenticando...")
                self.access_token = None

        except requests.RequestException as exc:
            logging.debug("Erro ao consultar controle panela %d: %s", tank_id, exc)

        return "idle", DEFAULT_SETPOINTS[tank_id]

    # ------------------------------------------------------------------
    # Envio de leitura
    # ------------------------------------------------------------------

    def _send_reading(self, tank_id: int, temperature: float) -> bool:
        payload = {
            "tank_id": tank_id,
            "temperature": temperature,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

        response = self.session.post(
            f"{self.api_url}/api/v1/readings",
            json=payload,
            timeout=10,
        )

        if response.status_code == 201:
            logging.debug("Panela %d: %.2f°C enviado.", tank_id, temperature)
            return True

        if response.status_code == 401:
            logging.warning("Token expirado — re-autenticando...")
            self.access_token = None
            return False

        if response.status_code == 404:
            logging.warning(
                "Panela %d não cadastrada na API (404). Execute o seed inicial.",
                tank_id,
            )
            return True

        logging.warning(
            "Panela %d: resposta inesperada HTTP %d.", tank_id, response.status_code
        )
        return True

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def run(self):
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logging.info(
            "Simulador iniciado | API: %s | Intervalo: %.1fs | Panelas: 1–8",
            self.api_url,
            self.interval,
        )
        logging.info(
            "Parâmetros de controle | cooling-rate: %.2f°C/ciclo | heating-rate: %.2f°C/ciclo",
            self.cooling_rate,
            self.heating_rate,
        )

        if self.fault_tank:
            logging.info(
                "Modo de falha ativo: panela %d → %.2f°C",
                self.fault_tank,
                self.fault_temp,
            )

        while self.running:
            if not self.access_token:
                if not self._login():
                    self._wait_retry("Login falhou")
                    continue
                self._reset_retry()

            cycle_ok = self._run_cycle()

            if cycle_ok:
                self._reset_retry()
                logging.info(
                    "Ciclo concluído — próxima leitura em %.1fs.", self.interval
                )
                self._interruptible_sleep(self.interval)
            else:
                self._wait_retry("Falha no ciclo")

    def _run_cycle(self) -> bool:
        for tank_id, tank in self.tanks.items():
            fault_temp = self.fault_temp if tank_id == self.fault_tank else None

            mode, setpoint = self._get_control(tank_id)
            if not self.access_token:
                return False

            temperature = tank.step(
                mode=mode,
                setpoint=setpoint,
                cooling_rate=self.cooling_rate,
                heating_rate=self.heating_rate,
                fault_temp=fault_temp,
            )

            logging.debug(
                "Panela %d | mode=%s | setpoint=%.1f°C | temp=%.2f°C",
                tank_id, mode, setpoint, temperature,
            )

            try:
                ok = self._send_reading(tank_id, temperature)
            except requests.RequestException as exc:
                logging.warning("Erro de rede ao enviar panela %d: %s", tank_id, exc)
                return False

            if not ok:
                return False

        return True

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _interruptible_sleep(self, seconds: float):
        elapsed = 0.0
        while self.running and elapsed < seconds:
            time.sleep(min(0.5, seconds - elapsed))
            elapsed += 0.5

    def _wait_retry(self, reason: str):
        logging.info("%s. Aguardando %.1fs antes de tentar novamente.", reason, self.retry_delay)
        self._interruptible_sleep(self.retry_delay)
        self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)

    def _reset_retry(self):
        self.retry_delay = 1.0

    def _handle_shutdown(self, signum, frame):
        logging.info("Sinal recebido — encerrando simulador...")
        self.running = False


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulador de CLP — EH Brewing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("SIMULATOR_API_URL", "http://localhost:8000"),
        help="URL base da API",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5")),
        metavar="SEGUNDOS",
        help="Intervalo entre ciclos de leitura",
    )
    parser.add_argument(
        "--fault-tank",
        type=int,
        default=None,
        choices=range(1, 9),
        metavar="[1-8]",
        help="Panela que receberá temperatura de falha",
    )
    parser.add_argument(
        "--fault-temp",
        type=float,
        default=None,
        metavar="GRAUS_C",
        help="Temperatura injetada na panela com falha",
    )
    parser.add_argument(
        "--cooling-rate",
        type=float,
        default=float(os.getenv("SIMULATOR_COOLING_RATE", "0.3")),
        metavar="GRAUS_C",
        help="Taxa de resfriamento por ciclo (°C/ciclo)",
    )
    parser.add_argument(
        "--heating-rate",
        type=float,
        default=float(os.getenv("SIMULATOR_HEATING_RATE", "0.2")),
        metavar="GRAUS_C",
        help="Taxa de aquecimento por ciclo (°C/ciclo)",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("SIMULATOR_USERNAME", "admin"),
        help="Usuário com role operador ou admin",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SIMULATOR_PASSWORD", "admin"),
        help="Senha do usuário",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log",
    )

    args = parser.parse_args()

    if args.fault_tank is not None and args.fault_temp is None:
        parser.error("--fault-tank requer --fault-temp")

    if args.fault_temp is not None and args.fault_tank is None:
        parser.error("--fault-temp requer --fault-tank")

    return args


def main():
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    simulator = CLPSimulator(
        api_url=args.api_url,
        interval=args.interval,
        fault_tank=args.fault_tank,
        fault_temp=args.fault_temp,
        username=args.username,
        password=args.password,
        cooling_rate=args.cooling_rate,
        heating_rate=args.heating_rate,
    )

    simulator.run()
    logging.info("Simulador encerrado.")


if __name__ == "__main__":
    main()
