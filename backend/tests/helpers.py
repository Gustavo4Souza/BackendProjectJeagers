"""Shared test helpers — used by test_api.py and test_integration.py."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import auth as auth_module
import models
from fastapi.testclient import TestClient


def make_user(db, username: str, password: str, role: str = "viewer") -> models.User:
    user = models.User(
        username=username,
        password=auth_module.hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_tank(
    db,
    name: str = "Tanque Teste",
    temp_min: float = 10.0,
    temp_max: float = 20.0,
    location: str = "Sala A",
) -> models.Tank:
    tank = models.Tank(name=name, temp_min=temp_min, temp_max=temp_max, location=location)
    db.add(tank)
    db.commit()
    db.refresh(tank)
    return tank


def get_token(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
