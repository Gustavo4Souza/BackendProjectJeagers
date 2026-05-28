"""
Integration tests — full flows: simulator → API → DB → alert → acknowledge.
"""
from helpers import auth_headers, get_token, make_tank, make_user


class TestFullReadingFlow:
    """Simulate the CLP simulator posting readings and verify downstream effects."""

    def test_reading_persisted_in_db(self, client, db):
        import models

        make_user(db, "sim_op", "pass", "operador")
        tank = make_tank(db, temp_min=10.0, temp_max=20.0)
        token = get_token(client, "sim_op", "pass")

        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 15.0},
            headers=auth_headers(token),
        )

        reading = (
            db.query(models.Reading)
            .filter(models.Reading.tank_id == tank.id)
            .first()
        )
        assert reading is not None
        assert reading.temperature == 15.0

    def test_reading_updates_tank_current_temperature(self, client, db):
        make_user(db, "sim_op2", "pass", "operador")
        make_user(db, "sim_v", "pass", "viewer")
        tank = make_tank(db, temp_min=10.0, temp_max=20.0)

        op_token = get_token(client, "sim_op2", "pass")
        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 14.7},
            headers=auth_headers(op_token),
        )

        v_token = get_token(client, "sim_v", "pass")
        tanks = client.get("/api/v1/tanks", headers=auth_headers(v_token)).json()
        matching = next(t for t in tanks if t["id"] == tank.id)
        assert matching["current_temperature"] == 14.7

    def test_out_of_range_creates_alert_and_resolves(self, client, db):
        make_user(db, "alert_op", "pass", "operador")
        make_user(db, "alert_v", "pass", "viewer")
        tank = make_tank(db, temp_min=10.0, temp_max=20.0)
        op_token = get_token(client, "alert_op", "pass")
        v_token = get_token(client, "alert_v", "pass")

        # Post out-of-range reading — should fire alert
        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 25.0},
            headers=auth_headers(op_token),
        )
        alerts_after_fire = client.get(
            f"/api/v1/alerts?status=active&tank_id={tank.id}",
            headers=auth_headers(v_token),
        ).json()
        assert len(alerts_after_fire) == 1
        assert alerts_after_fire[0]["temperature"] == 25.0

        # Post in-range reading — should resolve alert automatically
        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 15.0},
            headers=auth_headers(op_token),
        )
        alerts_after_resolve = client.get(
            f"/api/v1/alerts?status=active&tank_id={tank.id}",
            headers=auth_headers(v_token),
        ).json()
        assert len(alerts_after_resolve) == 0

    def test_duplicate_alert_not_fired_while_active(self, client, db):
        make_user(db, "dup_op", "pass", "operador")
        make_user(db, "dup_v", "pass", "viewer")
        tank = make_tank(db, temp_min=10.0, temp_max=20.0)
        op_token = get_token(client, "dup_op", "pass")
        v_token = get_token(client, "dup_v", "pass")

        # Two consecutive out-of-range readings
        for temp in (25.0, 26.0):
            client.post(
                "/api/v1/readings",
                json={"tank_id": tank.id, "temperature": temp},
                headers=auth_headers(op_token),
            )

        alerts = client.get(
            f"/api/v1/alerts?status=active&tank_id={tank.id}",
            headers=auth_headers(v_token),
        ).json()
        # Should only have one active alert despite two out-of-range readings
        assert len(alerts) == 1


class TestBatchLifecycle:
    """Test the full batch lifecycle: create → active → completed → export."""

    def test_batch_lifecycle(self, client, db):
        make_user(db, "bl_op", "pass", "operador")
        make_user(db, "bl_v", "pass", "viewer")
        op_token = get_token(client, "bl_op", "pass")
        v_token = get_token(client, "bl_v", "pass")

        # Create
        batch = client.post(
            "/api/v1/batches",
            json={
                "name": "IPA Lote 42",
                "style": "American IPA",
                "original_gravity": 1.065,
            },
            headers=auth_headers(op_token),
        ).json()
        assert batch["status"] == "planned"

        # Start
        batch = client.patch(
            f"/api/v1/batches/{batch['id']}",
            json={"status": "active"},
            headers=auth_headers(op_token),
        ).json()
        assert batch["status"] == "active"

        # Add gravity event
        client.patch(
            f"/api/v1/batches/{batch['id']}/events",
            json={
                "event_type": "gravity_reading",
                "description": "Gravity at day 5",
                "value": 1.020,
                "unit": "SG",
            },
            headers=auth_headers(op_token),
        )

        # Complete with final gravity
        batch = client.patch(
            f"/api/v1/batches/{batch['id']}",
            json={"status": "completed", "final_gravity": 1.012},
            headers=auth_headers(op_token),
        ).json()
        assert batch["status"] == "completed"

        # Get detail — should include abv
        detail = client.get(
            f"/api/v1/batches/{batch['id']}",
            headers=auth_headers(v_token),
        ).json()
        assert detail["abv"] is not None
        assert detail["abv"] > 0

        # Export CSV
        csv_resp = client.get(
            f"/api/v1/batches/{batch['id']}/export?format=csv",
            headers=auth_headers(v_token),
        )
        assert csv_resp.status_code == 200
        csv_text = csv_resp.text
        assert "IPA Lote 42" in csv_text
        assert "gravity_reading" in csv_text


class TestMultipleReadingsPeriod:
    """Readings for a tank filtered by period are returned correctly."""

    def test_readings_within_period_returned(self, client, db):
        from datetime import datetime, timedelta, timezone

        make_user(db, "per_op", "pass", "operador")
        make_user(db, "per_v", "pass", "viewer")
        tank = make_tank(db, temp_min=5.0, temp_max=25.0)
        op_token = get_token(client, "per_op", "pass")
        v_token = get_token(client, "per_v", "pass")

        # Post several readings
        for temp in (12.0, 13.0, 14.0):
            client.post(
                "/api/v1/readings",
                json={"tank_id": tank.id, "temperature": temp},
                headers=auth_headers(op_token),
            )

        resp = client.get(
            f"/api/v1/tanks/{tank.id}/readings?period=6h",
            headers=auth_headers(v_token),
        )
        assert resp.status_code == 200
        readings = resp.json()
        assert len(readings) == 3
        temps = [r["temperature"] for r in readings]
        assert 12.0 in temps
        assert 14.0 in temps
