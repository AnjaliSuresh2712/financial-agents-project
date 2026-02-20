from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalysisCreateResponse(BaseModel):
    run_id: str
    ticker: str
    status: str


class AnalysisSummaryResponse(BaseModel):
    run_id: str
    ticker: str
    status: str
    created_at: datetime
    updated_at: datetime


class AnalysisStatusResponse(AnalysisSummaryResponse):
    result: dict[str, Any] | None = None
    error: str | None = None
