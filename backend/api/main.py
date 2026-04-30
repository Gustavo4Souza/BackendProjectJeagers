import asyncio
import contextlib
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
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
    ],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
