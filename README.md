# API de Login com FastAPI

API simples de autenticação de usuários utilizando Python, com cadastro e login, incluindo armazenamento seguro de senhas com hash.

---

## Tecnologias utilizadas

* Python
* FastAPI
* SQLite
* SQLAlchemy
* Passlib (bcrypt)

---

## Estrutura do projeto

login_api/
│
├── main.py        # Rotas da API
├── database.py    # Conexão com banco
├── models.py      # Modelos (tabelas)
├── schemas.py     # Validação de dados
├── auth.py        # Hash e verificação de senha

---

## Como rodar o projeto

### 1. Clone o repositório

git clone https://github.com/Gustavo4Souza/BackendProjectJeagers.git
cd login-api/login_api

---

### 2. Instale as dependências

python -m pip install fastapi uvicorn sqlalchemy passlib[bcrypt] bcrypt==4.0.1

---

### 3. Execute a API

```
uvicorn main:app --reload
```

---

## Acessar a API

Após iniciar o servidor:

* Swagger UI: http://127.0.0.1:8000/docs

---

## Endpoints

### POST /register

Cria um novo usuário

**Body:**

{
  "username": "usuario",
  "password": "senha"
}

---

### POST /login

Realiza autenticação do usuário

**Body:**

{
  "username": "usuario",
  "password": "senha"
}

---

## Segurança

* Senhas são armazenadas com hash utilizando bcrypt
* Não há armazenamento de senha em texto puro

---

## Testes

Os testes podem ser realizados diretamente pelo Swagger UI:

http://127.0.0.1:8000/docs