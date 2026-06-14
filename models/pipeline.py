from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from models.filters import FilterReport


class StatusEvent(BaseModel):
    step: Literal["extract", "optimize", "filter", "render", "done", "error"]
    iteration: int | None = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineResult(BaseModel):
    success: bool
    output_pdf: Path | None = None
    iterations_used: int = 0
    filter_report: FilterReport | None = None
    error: str | None = None
    debug_dir: Path | None = None

