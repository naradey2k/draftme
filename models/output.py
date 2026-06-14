from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class IndexRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_filename: str
    jd_snippet: str
    output_pdf: str | None = None
    iterations_used: int
    model: str
    all_filters_passed: bool
    duration_seconds: float


class OutputIndex(BaseModel):
    records: list[IndexRecord] = Field(default_factory=list)

    def append_and_save(self, record: IndexRecord, path: Path) -> None:
        self.records.append(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

