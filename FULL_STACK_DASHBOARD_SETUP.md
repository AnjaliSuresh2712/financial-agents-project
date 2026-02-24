# Full-Stack Dashboard Setup

This project now runs with:
- Frontend: React dashboard (`frontend/`)
- Backend: FastAPI API (`backend/`)
- Database: PostgreSQL (`docker-compose.yml`)
- Analysis engine: existing root pipeline (`main.py` + `agents/`)

## 1) Start PostgreSQL (local)

From repo root:

```bash
docker compose up -d postgres
```

Verify DB is healthy:

```bash
docker compose ps
```

## 2) Configure env once (no repeated export)

From repo root:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `.env` (or `backend/.env`) with real keys:
- `OPENAI_API_KEY`
- `FINANCIAL_DATASETS_API_KEY`
- `DATABASE_URL` (default points to local Postgres container)

## 3) Run backend API

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn backend.app.api:app --reload --port 8000
```

Backend endpoints:
- `GET /health`
- `POST /analyze/{ticker}`
- `GET /analysis/{run_id}`
- `GET /analyses?limit=20`

Schema changes:
- Create a new migration:
```bash
python -m alembic -c backend/alembic.ini revision --autogenerate -m "describe change"
```
- Apply migrations:
```bash
python -m alembic -c backend/alembic.ini upgrade head
```

## 4) Run frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:
- `http://localhost:5173`

## 5) How it works

1. Frontend submits ticker to backend.
2. Backend creates a DB row with status `queued`.
3. Background job runs `run_analysis(ticker)`.
4. Backend stores full result in PostgreSQL and updates status.
5. Frontend polls by `run_id` and renders final policy + agent outputs.
