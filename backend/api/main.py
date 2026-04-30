import os

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models, schemas, auth
from database import SessionLocal, engine

API_VERSION = os.getenv("API_VERSION", "0.1.0")

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Jeagers Backend API",
    version=API_VERSION,
    description="API de autenticacao e ingestao de leituras de dispositivos.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
def create_reading(reading: schemas.ReadingCreate, db: Session = Depends(get_db)):
    new_reading = models.Reading(**reading.model_dump())

    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)

    return new_reading
