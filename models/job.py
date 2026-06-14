from pydantic import BaseModel


class JobPosting(BaseModel):
    title: str | None = None
    company: str | None = None
    requirements: list[str] = []
    keywords: list[str] = []
    description: str | None = None

