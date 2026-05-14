import asyncio
import csv
import contextlib
import io
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

import models, schemas, auth
from database import SessionLocal, engine

API_VERSION = os.getenv("API_VERSION", "0.1.0")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PROTECTED_ROLES = ("admin", "operador", "viewer")


def fermenter_readings_channel(fermenter_id: str) -> str:
    return f"fermenters:{fermenter_id}:readings"

def utc_now():
    return datetime.now(timezone.utc)


class FermenterWebSocketHub:
    def __init__(self):
        self.clients = defaultdict(set)
        self.subscribers = {}
        self.lock = asyncio.Lock()
        self.redis = None

    async def connect(self, fermenter_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.clients[fermenter_id].add(websocket)
            if fermenter_id not in self.subscribers:
                self.subscribers[fermenter_id] = asyncio.create_task(self.subscribe(fermenter_id))

    async def disconnect(self, fermenter_id: str, websocket: WebSocket):
        task = None
        async with self.lock:
            self.clients[fermenter_id].discard(websocket)
            if not self.clients[fermenter_id]:
                task = self.subscribers.pop(fermenter_id, None)
                self.clients.pop(fermenter_id, None)

        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def subscribe(self, fermenter_id: str):
        pubsub = self.redis.pubsub()
        channel = fermenter_readings_channel(fermenter_id)

        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self.broadcast(fermenter_id, message["data"])
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()

    async def broadcast(self, fermenter_id: str, message: str):
        async with self.lock:
            clients = list(self.clients.get(fermenter_id, set()))

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
                    self.clients[fermenter_id].discard(client)

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await app.state.redis.ping()
    websocket_hub.redis = app.state.redis

    try:
        yield
    finally:
        await websocket_hub.close()
        await app.state.redis.aclose()

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
    title="Jeagers Backend API",
    version=API_VERSION,
    description="API de autenticacao e ingestao de leituras de dispositivos.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Status da aplicacao."},
        {"name": "Auth", "description": "Cadastro e login de usuarios."},
        {"name": "Readings", "description": "Ingestao de leituras de dispositivos."},
        {"name": "Batches", "description": "Gerenciamento de lotes de fermentacao."},
        {"name": "Yeast Profiles", "description": "Cadastro de perfis de levedura."},
        {"name": "Analytics", "description": "Indicadores de fermentacao."},
    ],
)

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

def calculate_apparent_attenuation(original_gravity: float | None, current_gravity: float | None):
    if original_gravity is None or current_gravity is None or original_gravity <= 1:
        return None

    return round(((original_gravity - current_gravity) / (original_gravity - 1)) * 100, 2)

def find_original_gravity_for_reading(reading: models.Reading, db: Session):
    batch = (
        db.query(models.Batch)
        .filter(
            models.Batch.fermenter_id == reading.fermenter_id,
            models.Batch.original_gravity.isnot(None),
        )
        .filter(
            (models.Batch.started_at.is_(None)) | (models.Batch.started_at <= reading.timestamp)
        )
        .filter((models.Batch.ended_at.is_(None)) | (models.Batch.ended_at >= reading.timestamp))
        .order_by(models.Batch.started_at.desc(), models.Batch.created_at.desc())
        .first()
    )

    return batch.original_gravity if batch else None

def as_aware_utc(value: datetime):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)

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

@app.get("/health", response_model=schemas.HealthResponse, tags=["Health"])
def health():
    return {"status": "ok", "version": API_VERSION}

# Registro
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

# Login
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
    new_reading = models.Reading(**reading.model_dump())

    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)

    payload = schemas.ReadingResponse.model_validate(new_reading).model_dump(mode="json")
    await request.app.state.redis.publish(
        fermenter_readings_channel(new_reading.fermenter_id),
        json.dumps(payload),
    )

    return new_reading

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
    "/api/v1/analytics/speed",
    response_model=list[schemas.FermenterSpeedResponse],
    tags=["Analytics"],
    dependencies=[Depends(require_roles(*PROTECTED_ROLES))],
)
def get_attenuation_speed(
    fermenter_id: str | None = Query(default=None, min_length=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Reading).filter(
        func.lower(models.Reading.metric).in_(["gravity", "specific_gravity", "sg"])
    )

    if fermenter_id:
        query = query.filter(models.Reading.fermenter_id == fermenter_id)

    if date_from:
        query = query.filter(models.Reading.timestamp >= date_from)

    if date_to:
        query = query.filter(models.Reading.timestamp <= date_to)

    readings = query.order_by(models.Reading.fermenter_id.asc(), models.Reading.timestamp.asc()).all()
    grouped_points = defaultdict(list)

    for reading in readings:
        original_gravity = find_original_gravity_for_reading(reading, db)
        grouped_points[reading.fermenter_id].append(
            schemas.FermenterSpeedPoint(
                fermenter_id=reading.fermenter_id,
                timestamp=reading.timestamp,
                gravity=reading.value,
                original_gravity=original_gravity,
                apparent_attenuation=calculate_apparent_attenuation(
                    original_gravity,
                    reading.value,
                ),
            )
        )

    return [
        schemas.FermenterSpeedResponse(fermenter_id=fermenter_id, points=points)
        for fermenter_id, points in grouped_points.items()
    ]

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

@app.websocket("/ws/fermenters/{id}")
async def fermenter_readings_websocket(websocket: WebSocket, id: str):
    await websocket_hub.connect(id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await websocket_hub.disconnect(id, websocket)
