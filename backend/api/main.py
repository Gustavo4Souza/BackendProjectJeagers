import asyncio
import contextlib
import csv
import io
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import auth
import models
import schemas
from database import SessionLocal, engine

API_VERSION = os.getenv("API_VERSION", "0.1.0")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PROTECTED_ROLES = ("admin", "operador", "viewer")
ALERTS_CHANNEL = "alerts:events"


def tank_readings_channel(tank_id: int) -> str:
    return f"tanks:{tank_id}:readings"

def utc_now():
    return datetime.now(timezone.utc)


class FermenterWebSocketHub:
    def __init__(self):
        self.clients = defaultdict(set)
        self.subscribers = {}
        self.lock = asyncio.Lock()
        self.redis = None

    async def connect(self, tank_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.clients[tank_id].add(websocket)
            if tank_id not in self.subscribers:
                self.subscribers[tank_id] = asyncio.create_task(self.subscribe(tank_id))

    async def disconnect(self, tank_id: str, websocket: WebSocket):
        task = None
        async with self.lock:
            self.clients[tank_id].discard(websocket)
            if not self.clients[tank_id]:
                task = self.subscribers.pop(tank_id, None)
                self.clients.pop(tank_id, None)

        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def subscribe(self, tank_id: str):
        pubsub = self.redis.pubsub()
        channel = tank_readings_channel(int(tank_id))

        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.broadcast(tank_id, message["data"])
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()

    async def broadcast(self, tank_id: str, message: str):
        async with self.lock:
            clients = list(self.clients.get(tank_id, set()))

        if not clients:
            return

        results = await asyncio.gather(
            *(client.send_text(message) for client in clients),
            return_exceptions=True,
        )

        stale_clients = [
            client for client, result in zip(clients, results) if isinstance(result, Exception)
        ]

        if stale_clients:
            async with self.lock:
                for client in stale_clients:
                    self.clients[tank_id].discard(client)

    async def close(self):
        async with self.lock:
            tasks = list(self.subscribers.values())
            self.subscribers.clear()
            self.clients.clear()

        for task in tasks:
            task.cancel()

        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task


websocket_hub = FermenterWebSocketHub()


class AlertsWebSocketHub:
    def __init__(self):
        self.clients: set = set()
        self.subscriber: asyncio.Task | None = None
        self.lock = asyncio.Lock()
        self.redis = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.clients.add(websocket)
            if self.subscriber is None or self.subscriber.done():
                self.subscriber = asyncio.create_task(self.subscribe())

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.clients.discard(websocket)

    async def subscribe(self):
        pubsub = self.redis.pubsub()
        try:
            await pubsub.subscribe(ALERTS_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.broadcast(message["data"])
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(ALERTS_CHANNEL)
                await pubsub.aclose()

    async def broadcast(self, message: str):
        async with self.lock:
            clients = list(self.clients)
        if not clients:
            return
        results = await asyncio.gather(
            *(c.send_text(message) for c in clients),
            return_exceptions=True,
        )
        stale = [c for c, r in zip(clients, results) if isinstance(r, Exception)]
        if stale:
            async with self.lock:
                for c in stale:
                    self.clients.discard(c)

    async def close(self):
        async with self.lock:
            task = self.subscriber
            self.subscriber = None
            self.clients.clear()
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


alerts_hub = AlertsWebSocketHub()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await app.state.redis.ping()
    websocket_hub.redis = app.state.redis
    alerts_hub.redis = app.state.redis

    try:
        yield
    finally:
        await websocket_hub.close()
        await alerts_hub.close()
        await app.state.redis.aclose()

# Tables auto-created on startup; use `alembic upgrade head` for fresh deployments.
models.Base.metadata.create_all(bind=engine)

def ensure_schema_updates():
    inspector = inspect(engine)

    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}

        if "role" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'viewer'")
                )

ensure_schema_updates()

app = FastAPI(
    title="EH Brewing API",
    version=API_VERSION,
    description="API de monitoramento de temperatura para panelas de bebidas.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Status da aplicacao."},
        {"name": "Auth", "description": "Cadastro e login de usuarios."},
        {"name": "Tanks", "description": "Panelas de armazenamento e suas leituras."},
        {"name": "Readings", "description": "Ingestao de leituras de temperatura."},
        {"name": "Alerts", "description": "Alertas de temperatura fora da faixa configurada."},
        {"name": "Batches", "description": "Gerenciamento de lotes de fermentacao."},
        {"name": "Yeast Profiles", "description": "Cadastro de perfis de levedura."},
    ],
)


