from __future__ import annotations

from datetime import datetime

from .db import SessionLocal
from .models import AnalysisRun


def run_analysis_job(run_id: str, ticker: str) -> None:
    """Background task that runs the existing analysis pipeline and persists output."""
    db = SessionLocal()
    try:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            return

        run.status = "running"
        run.updated_at = datetime.utcnow()
        db.commit()

        from main import run_analysis

        result = run_analysis(ticker)
        run.status = "completed"
        run.result_json = result
        run.error = None
        run.updated_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        run = db.get(AnalysisRun, run_id)
        if run is not None:
            run.status = "failed"
            run.error = str(exc)
            run.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
