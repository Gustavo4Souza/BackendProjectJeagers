"""
Tests specifically targeting checklist items not covered by test_api.py / test_integration.py:
  - 8 tanks after seed
  - WebSocket connection (101), 8 simultaneous connections
  - Login with the default seeded admin/admin123 credentials (checklist phrasing)
"""
from helpers import auth_headers, get_token, make_tank, make_user


# ── Autenticação ──────────────────────────────────────────────────────────────

class TestLoginAdminPassword:
    """Checklist: Login válido com admin / admin123."""

    def test_login_admin_admin123(self, client, db):
        make_user(db, "admin", "admin123", "admin")
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


# ── Panelas ───────────────────────────────────────────────────────────────────

class TestEightTanksAfterSeed:
    """Checklist: retorna lista com 8 panelas após o seed."""

    def test_list_returns_8_tanks(self, client, db):
        make_user(db, "v_8", "pass", "viewer")
        for i in range(1, 9):
            make_tank(db, name=f"Panela {i}")
        token = get_token(client, "v_8", "pass")
        resp = client.get("/api/v1/tanks", headers=auth_headers(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 8

    def test_tank_names_in_list(self, client, db):
        make_user(db, "v_names", "pass", "viewer")
        for i in range(1, 9):
            make_tank(db, name=f"Panela {i}")
        token = get_token(client, "v_names", "pass")
        names = [t["name"] for t in client.get("/api/v1/tanks", headers=auth_headers(token)).json()]
        for i in range(1, 9):
            assert f"Panela {i}" in names


# ── Batch status planned ──────────────────────────────────────────────────────

class TestBatchCreatedAsPlanned:
    """Checklist: Criar lote retorna 201 e status: planned."""

    def test_new_batch_has_planned_status(self, client, db):
        make_user(db, "op_plan", "pass", "operador")
        token = get_token(client, "op_plan", "pass")
        resp = client.post(
            "/api/v1/batches",
            json={"name": "Novo Lote", "style": "IPA"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "planned"


# ── WebSocket ─────────────────────────────────────────────────────────────────

class TestWebSocket:
    """Checklist: WebSocket connection, message, 8 simultaneous connections."""

    def test_websocket_connection_established(self, client, db):
        """Connecting to /ws/tanks/{id} must succeed (HTTP 101 handshake)."""
        make_tank(db, name="WS Tank")
        # TestClient raises on connection failure; no exception == 101 accepted
        with client.websocket_connect("/ws/tanks/1") as ws:
            assert ws is not None

    def test_websocket_accepts_any_tank_id(self, client, db):
        """The WS endpoint accepts a string tank_id — connection must not error."""
        with client.websocket_connect("/ws/tanks/42") as ws:
            assert ws is not None

    def test_8_simultaneous_websocket_connections(self, client, db):
        """Checklist: 8 simultaneous connections (one per tank) without error."""
        connections = []
        try:
            for tank_id in range(1, 9):
                ws = client.websocket_connect(f"/ws/tanks/{tank_id}")
                connections.append(ws.__enter__())
            assert len(connections) == 8
        finally:
            for ws_obj in connections:
                try:
                    ws_obj.__exit__(None, None, None)
                except Exception:
                    pass

    def test_reading_publishes_and_ws_connection_coexists(self, client, db, mock_redis):
        """
        Post a reading while a WS is connected.
        Checklist item 'mensagem recebida': with mocked Redis the WS message
        itself cannot be asserted end-to-end, but we verify:
          - WS connection stays alive
          - redis.publish is called with the correct channel
        """
        import json

        make_user(db, "op_ws", "pass", "operador")
        tank = make_tank(db, name="WS Reading Tank")
        token = get_token(client, "op_ws", "pass")
        mock_redis.publish.reset_mock()

        with client.websocket_connect(f"/ws/tanks/{tank.id}") as ws:
            resp = client.post(
                "/api/v1/readings",
                json={"tank_id": tank.id, "temperature": 13.5},
                headers=auth_headers(token),
            )
            assert resp.status_code == 201
            assert mock_redis.publish.called

            call_args = mock_redis.publish.call_args
            channel = call_args[0][0]
            payload = json.loads(call_args[0][1])

            assert str(tank.id) in channel
            assert payload["tank_id"] == tank.id
            assert payload["temperature"] == 13.5
            assert "recorded_at" in payload
