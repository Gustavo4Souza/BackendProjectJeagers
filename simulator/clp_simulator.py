#!/usr/bin/env python3
"""
Simulador de CLP — EH Brewing
Simula 8 panelas de armazenamento enviando leituras de temperatura para a API.
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

# Setpoints padrão por panela (temperatura alvo em °C)
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


@dataclass
class TankSimulator:
    """Simula a dinâmica de temperatura de uma única panela."""

    tank_id: int
    setpoint: float
    noise_std: float = 0.3
    current_temp: float = field(init=False)

    def __post_init__(self):
        self.current_temp = self.setpoint + random.gauss(0, self.noise_std)

    def read(self, fault_temp: Optional[float] = None) -> float:
        """Retorna a temperatura atual com ruído gaussiano.

        Se fault_temp for informado, retorna esse valor com pequeno ruído
        para simular uma falha de temperatura na panela.
        """
        if fault_temp is not None:
            return round(fault_temp + random.gauss(0, 0.1), 2)

        # Dinâmica de primeira ordem: tende ao setpoint com ruído
        self.current_temp = (
            0.95 * self.current_temp
            + 0.05 * self.setpoint
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
    ):
        self.api_url = api_url.rstrip("/")
        self.interval = interval
        self.fault_tank = fault_tank
        self.fault_temp = fault_temp
        self.username = username
        self.password = password

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
    # Envio de leitura
    # ------------------------------------------------------------------

    def _send_reading(self, tank_id: int, temperature: float) -> bool:
        """Envia uma leitura para a API.

        Retorna True em caso de sucesso ou erro não-crítico.
        Retorna False se o token expirou (401) — sinaliza re-login.
        Lança requests.RequestException em caso de falha de rede.
        """
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
                "Panela %d não cadastrada na API (404). "
                "Execute o seed inicial antes de usar o simulador.",
                tank_id,
            )
            return True  # Não é erro de conexão; continue o ciclo

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

        if self.fault_tank:
            logging.info(
                "Modo de falha ativo: panela %d → %.2f°C",
                self.fault_tank,
                self.fault_temp,
            )

        while self.running:
            # Garante token válido antes do ciclo
            if not self.access_token:
                if not self._login():
                    self._wait_retry("Login falhou")
                    continue
                self._reset_retry()

            # Ciclo de leitura das 8 panelas
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
        """Lê e envia a temperatura de todas as 8 panelas. Retorna False em falha de rede."""
        for tank_id, tank in self.tanks.items():
            fault_temp = (
                self.fault_temp if tank_id == self.fault_tank else None
            )
            temperature = tank.read(fault_temp)

            try:
                ok = self._send_reading(tank_id, temperature)
            except requests.RequestException as exc:
                logging.warning("Erro de rede ao enviar panela %d: %s", tank_id, exc)
                return False

            if not ok:
                return False  # Token expirado — força re-login

        return True

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _interruptible_sleep(self, seconds: float):
        """Sleep em fatias de 0.5s para reagir ao sinal de shutdown rapidamente."""
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
    )

    simulator.run()
    logging.info("Simulador encerrado.")


if __name__ == "__main__":
    main()
