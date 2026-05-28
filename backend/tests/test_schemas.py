"""Unit tests for schemas.py — Pydantic validation."""
import pytest
from datetime import datetime, timezone

import schemas


class TestTankConfigUpdate:
    def test_valid_update(self):
        s = schemas.TankConfigUpdate(name="Nova Cerveja", temp_min=5.0, temp_max=15.0)
        assert s.name == "Nova Cerveja"

    def test_partial_update_only_name(self):
        s = schemas.TankConfigUpdate(name="Pilsen")
        assert s.name == "Pilsen"
        assert s.temp_min is None
        assert s.temp_max is None

    def test_min_equal_max_raises(self):
        with pytest.raises(Exception):
            schemas.TankConfigUpdate(temp_min=10.0, temp_max=10.0)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(Exception):
            schemas.TankConfigUpdate(temp_min=20.0, temp_max=10.0)

    def test_name_too_long_raises(self):
        with pytest.raises(Exception):
            schemas.TankConfigUpdate(name="x" * 101)


class TestReadingCreate:
    def test_valid_reading(self):
        r = schemas.ReadingCreate(tank_id=1, temperature=14.5)
        assert r.tank_id == 1
        assert r.temperature == 14.5

    def test_tank_id_zero_raises(self):
        with pytest.raises(Exception):
            schemas.ReadingCreate(tank_id=0, temperature=14.5)

    def test_tank_id_negative_raises(self):
        with pytest.raises(Exception):
            schemas.ReadingCreate(tank_id=-1, temperature=14.5)

    def test_default_recorded_at_is_utc(self):
        r = schemas.ReadingCreate(tank_id=1, temperature=10.0)
        assert r.recorded_at.tzinfo is not None

    def test_explicit_recorded_at(self):
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        r = schemas.ReadingCreate(tank_id=2, temperature=8.0, recorded_at=ts)
        assert r.recorded_at == ts


class TestYeastProfileCreate:
    def test_valid_profile(self):
        p = schemas.YeastProfileCreate(name="WY1056", attenuation_min=73.0, attenuation_max=77.0)
        assert p.name == "WY1056"

    def test_attenuation_min_gt_max_raises(self):
        with pytest.raises(Exception):
            schemas.YeastProfileCreate(name="X", attenuation_min=80.0, attenuation_max=70.0)

    def test_temperature_min_gt_max_raises(self):
        with pytest.raises(Exception):
            schemas.YeastProfileCreate(name="X", temperature_min_c=25.0, temperature_max_c=20.0)

    def test_attenuation_out_of_range_raises(self):
        with pytest.raises(Exception):
            schemas.YeastProfileCreate(name="X", attenuation_min=-1.0)

    def test_optional_fields_default_none(self):
        p = schemas.YeastProfileCreate(name="Simple")
        assert p.strain is None
        assert p.attenuation_min is None
        assert p.notes is None

    def test_name_too_short_raises(self):
        with pytest.raises(Exception):
            schemas.YeastProfileCreate(name="")


class TestBatchCreate:
    def test_valid_batch(self):
        b = schemas.BatchCreate(name="Lote 1", style="IPA")
        assert b.name == "Lote 1"
        assert b.status == "planned"

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            schemas.BatchCreate(name="X", style="IPA", status="invalid_status")

    def test_ended_before_started_raises(self):
        with pytest.raises(Exception):
            schemas.BatchCreate(
                name="X",
                style="IPA",
                started_at=datetime(2025, 6, 10, tzinfo=timezone.utc),
                ended_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
            )

    def test_final_gravity_greater_than_original_raises(self):
        with pytest.raises(Exception):
            schemas.BatchCreate(
                name="X", style="IPA", original_gravity=1.050, final_gravity=1.060
            )

    def test_gravity_below_min_raises(self):
        with pytest.raises(Exception):
            schemas.BatchCreate(name="X", style="IPA", original_gravity=0.5)

    def test_volume_negative_raises(self):
        with pytest.raises(Exception):
            schemas.BatchCreate(name="X", style="IPA", volume_liters=-10.0)


class TestHealthResponse:
    def test_health_response(self):
        h = schemas.HealthResponse(status="ok", version="1.0.0")
        assert h.status == "ok"
        assert h.version == "1.0.0"


class TestUserCreate:
    def test_default_role_viewer(self):
        u = schemas.UserCreate(username="alice", password="secret")
        assert u.role == "viewer"

    def test_admin_role(self):
        u = schemas.UserCreate(username="admin", password="secret", role="admin")
        assert u.role == "admin"

    def test_invalid_role_raises(self):
        with pytest.raises(Exception):
            schemas.UserCreate(username="x", password="y", role="superuser")
