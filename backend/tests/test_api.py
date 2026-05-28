"""API endpoint tests — covers auth, tanks, readings, alerts, batches, yeast profiles."""
import pytest
from helpers import auth_headers, get_token, make_tank, make_user


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert "version" in data


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_new_user(self, client):
        resp = client.post("/register", json={"username": "newuser", "password": "pass123"})
        assert resp.status_code == 200
        assert "msg" in resp.json()

    def test_register_duplicate_raises_400(self, client):
        client.post("/register", json={"username": "dup", "password": "pass"})
        resp = client.post("/register", json={"username": "dup", "password": "pass"})
        assert resp.status_code == 400

    def test_register_with_role(self, client):
        resp = client.post(
            "/register", json={"username": "op1", "password": "pass", "role": "operador"}
        )
        assert resp.status_code == 200


class TestLogin:
    def test_login_valid_credentials(self, client, db):
        make_user(db, "alice", "secret", "admin")
        resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db):
        make_user(db, "bob", "correct", "viewer")
        resp = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_legacy_login_endpoint(self, client, db):
        make_user(db, "leg", "pass", "viewer")
        resp = client.post("/login", json={"username": "leg", "password": "pass"})
        assert resp.status_code == 200


class TestRefreshLogout:
    def test_refresh_returns_new_tokens(self, client, db):
        make_user(db, "refresh_u", "pass", "viewer")
        login = client.post("/auth/login", json={"username": "refresh_u", "password": "pass"})
        refresh_token = login.json()["refresh_token"]

        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "bad.token.here"})
        assert resp.status_code == 401

    def test_logout_revokes_token(self, client, db):
        make_user(db, "logout_u", "pass", "viewer")
        login = client.post("/auth/login", json={"username": "logout_u", "password": "pass"})
        refresh_token = login.json()["refresh_token"]

        resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
        assert resp.status_code == 200

        # Using the revoked token again should fail
        resp2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp2.status_code == 401

    def test_refresh_used_twice_fails(self, client, db):
        make_user(db, "rotate_u", "pass", "viewer")
        login = client.post("/auth/login", json={"username": "rotate_u", "password": "pass"})
        rt = login.json()["refresh_token"]

        client.post("/auth/refresh", json={"refresh_token": rt})
        resp = client.post("/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 401


# ── Protected route guard ─────────────────────────────────────────────────────

class TestAuthMiddleware:
    def test_protected_route_without_token_returns_401(self, client):
        resp = client.get("/api/v1/tanks")
        assert resp.status_code == 401

    def test_protected_route_with_invalid_token_returns_401(self, client):
        resp = client.get("/api/v1/tanks", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401

    def test_docs_is_public(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_is_public(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200


# ── Tanks ─────────────────────────────────────────────────────────────────────

class TestListTanks:
    def test_returns_empty_list(self, client, db):
        make_user(db, "v1", "pass", "viewer")
        token = get_token(client, "v1", "pass")
        resp = client.get("/api/v1/tanks", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_tank(self, client, db):
        make_user(db, "v2", "pass", "viewer")
        make_tank(db, name="Panela 1")
        token = get_token(client, "v2", "pass")
        resp = client.get("/api/v1/tanks", headers=auth_headers(token))
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Panela 1"

    def test_tank_response_fields(self, client, db):
        make_user(db, "v3", "pass", "viewer")
        make_tank(db)
        token = get_token(client, "v3", "pass")
        tank = client.get("/api/v1/tanks", headers=auth_headers(token)).json()[0]
        assert "id" in tank
        assert "temp_min" in tank
        assert "temp_max" in tank
        assert "current_temperature" in tank
        assert "last_reading_at" in tank


class TestTankStatus:
    def test_status_of_existing_tank(self, client, db):
        make_user(db, "sv", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "sv", "pass")
        resp = client.get(f"/api/v1/tanks/{tank.id}/status", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["tank_id"] == tank.id
        assert data["tank_status"] == "offline"

    def test_status_404_for_missing_tank(self, client, db):
        make_user(db, "sv2", "pass", "viewer")
        token = get_token(client, "sv2", "pass")
        resp = client.get("/api/v1/tanks/9999/status", headers=auth_headers(token))
        assert resp.status_code == 404


class TestUpdateTankConfig:
    def test_admin_can_update(self, client, db):
        make_user(db, "adm1", "pass", "admin")
        tank = make_tank(db)
        token = get_token(client, "adm1", "pass")
        resp = client.patch(
            f"/api/v1/tanks/{tank.id}/config",
            json={"name": "Cerveja Nova", "temp_min": 8.0, "temp_max": 18.0},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Cerveja Nova"

    def test_viewer_cannot_update(self, client, db):
        make_user(db, "vwr1", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "vwr1", "pass")
        resp = client.patch(
            f"/api/v1/tanks/{tank.id}/config",
            json={"name": "X"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_invalid_range_returns_400(self, client, db):
        make_user(db, "adm2", "pass", "admin")
        tank = make_tank(db)
        token = get_token(client, "adm2", "pass")
        resp = client.patch(
            f"/api/v1/tanks/{tank.id}/config",
            json={"temp_min": 20.0, "temp_max": 10.0},
            headers=auth_headers(token),
        )
        assert resp.status_code in (400, 422)

    def test_update_nonexistent_tank(self, client, db):
        make_user(db, "adm3", "pass", "admin")
        token = get_token(client, "adm3", "pass")
        resp = client.patch(
            "/api/v1/tanks/9999/config",
            json={"name": "X"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404


class TestTankReadings:
    def test_readings_empty(self, client, db):
        make_user(db, "rv1", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "rv1", "pass")
        resp = client.get(
            f"/api/v1/tanks/{tank.id}/readings?period=24h",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_period_returns_422(self, client, db):
        make_user(db, "rv2", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "rv2", "pass")
        resp = client.get(
            f"/api/v1/tanks/{tank.id}/readings?period=99h",
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    def test_valid_periods_accepted(self, client, db):
        make_user(db, "rv3", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "rv3", "pass")
        for period in ("6h", "24h", "7d", "30d"):
            resp = client.get(
                f"/api/v1/tanks/{tank.id}/readings?period={period}",
                headers=auth_headers(token),
            )
            assert resp.status_code == 200


# ── Readings ──────────────────────────────────────────────────────────────────

class TestCreateReading:
    def test_operator_can_post_reading(self, client, db):
        make_user(db, "op2", "pass", "operador")
        tank = make_tank(db)
        token = get_token(client, "op2", "pass")
        resp = client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 15.0},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.json()["temperature"] == 15.0

    def test_admin_can_post_reading(self, client, db):
        make_user(db, "adm4", "pass", "admin")
        tank = make_tank(db)
        token = get_token(client, "adm4", "pass")
        resp = client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 12.0},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201

    def test_viewer_cannot_post_reading(self, client, db):
        make_user(db, "vwr2", "pass", "viewer")
        tank = make_tank(db)
        token = get_token(client, "vwr2", "pass")
        resp = client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 12.0},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_reading_for_missing_tank_returns_404(self, client, db):
        make_user(db, "op3", "pass", "operador")
        token = get_token(client, "op3", "pass")
        resp = client.post(
            "/api/v1/readings",
            json={"tank_id": 9999, "temperature": 15.0},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_reading_publishes_to_redis(self, client, db, mock_redis):
        make_user(db, "op4", "pass", "operador")
        tank = make_tank(db)
        token = get_token(client, "op4", "pass")
        mock_redis.publish.reset_mock()
        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 15.0},
            headers=auth_headers(token),
        )
        assert mock_redis.publish.called

    def test_out_of_range_reading_fires_alert(self, client, db):
        make_user(db, "op5", "pass", "operador")
        tank = make_tank(db, temp_min=10.0, temp_max=20.0)
        token = get_token(client, "op5", "pass")

        # Post a temperature above the max
        client.post(
            "/api/v1/readings",
            json={"tank_id": tank.id, "temperature": 25.0},
            headers=auth_headers(token),
        )
        # Check alert was created
        make_user(db, "adm5_v", "pass", "admin")
        vtoken = get_token(client, "adm5_v", "pass")
        alerts = client.get(
            f"/api/v1/alerts?status=active&tank_id={tank.id}",
            headers=auth_headers(vtoken),
        ).json()
        assert len(alerts) >= 1


# ── Alerts ────────────────────────────────────────────────────────────────────

class TestAlerts:
    def test_list_alerts_empty(self, client, db):
        make_user(db, "va1", "pass", "viewer")
        token = get_token(client, "va1", "pass")
        resp = client.get("/api/v1/alerts", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_active_alerts(self, client, db):
        make_user(db, "va2", "pass", "viewer")
        token = get_token(client, "va2", "pass")
        resp = client.get("/api/v1/alerts?status=active", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_filter_resolved_alerts(self, client, db):
        make_user(db, "va3", "pass", "viewer")
        token = get_token(client, "va3", "pass")
        resp = client.get("/api/v1/alerts?status=resolved", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_invalid_status_filter_returns_422(self, client, db):
        make_user(db, "va4", "pass", "viewer")
        token = get_token(client, "va4", "pass")
        resp = client.get("/api/v1/alerts?status=unknown", headers=auth_headers(token))
        assert resp.status_code == 422

    def test_acknowledge_alert(self, client, db):
        import models
        from datetime import datetime, timezone

        make_user(db, "adm_ack", "pass", "admin")
        tank = make_tank(db)
        alert = models.Alert(tank_id=tank.id, temperature=25.0, fired_at=datetime.now(timezone.utc))
        db.add(alert)
        db.commit()

        token = get_token(client, "adm_ack", "pass")
        resp = client.patch(
            f"/api/v1/alerts/{alert.id}/acknowledge",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200

    def test_acknowledge_missing_alert(self, client, db):
        make_user(db, "adm_ack2", "pass", "admin")
        token = get_token(client, "adm_ack2", "pass")
        resp = client.patch("/api/v1/alerts/9999/acknowledge", headers=auth_headers(token))
        assert resp.status_code == 404


# ── Yeast Profiles ────────────────────────────────────────────────────────────

class TestYeastProfiles:
    def test_list_yeast_profiles_empty(self, client, db):
        make_user(db, "yv1", "pass", "viewer")
        token = get_token(client, "yv1", "pass")
        resp = client.get("/api/v1/yeast_profiles", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_admin_creates_profile(self, client, db):
        make_user(db, "ya1", "pass", "admin")
        token = get_token(client, "ya1", "pass")
        resp = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "WY1056 American Ale", "strain": "Chico"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "WY1056 American Ale"

    def test_viewer_cannot_create_profile(self, client, db):
        make_user(db, "yv2", "pass", "viewer")
        token = get_token(client, "yv2", "pass")
        resp = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "Some Yeast"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_duplicate_profile_name_returns_400(self, client, db):
        make_user(db, "ya2", "pass", "admin")
        token = get_token(client, "ya2", "pass")
        client.post("/api/v1/yeast_profiles", json={"name": "WY1234"}, headers=auth_headers(token))
        resp = client.post("/api/v1/yeast_profiles", json={"name": "WY1234"}, headers=auth_headers(token))
        assert resp.status_code == 400

    def test_get_profile_by_id(self, client, db):
        make_user(db, "ya3", "pass", "admin")
        token = get_token(client, "ya3", "pass")
        created = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "S-04 English Ale"},
            headers=auth_headers(token),
        ).json()
        resp = client.get(f"/api/v1/yeast_profiles/{created['id']}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "S-04 English Ale"

    def test_get_profile_404(self, client, db):
        make_user(db, "yv3", "pass", "viewer")
        token = get_token(client, "yv3", "pass")
        resp = client.get("/api/v1/yeast_profiles/9999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_update_profile(self, client, db):
        make_user(db, "ya4", "pass", "admin")
        token = get_token(client, "ya4", "pass")
        created = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "US-05"},
            headers=auth_headers(token),
        ).json()
        resp = client.patch(
            f"/api/v1/yeast_profiles/{created['id']}",
            json={"strain": "Clean American Ale"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["strain"] == "Clean American Ale"

    def test_delete_profile(self, client, db):
        make_user(db, "ya5", "pass", "admin")
        token = get_token(client, "ya5", "pass")
        created = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "Delete Me"},
            headers=auth_headers(token),
        ).json()
        resp = client.delete(
            f"/api/v1/yeast_profiles/{created['id']}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 204

    def test_delete_linked_profile_returns_400(self, client, db):
        make_user(db, "ya6", "pass", "admin")
        token = get_token(client, "ya6", "pass")
        profile = client.post(
            "/api/v1/yeast_profiles",
            json={"name": "Linked Profile"},
            headers=auth_headers(token),
        ).json()
        client.post(
            "/api/v1/batches",
            json={"name": "Lote X", "style": "IPA", "yeast_profile_id": profile["id"]},
            headers=auth_headers(token),
        )
        resp = client.delete(
            f"/api/v1/yeast_profiles/{profile['id']}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400


# ── Batches ───────────────────────────────────────────────────────────────────

class TestBatches:
    def test_list_batches_empty(self, client, db):
        make_user(db, "bv1", "pass", "viewer")
        token = get_token(client, "bv1", "pass")
        resp = client.get("/api/v1/batches", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_batch(self, client, db):
        make_user(db, "bo1", "pass", "operador")
        token = get_token(client, "bo1", "pass")
        resp = client.post(
            "/api/v1/batches",
            json={"name": "Lote Teste", "style": "Pale Ale"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Lote Teste"

    def test_viewer_cannot_create_batch(self, client, db):
        make_user(db, "bv2", "pass", "viewer")
        token = get_token(client, "bv2", "pass")
        resp = client.post(
            "/api/v1/batches",
            json={"name": "X", "style": "IPA"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_get_batch_by_id(self, client, db):
        make_user(db, "bo2", "pass", "operador")
        token = get_token(client, "bo2", "pass")
        created = client.post(
            "/api/v1/batches",
            json={"name": "Lote Detail", "style": "Stout"},
            headers=auth_headers(token),
        ).json()
        resp = client.get(f"/api/v1/batches/{created['id']}", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_get_batch_404(self, client, db):
        make_user(db, "bv3", "pass", "viewer")
        token = get_token(client, "bv3", "pass")
        resp = client.get("/api/v1/batches/9999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_update_batch(self, client, db):
        make_user(db, "bo3", "pass", "operador")
        token = get_token(client, "bo3", "pass")
        created = client.post(
            "/api/v1/batches",
            json={"name": "Lote Update", "style": "Lager"},
            headers=auth_headers(token),
        ).json()
        resp = client.patch(
            f"/api/v1/batches/{created['id']}",
            json={"status": "active"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_filter_batch_by_status(self, client, db):
        make_user(db, "bo4", "pass", "operador")
        token = get_token(client, "bo4", "pass")
        client.post(
            "/api/v1/batches",
            json={"name": "Planned Batch", "style": "Wheat"},
            headers=auth_headers(token),
        )
        resp = client.get("/api/v1/batches?status=planned", headers=auth_headers(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_batch_event(self, client, db):
        make_user(db, "bo5", "pass", "operador")
        token = get_token(client, "bo5", "pass")
        batch = client.post(
            "/api/v1/batches",
            json={"name": "Event Batch", "style": "Porter"},
            headers=auth_headers(token),
        ).json()
        resp = client.patch(
            f"/api/v1/batches/{batch['id']}/events",
            json={
                "event_type": "gravity_reading",
                "description": "Initial gravity taken",
                "value": 1.052,
                "unit": "SG",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 201

    def test_export_batch_csv(self, client, db):
        make_user(db, "bex1", "pass", "viewer")
        make_user(db, "bex_op", "pass", "operador")
        op_token = get_token(client, "bex_op", "pass")
        batch = client.post(
            "/api/v1/batches",
            json={"name": "Export Batch", "style": "IPA"},
            headers=auth_headers(op_token),
        ).json()
        v_token = get_token(client, "bex1", "pass")
        resp = client.get(
            f"/api/v1/batches/{batch['id']}/export?format=csv",
            headers=auth_headers(v_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_batch_unsupported_format(self, client, db):
        make_user(db, "bex2", "pass", "viewer")
        make_user(db, "bex_op2", "pass", "operador")
        op_token = get_token(client, "bex_op2", "pass")
        batch = client.post(
            "/api/v1/batches",
            json={"name": "Export Batch 2", "style": "IPA"},
            headers=auth_headers(op_token),
        ).json()
        v_token = get_token(client, "bex2", "pass")
        resp = client.get(
            f"/api/v1/batches/{batch['id']}/export?format=pdf",
            headers=auth_headers(v_token),
        )
        assert resp.status_code == 400
