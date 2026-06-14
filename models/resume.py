from pydantic import BaseModel


class HTMLResume(BaseModel):
    html: str
    iteration: int = 0
    model_used: str = ""
    changes: list[str] = []


class OptimizerOutput(BaseModel):
    resume: HTMLResume
    target_company: str | None = None
    target_role: str | None = None
    language: str