# --- Error handlers centralizados ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

def _serializable(obj):
    """Recursively converts non-JSON-serializable objects (e.g. Pydantic v2 ctx exceptions) to str."""
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serializable(item) for item in obj]
    if isinstance(obj, Exception):
        return str(obj)
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _serializable(exc.errors())},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )


# --- Dependências ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_public_path(path: str):
    public_exact_paths = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/register",
        "/login",
        "/auth/login",
        "/auth/refresh",
        "/auth/logout",
    }

    return path in public_exact_paths or path.startswith("/docs/")

@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    if is_public_path(request.url.path):
        return await call_next(request)

    authorization = request.headers.get("Authorization")

    if not authorization or not authorization.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"detail": "Token de acesso ausente"})

    token = authorization.split(" ", 1)[1]

    try:
        payload = auth.decode_token(token)
    except ValueError:
        return JSONResponse(status_code=401, content={"detail": "Token de acesso invalido"})

    if payload.get("type") != "access":
        return JSONResponse(status_code=401, content={"detail": "Token de acesso invalido"})

    db = SessionLocal()

    try:
        user = db.query(models.User).filter(models.User.username == payload.get("sub")).first()

        if not user:
            return JSONResponse(status_code=401, content={"detail": "Usuario nao encontrado"})

        request.state.user = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }
    finally:
        db.close()

    return await call_next(request)

def require_roles(*roles: str):
    def dependency(request: Request):
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(status_code=401, detail="Autenticacao obrigatoria")

        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Permissao insuficiente")

        return user

    return dependency

def get_batch_or_404(batch_id: int, db: Session):
    batch = db.get(models.Batch, batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail="Lote nao encontrado")

    return batch

def get_yeast_profile_or_404(yeast_profile_id: int, db: Session):
    yeast_profile = db.get(models.YeastProfile, yeast_profile_id)

    if not yeast_profile:
        raise HTTPException(status_code=404, detail="Perfil de levedura nao encontrado")

    return yeast_profile

def ensure_yeast_profile_exists(yeast_profile_id: int | None, db: Session):
    if yeast_profile_id is not None:
        get_yeast_profile_or_404(yeast_profile_id, db)

def close_completed_batch(batch: models.Batch):
    if batch.status == "completed" and batch.ended_at is None:
        batch.ended_at = datetime.now(timezone.utc)

def calculate_batch_stats(batch: models.Batch):
    original_gravity = batch.original_gravity
    final_gravity = batch.final_gravity

    if original_gravity is None or final_gravity is None:
        return None, None

    abv = round((original_gravity - final_gravity) * 131.25, 2)
    apparent_attenuation = None

    if original_gravity > 1:
        apparent_attenuation = round(
            ((original_gravity - final_gravity) / (original_gravity - 1)) * 100,
            2,
        )

    return abv, apparent_attenuation

def batch_detail_payload(batch: models.Batch):
    payload = schemas.BatchDetailResponse.model_validate(batch).model_dump()
    payload["abv"], payload["apparent_attenuation"] = calculate_batch_stats(batch)
    return payload

def as_aware_utc(value: datetime):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


