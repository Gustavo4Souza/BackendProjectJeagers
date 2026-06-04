#!/usr/bin/env python3
"""
Seed inicial — EH Brewing
Cadastra as 8 panelas de armazenamento e o usuário admin padrão.

Uso:
    docker compose exec api python scripts/seed_tanks.py
    docker compose exec api python scripts/seed_tanks.py --admin-password MinhaSenh@123
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

import auth
import models
from database import SessionLocal, engine

# ------------------------------------------------------------------
# Dados das 8 panelas
# ------------------------------------------------------------------

TANKS_SEED = [
    {
        "id": 1,
        "name": "Panela 1",
        "location": "Setor A",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 2,
        "name": "Panela 2",
        "location": "Setor A",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 3,
        "name": "Panela 3",
        "location": "Setor A",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 4,
        "name": "Panela 4",
        "location": "Setor A",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 5,
        "name": "Panela 5",
        "location": "Setor B",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 6,
        "name": "Panela 6",
        "location": "Setor B",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 7,
        "name": "Panela 7",
        "location": "Setor B",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
    {
        "id": 8,
        "name": "Panela 8",
        "location": "Setor B",
        "temp_min": 10.0,
        "temp_max": 20.0,
        "status": "active",
    },
]


# ------------------------------------------------------------------
# Funções de seed
# ------------------------------------------------------------------

def seed_tanks(db) -> int:
    created = 0

    for data in TANKS_SEED:
        existing = db.get(models.Tank, data["id"])

        if existing:
            print(f"  [skip] Panela {data['id']} — já existe ({existing.name})")
            continue

        tank = models.Tank(**data)
        db.add(tank)
        created += 1
        print(f"  [ok]   Panela {data['id']} criada — {data['name']} ({data['location']})")

    db.commit()
    return created


DEFAULT_CONTROL_SETPOINTS = {
    1: 15.0,
    2: 12.0,
    3: 18.0,
    4: 14.0,
    5: 16.0,
    6: 13.0,
    7: 17.0,
    8: 15.5,
}


def seed_tank_controls(db) -> int:
    created = 0

    for tank_id, setpoint in DEFAULT_CONTROL_SETPOINTS.items():
        existing = db.query(models.TankControl).filter(models.TankControl.tank_id == tank_id).first()

        if existing:
            print(f"  [skip] Controle panela {tank_id} — já existe (setpoint={existing.setpoint}°C, mode={existing.mode})")
            continue

        control = models.TankControl(
            tank_id=tank_id,
            setpoint=setpoint,
            mode="idle",
            updated_at=datetime.now(timezone.utc),
        )
        db.add(control)
        created += 1
        print(f"  [ok]   Controle panela {tank_id} criado — setpoint={setpoint}°C, mode=idle")

    db.commit()
    return created


def seed_admin(db, username: str, password: str) -> bool:
    existing = db.query(models.User).filter(models.User.username == username).first()

    if existing:
        print(f"  [skip] Usuário '{username}' — já existe (role: {existing.role})")
        return False

    user = models.User(
        username=username,
        password=auth.hash_password(password),
        role="admin",
    )
    db.add(user)
    db.commit()
    print(f"  [ok]   Usuário admin '{username}' criado.")
    return True


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Seed inicial — EH Brewing")
    parser.add_argument(
        "--admin-user",
        default=os.getenv("SEED_ADMIN_USER", "admin"),
        help="Username do admin padrão",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("SEED_ADMIN_PASSWORD", "admin"),
        help="Senha do admin padrão",
    )
    parser.add_argument(
        "--skip-admin",
        action="store_true",
        help="Não criar usuário admin",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("\n=== Seed: Panelas ===")
        n = seed_tanks(db)
        print(f"→ {n} panela(s) criada(s).\n")

        if not args.skip_admin:
            print("=== Seed: Usuário Admin ===")
            seed_admin(db, args.admin_user, args.admin_password)
            print()

        print("=== Seed: Controles de Temperatura ===")
        nc = seed_tank_controls(db)
        print(f"→ {nc} controle(s) criado(s).\n")

    finally:
        db.close()

    print("Seed concluído.")


if __name__ == "__main__":
    main()
