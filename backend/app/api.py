from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session

# Load env files before importing DB settings.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend/.env")

from .db import Base, engine, get_db
from .models import AnalysisRun
from .schemas import (
    AnalysisCreateResponse,
    AnalysisStatusResponse,
    AnalysisSummaryResponse,
)
from .service import run_analysis_job


TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,7}$")

app = FastAPI(
    title="Financial Agents API",
    version="0.1.0",
    description="Async API wrapper around the multi-agent financial analysis workflow.",
)

allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def _status_payload(run: AnalysisRun, include_result: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run.id,
        "ticker": run.ticker,
        "status": run.status,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
    if include_result:
        payload["result"] = json.loads(run.result_json) if run.result_json else None
        payload["error"] = run.error
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze/{ticker}", response_model=AnalysisCreateResponse, status_code=202)
def create_analysis(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AnalysisCreateResponse:
    normalized = ticker.strip().upper()
    if not TICKER_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    run = AnalysisRun(ticker=normalized, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(run_analysis_job, run.id, normalized)
    return AnalysisCreateResponse(run_id=run.id, ticker=run.ticker, status=run.status)


@app.get("/analysis/{run_id}", response_model=AnalysisStatusResponse)
def get_analysis(run_id: str, db: Session = Depends(get_db)) -> AnalysisStatusResponse:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return AnalysisStatusResponse(**_status_payload(run, include_result=True))


@app.get("/analyses", response_model=List[AnalysisSummaryResponse])
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[AnalysisSummaryResponse]:
    runs = (
        db.query(AnalysisRun)
        .order_by(desc(AnalysisRun.created_at))
        .limit(limit)
        .all()
    )
    return [AnalysisSummaryResponse(**_status_payload(run, include_result=False)) for run in runs]
