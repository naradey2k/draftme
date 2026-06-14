from pydantic import BaseModel, Field


class FilterResult(BaseModel):
    filter_name: str
    passed: bool
    score: float | None = None
    feedback: str = ""
    detail: dict = Field(default_factory=dict)


class FilterReport(BaseModel):
    results: list[FilterResult]
    all_passed: bool
    combined_feedback: str
    hard_failed: bool = False

