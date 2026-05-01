import asyncio
import contextlib
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy import func
from sqlalchemy.orm import Session

import models, schemas, auth
from database import SessionLocal, engine

API_VERSION = os.getenv("API_VERSION", "0.1.0")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def fermenter_readings_channel(fermenter_id: str) -> str:
    return f"fermenters:{fermenter_id}:readings"


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
    ],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "Usuário criado com sucesso"}

# Login
@app.post("/login", tags=["Auth"])
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    if not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Senha incorreta")

    return {"msg": "Login realizado com sucesso"}

@app.post("/api/v1/readings", response_model=schemas.ReadingResponse, status_code=201, tags=["Readings"])
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

@app.post("/api/v1/batches", response_model=schemas.BatchResponse, status_code=201, tags=["Batches"])
def create_batch(batch: schemas.BatchCreate, db: Session = Depends(get_db)):
    ensure_yeast_profile_exists(batch.yeast_profile_id, db)

    new_batch = models.Batch(**batch.model_dump())
    close_completed_batch(new_batch)

    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    return new_batch

@app.get("/api/v1/batches", response_model=list[schemas.BatchResponse], tags=["Batches"])
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

@app.get("/api/v1/batches/{id}", response_model=schemas.BatchDetailResponse, tags=["Batches"])
def get_batch(id: int, db: Session = Depends(get_db)):
    batch = get_batch_or_404(id, db)
    return batch_detail_payload(batch)

@app.patch("/api/v1/batches/{id}", response_model=schemas.BatchDetailResponse, tags=["Batches"])
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
)
def list_yeast_profiles(db: Session = Depends(get_db)):
    return db.query(models.YeastProfile).order_by(models.YeastProfile.name.asc()).all()

@app.get(
    "/api/v1/yeast_profiles/{id}",
    response_model=schemas.YeastProfileResponse,
    tags=["Yeast Profiles"],
)
def get_yeast_profile(id: int, db: Session = Depends(get_db)):
    return get_yeast_profile_or_404(id, db)

@app.patch(
    "/api/v1/yeast_profiles/{id}",
    response_model=schemas.YeastProfileResponse,
    tags=["Yeast Profiles"],
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

@app.delete("/api/v1/yeast_profiles/{id}", status_code=204, tags=["Yeast Profiles"])
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