PERIOD_DELTA: dict[str, timedelta] = {
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

OFFLINE_THRESHOLD = timedelta(seconds=30)
WARNING_MARGIN = 0.5


def compute_tank_status(
    temperature: float | None,
    temp_min: float,
    temp_max: float,
    last_reading_at: datetime | None,
) -> str:
    if last_reading_at is None:
        return "offline"

    age = utc_now() - as_aware_utc(last_reading_at)
    if age > OFFLINE_THRESHOLD:
        return "offline"

    if temperature is None:
        return "offline"

    if temperature > temp_max or temperature < temp_min:
        return "alert"

    if temperature > temp_max - WARNING_MARGIN or temperature < temp_min + WARNING_MARGIN:
        return "warning"

    return "normal"


def get_tank_or_404(tank_id: int, db: Session) -> models.Tank:
    tank = db.get(models.Tank, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Panela nao encontrada")
    return tank


def get_latest_reading(tank_id: int, db: Session) -> models.Reading | None:
    return (
        db.query(models.Reading)
        .filter(models.Reading.tank_id == tank_id)
        .order_by(models.Reading.recorded_at.desc())
        .first()
    )


def get_active_alert(tank_id: int, db: Session) -> models.Alert | None:
    return (
        db.query(models.Alert)
        .filter(
            models.Alert.tank_id == tank_id,
            models.Alert.resolved_at.is_(None),
        )
        .first()
    )


def fire_or_resolve_alert(tank: models.Tank, temperature: float, db: Session) -> models.Alert | None:
    active_alert = get_active_alert(tank.id, db)
    out_of_range = temperature > tank.temp_max or temperature < tank.temp_min

    if out_of_range and active_alert is None:
        new_alert = models.Alert(tank_id=tank.id, temperature=temperature)
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert

    if not out_of_range and active_alert is not None:
        active_alert.resolved_at = utc_now()
        db.commit()

    return None


def store_refresh_token(username: str, role: str, token_jti: str, expires_at: datetime, db: Session):
    refresh_token = models.RefreshToken(
        token_jti=token_jti,
        username=username,
        role=role,
        expires_at=expires_at,
    )

    db.add(refresh_token)
    db.commit()

def issue_token_pair(user: models.User, db: Session):
    access_token, _, _ = auth.create_access_token(user.username, user.role)
    refresh_token, refresh_jti, refresh_expires_at = auth.create_refresh_token(user.username, user.role)
    store_refresh_token(user.username, user.role, refresh_jti, refresh_expires_at, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

def get_valid_refresh_token(refresh_token: str, db: Session):
    try:
        payload = auth.decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Refresh token invalido")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalido")

    stored_token = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_jti == payload.get("jti"))
        .first()
    )

    if not stored_token or stored_token.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revogado")

    if as_aware_utc(stored_token.expires_at) <= utc_now():
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    return payload, stored_token

def revoke_refresh_token(stored_token: models.RefreshToken, db: Session):
    stored_token.revoked_at = utc_now()
    db.commit()


# --- Rotas ---

@app.get("/health", response_model=schemas.HealthResponse, tags=["Health"])
def health():
    return {"status": "ok", "version": API_VERSION}

