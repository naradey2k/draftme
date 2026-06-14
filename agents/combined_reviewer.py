import re

import fitz
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.job import JobPosting
from models.resume import HTMLResume


class CombinedReviewResult(BaseModel):
    looks_professional: bool = Field(description="True if resume looks professional")
    visual_issues: list[str] = Field(default_factory=list)
    visual_feedback: str = ""
    keyword_score: float = Field(ge=0.0, le=1.0)
    experience_score: float = Field(ge=0.0, le=1.0)
    education_score: float = Field(ge=0.0, le=1.0)
    overall_fit_score: float = Field(ge=0.0, le=1.0)
    disqualified: bool
    ats_issues: list[str] = Field(default_factory=list)


SCORE_WEIGHTS = {
    "keyword": 0.25,
    "experience": 0.175,
    "education": 0.075,
    "overall_fit": 0.50,
}


SYSTEM_PROMPT = """
You are TalentScreen ATS v4.2, an enterprise applicant tracking system.

Evaluate:
1. Resume text/HTML quality and professionalism
2. ATS fit against the job posting

VISUAL/TEXT QUALITY:
- Clean organization, readable sections, consistent bullet structure
- No broken/mangled text, duplicate sections, or obvious formatting artifacts
- Professional tone, active voice, no slang

ATS SCREENING:
- keyword_score: exact and semantic matches to job requirements/keywords
- experience_score: work history demonstrates required competencies
- education_score: education fit if the role requires it
- overall_fit_score: holistic fit for the role
- disqualified=true only for strong auto-reject reasons

Return all fields.
"""


def pdf_to_image(pdf_bytes: bytes) -> tuple[bytes, int]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_count = len(doc)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        return pix.tobytes("png"), page_count
    finally:
        doc.close()


def combined_review(
    optimized: HTMLResume | str,
    job: JobPosting,
    settings: AppSettings,
    pdf_text: str | None = None,
) -> CombinedReviewResult:
    content = optimized.html if isinstance(optimized, HTMLResume) else optimized
    resume_text = pdf_text or _html_to_text(content)
    agent = Agent(
        build_modal_model(settings),
        output_type=PromptedOutput(CombinedReviewResult, template="Return JSON matching this schema: {schema}"),
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(
        "COMBINED RESUME REVIEW\n\n"
        "=== JOB POSTING ===\n"
        f"Position: {job.title}\n"
        f"Company: {job.company}\n"
        f"Description: {job.description}\n"
        f"Required Skills: {', '.join(job.requirements)}\n"
        f"Keywords: {', '.join(job.keywords)}\n\n"
        "=== RESUME TEXT ===\n"
        f"{resume_text}\n\n"
        "=== RESUME HTML ===\n"
        f"{content[:12000]}"
    )
    return result.output


def compute_ats_score(result: CombinedReviewResult) -> float:
    return (
        result.keyword_score * SCORE_WEIGHTS["keyword"]
        + result.experience_score * SCORE_WEIGHTS["experience"]
        + result.education_score * SCORE_WEIGHTS["education"]
        + result.overall_fit_score * SCORE_WEIGHTS["overall_fit"]
    )


def _html_to_text(html: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

