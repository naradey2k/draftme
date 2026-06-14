from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.filters import FilterResult
from models.resume import HTMLResume


class AIGeneratedResult(BaseModel):
    is_ai_generated: bool = Field(description="True if resume appears AI-generated")
    ai_probability: float = Field(ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)


SYSTEM_PROMPT = """You detect AI-generated content in resumes.

CRITICAL: Resumes are INTENTIONALLY formulaic. Every resume guide teaches:
- Action Verb + Task + Result pattern
- Consistent bullet structure and length
- Quantified metrics
- Industry keywords
This is GOOD resume writing, NOT AI tells.

FLAG ONLY:
- Fabricated/impossible claims
- Internal contradictions
- Buzzword soup with zero specifics
- Generic filler repeated verbatim
- Hallucinated details

Set is_ai_generated=true ONLY if ai_probability > 0.5.
When listing indicators, quote specific problematic text.
"""


def detect_ai_generated(resume: HTMLResume | str, settings: AppSettings) -> FilterResult:
    content = resume.html if isinstance(resume, HTMLResume) else resume
    agent = Agent(
        build_modal_model(settings),
        output_type=PromptedOutput(AIGeneratedResult, template="Return JSON matching this schema: {schema}"),
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(
        "Analyze this resume text for signs of AI generation while ignoring normal resume conventions.\n\n"
        f"=== RESUME TEXT ===\n{content}\n=== END ==="
    )
    output = result.output
    feedback = ""
    if output.indicators:
        feedback = "AI-generation indicators:\n" + "\n".join(f"- {item}" for item in output.indicators)
    return FilterResult(
        filter_name="ai_generated",
        passed=not output.is_ai_generated,
        score=1.0 - output.ai_probability,
        feedback=feedback,
        detail=output.model_dump(mode="json"),
    )