@app.post("/register", tags=["Auth"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    hashed_password = auth.hash_password(user.password)

    new_user = models.User(
        username=user.username,
        password=hashed_password,
        role=user.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "Usuário criado com sucesso"}

@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def auth_login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Credenciais invalidas")

    return issue_token_pair(db_user, db)

@app.post("/auth/refresh", response_model=schemas.TokenResponse, tags=["Auth"])
def refresh_token(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    _, stored_token = get_valid_refresh_token(payload.refresh_token, db)
    user = db.query(models.User).filter(models.User.username == stored_token.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")

    revoke_refresh_token(stored_token, db)
    return issue_token_pair(user, db)

@app.post("/auth/logout", response_model=schemas.LogoutResponse, tags=["Auth"])
def logout(payload: schemas.LogoutRequest, db: Session = Depends(get_db)):
    _, stored_token = get_valid_refresh_token(payload.refresh_token, db)
    revoke_refresh_token(stored_token, db)

    return {"msg": "Logout realizado com sucesso"}

@app.post("/login", tags=["Auth"])
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    if not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Senha incorreta")

    return {"msg": "Login realizado com sucesso"}

@app.post(
    "/api/v1/readings",
    response_model=schemas.ReadingResponse,
    status_code=201,
    tags=["Readings"],
    dependencies=[Depends(require_roles("admin", "operador"))],
)
async def create_reading(
    reading: schemas.ReadingCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tank = db.get(models.Tank, reading.tank_id)

    if not tank:
        raise HTTPException(status_code=404, detail="Panela nao encontrada")

    new_reading = models.Reading(**reading.model_dump())

    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)

    payload = schemas.ReadingResponse.model_validate(new_reading).model_dump(mode="json")
    await request.app.state.redis.publish(
        tank_readings_channel(new_reading.tank_id),
        json.dumps(payload),
    )

    fired_alert = fire_or_resolve_alert(tank, new_reading.temperature, db)
    if fired_alert:
        alert_payload = schemas.AlertResponse.model_validate(fired_alert).model_dump(mode="json")
        await request.app.state.redis.publish(ALERTS_CHANNEL, json.dumps(alert_payload))

    return new_reading

@app.get(
    "/api/v1/tanks",
    response_model=list[schemas.TankResponse],
    tags=["Tanks"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def list_tanks(db: Session = Depends(get_db)):
    tanks = db.query(models.Tank).order_by(models.Tank.id).all()
    result = []

    for tank in tanks:
        latest = get_latest_reading(tank.id, db)
        result.append(
            schemas.TankResponse(
                id=tank.id,
                name=tank.name,
                location=tank.location,
                temp_min=tank.temp_min,
                temp_max=tank.temp_max,
                status=tank.status,
                current_temperature=latest.temperature if latest else None,
                last_reading_at=latest.recorded_at if latest else None,
            )
        )

    return result


@app.get(
    "/api/v1/tanks/{id}/readings",
    response_model=list[schemas.ReadingResponse],
    tags=["Tanks"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def list_tank_readings(
    id: int,
    period: str = Query(default="24h", pattern="^(6h|24h|7d|30d)$"),
    db: Session = Depends(get_db),
):
    get_tank_or_404(id, db)

    since = utc_now() - PERIOD_DELTA[period]

    readings = (
        db.query(models.Reading)
        .filter(
            models.Reading.tank_id == id,
            models.Reading.recorded_at >= since,
        )
        .order_by(models.Reading.recorded_at.asc())
        .all()
    )

    return readings


@app.get(
    "/api/v1/tanks/{id}/status",
    response_model=schemas.TankStatusResponse,
    tags=["Tanks"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def get_tank_status(id: int, db: Session = Depends(get_db)):
    tank = get_tank_or_404(id, db)
    latest = get_latest_reading(id, db)

    temperature = latest.temperature if latest else None
    last_reading_at = latest.recorded_at if latest else None
    status = compute_tank_status(temperature, tank.temp_min, tank.temp_max, last_reading_at)

    active_alerts = (
        db.query(models.Alert)
        .filter(
            models.Alert.tank_id == id,
            models.Alert.resolved_at.is_(None),
        )
        .order_by(models.Alert.fired_at.desc())
        .all()
    )

    return schemas.TankStatusResponse(
        tank_id=tank.id,
        name=tank.name,
        current_temperature=temperature,
        last_reading_at=last_reading_at,
        temp_min=tank.temp_min,
        temp_max=tank.temp_max,
        tank_status=status,
        active_alerts=active_alerts,
    )


@app.patch(
    "/api/v1/tanks/{id}/config",
    response_model=schemas.TankResponse,
    tags=["Tanks"],
    dependencies=[Depends(require_roles("admin"))],
)
def update_tank_config(
    id: int,
    config: schemas.TankConfigUpdate,
    db: Session = Depends(get_db),
):
    tank = get_tank_or_404(id, db)
    updates = config.model_dump(exclude_unset=True)

    pending_min = updates.get("temp_min", tank.temp_min)
    pending_max = updates.get("temp_max", tank.temp_max)

    if pending_min >= pending_max:
        raise HTTPException(
            status_code=400,
            detail="temp_min deve ser menor que temp_max",
        )

    for field, value in updates.items():
        setattr(tank, field, value)

    db.commit()
    db.refresh(tank)

    latest = get_latest_reading(tank.id, db)

    return schemas.TankResponse(
        id=tank.id,
        name=tank.name,
        location=tank.location,
        temp_min=tank.temp_min,
        temp_max=tank.temp_max,
        status=tank.status,
        current_temperature=latest.temperature if latest else None,
        last_reading_at=latest.recorded_at if latest else None,
    )


@app.get(
    "/api/v1/alerts",
    response_model=list[schemas.AlertResponse],
    tags=["Alerts"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def list_alerts(
    status: str | None = Query(default=None, pattern="^(active|resolved)$"),
    tank_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Alert)

    if status == "active":
        query = query.filter(models.Alert.resolved_at.is_(None))
    elif status == "resolved":
        query = query.filter(models.Alert.resolved_at.isnot(None))

    if tank_id is not None:
        query = query.filter(models.Alert.tank_id == tank_id)

    return query.order_by(models.Alert.fired_at.desc()).all()


@app.patch(
    "/api/v1/alerts/{id}/acknowledge",
    response_model=schemas.AlertResponse,
    tags=["Alerts"],
)
def acknowledge_alert(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*PROTECTED_ROLES)),
):
    alert = db.get(models.Alert, id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado")

    alert.acknowledged_by = current_user["id"]
    db.commit()
    db.refresh(alert)

    return alert


@app.post(
    "/api/v1/batches",
    response_model=schemas.BatchResponse,
    status_code=201,
    tags=["Batches"],
    dependencies=[Depends(require_roles("admin", "operador"))],
)
def create_batch(batch: schemas.BatchCreate, db: Session = Depends(get_db)):
    ensure_yeast_profile_exists(batch.yeast_profile_id, db)

    new_batch = models.Batch(**batch.model_dump())
    close_completed_batch(new_batch)

    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    return new_batch

@app.get(
    "/api/v1/batches",
    response_model=list[schemas.BatchResponse],
    tags=["Batches"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def list_batches(
    status: schemas.BatchStatus | None = Query(default=None),
    style: str | None = Query(default=None, min_length=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Batch)

    if status:
        query = query.filter(models.Batch.status == status)

    if style:
        query = query.filter(models.Batch.style.ilike(f"%{style}%"))

    batch_date = func.coalesce(models.Batch.started_at, models.Batch.created_at)

    if date_from:
        query = query.filter(batch_date >= date_from)

    if date_to:
        query = query.filter(batch_date <= date_to)

    return query.order_by(models.Batch.created_at.desc()).all()

@app.get(
    "/api/v1/batches/{id}",
    response_model=schemas.BatchDetailResponse,
    tags=["Batches"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def get_batch(id: int, db: Session = Depends(get_db)):
    batch = get_batch_or_404(id, db)
    return batch_detail_payload(batch)

@app.patch(
    "/api/v1/batches/{id}",
    response_model=schemas.BatchDetailResponse,
    tags=["Batches"],
    dependencies=[Depends(require_roles("admin", "operador"))],
)
def update_batch(id: int, batch_update: schemas.BatchUpdate, db: Session = Depends(get_db)):
    batch = get_batch_or_404(id, db)
    updates = batch_update.model_dump(exclude_unset=True)

    if "yeast_profile_id" in updates:
        ensure_yeast_profile_exists(updates["yeast_profile_id"], db)

    for field, value in updates.items():
        setattr(batch, field, value)

    close_completed_batch(batch)

    if batch.ended_at and batch.started_at and batch.ended_at < batch.started_at:
        raise HTTPException(status_code=400, detail="ended_at deve ser depois de started_at")

    if (
        batch.original_gravity is not None
        and batch.final_gravity is not None
        and batch.final_gravity > batch.original_gravity
    ):
        raise HTTPException(
            status_code=400,
            detail="final_gravity deve ser menor ou igual a original_gravity",
        )

    db.commit()
    db.refresh(batch)

    return batch_detail_payload(batch)

@app.patch(
    "/api/v1/batches/{id}/events",
    response_model=schemas.BatchEventResponse,
    status_code=201,
    tags=["Batches"],
    dependencies=[Depends(require_roles("admin", "operador"))],
)
def create_batch_event(
    id: int,
    event: schemas.BatchEventCreate,
    db: Session = Depends(get_db),
):
    get_batch_or_404(id, db)

    new_event = models.BatchEvent(batch_id=id, **event.model_dump())

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event

@app.post(
    "/api/v1/yeast_profiles",
    response_model=schemas.YeastProfileResponse,
    status_code=201,
    tags=["Yeast Profiles"],
    dependencies=[Depends(require_roles("admin"))],
)
def create_yeast_profile(
    yeast_profile: schemas.YeastProfileCreate,
    db: Session = Depends(get_db),
):
    existing_profile = (
        db.query(models.YeastProfile)
        .filter(models.YeastProfile.name == yeast_profile.name)
        .first()
    )

    if existing_profile:
        raise HTTPException(status_code=400, detail="Perfil de levedura ja existe")

    new_profile = models.YeastProfile(**yeast_profile.model_dump())

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile

@app.get(
    "/api/v1/yeast_profiles",
    response_model=list[schemas.YeastProfileResponse],
    tags=["Yeast Profiles"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def list_yeast_profiles(db: Session = Depends(get_db)):
    return db.query(models.YeastProfile).order_by(models.YeastProfile.name.asc()).all()

@app.get(
    "/api/v1/yeast_profiles/{id}",
    response_model=schemas.YeastProfileResponse,
    tags=["Yeast Profiles"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def get_yeast_profile(id: int, db: Session = Depends(get_db)):
    return get_yeast_profile_or_404(id, db)

@app.patch(
    "/api/v1/yeast_profiles/{id}",
    response_model=schemas.YeastProfileResponse,
    tags=["Yeast Profiles"],
    dependencies=[Depends(require_roles("admin"))],
)
def update_yeast_profile(
    id: int,
    yeast_profile_update: schemas.YeastProfileUpdate,
    db: Session = Depends(get_db),
):
    yeast_profile = get_yeast_profile_or_404(id, db)
    updates = yeast_profile_update.model_dump(exclude_unset=True)

    if "name" in updates:
        existing_profile = (
            db.query(models.YeastProfile)
            .filter(
                models.YeastProfile.name == updates["name"],
                models.YeastProfile.id != id,
            )
            .first()
        )

        if existing_profile:
            raise HTTPException(status_code=400, detail="Perfil de levedura ja existe")

    for field, value in updates.items():
        setattr(yeast_profile, field, value)

    if (
        yeast_profile.attenuation_min is not None
        and yeast_profile.attenuation_max is not None
        and yeast_profile.attenuation_min > yeast_profile.attenuation_max
    ):
        raise HTTPException(
            status_code=400,
            detail="attenuation_min deve ser menor ou igual a attenuation_max",
        )

    if (
        yeast_profile.temperature_min_c is not None
        and yeast_profile.temperature_max_c is not None
        and yeast_profile.temperature_min_c > yeast_profile.temperature_max_c
    ):
        raise HTTPException(
            status_code=400,
            detail="temperature_min_c deve ser menor ou igual a temperature_max_c",
        )

    db.commit()
    db.refresh(yeast_profile)

    return yeast_profile

@app.delete(
    "/api/v1/yeast_profiles/{id}",
    status_code=204,
    tags=["Yeast Profiles"],
    dependencies=[Depends(require_roles("admin"))],
)
def delete_yeast_profile(id: int, db: Session = Depends(get_db)):
    yeast_profile = get_yeast_profile_or_404(id, db)
    linked_batches = db.query(models.Batch).filter(models.Batch.yeast_profile_id == id).count()

    if linked_batches:
        raise HTTPException(
            status_code=400,
            detail="Perfil de levedura esta associado a um ou mais lotes",
        )

    db.delete(yeast_profile)
    db.commit()

    return Response(status_code=204)

@app.get(
    "/batches/{id}/export",
    tags=["Batches"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
@app.get(
    "/api/v1/batches/{id}/export",
    tags=["Batches"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def export_batch(id: int, format: str = Query(default="csv"), db: Session = Depends(get_db)):
    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Formato suportado: csv")

    batch = get_batch_or_404(id, db)
    output = io.StringIO()
    writer = csv.writer(output)
    abv, apparent_attenuation = calculate_batch_stats(batch)

    writer.writerow(["section", "field", "value"])
    writer.writerow(["batch", "id", batch.id])
    writer.writerow(["batch", "name", batch.name])
    writer.writerow(["batch", "style", batch.style])
    writer.writerow(["batch", "status", batch.status])
    writer.writerow(["batch", "fermenter_id", batch.fermenter_id or ""])
    writer.writerow(["batch", "original_gravity", batch.original_gravity or ""])
    writer.writerow(["batch", "final_gravity", batch.final_gravity or ""])
    writer.writerow(["batch", "abv", abv if abv is not None else ""])
    writer.writerow([
        "batch",
        "apparent_attenuation",
        apparent_attenuation if apparent_attenuation is not None else "",
    ])
    writer.writerow(["batch", "started_at", batch.started_at.isoformat() if batch.started_at else ""])
    writer.writerow(["batch", "ended_at", batch.ended_at.isoformat() if batch.ended_at else ""])
    writer.writerow([])
    writer.writerow(["event_id", "event_type", "description", "value", "unit", "occurred_at"])

    for event in batch.events:
        writer.writerow([
            event.id,
            event.event_type,
            event.description,
            event.value if event.value is not None else "",
            event.unit or "",
            event.occurred_at.isoformat(),
        ])

    output.seek(0)
    filename = f"batch-{batch.id}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@app.websocket("/ws/tanks/{id}")
async def tank_readings_websocket(websocket: WebSocket, id: str):
    await websocket_hub.connect(id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await websocket_hub.disconnect(id, websocket)


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    await alerts_hub.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await alerts_hub.disconnect(websocket)
