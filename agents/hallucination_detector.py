from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.filters import FilterResult
from models.resume import HTMLResume


class HallucinationResult(BaseModel):
    no_hallucination_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score from 0 to 1 where 1.0 = no fabrications, 0.0 = severe fabrications",
    )
    concerns: list[str] = Field(default_factory=list)
    reasoning: str = ""


STRICT_PROMPT = """You are a resume verification specialist.
Compare an ORIGINAL resume with an OPTIMIZED version and return a no_hallucination_score from 0.0 to 1.0.

SCORING GUIDE:
- 1.0: Perfect - all content traceable to original, only rephrasing/restructuring
- 0.9-0.99: Minor acceptable additions (related tech inference, umbrella terms)
- 0.8-0.9: Light assumptions that are reasonable but noticeable
- 0.7-0.8: Questionable additions - somewhat plausible but stretching
- 0.5-0.69: Significant fabrications - claims that may not be true
- 0.0-0.49: Severe fabrications - fake jobs, degrees, major false claims

SERIOUS FABRICATIONS (score below 0.5):
- Fabricated job titles, companies, or employment dates
- Invented degrees, certifications, or institutions
- Made-up metrics with specific numbers not in original
- Fake achievements, publications, or awards
- Completely unrelated technologies
"""

LENIENT_PROMPT = """You are a resume verification specialist. 
Compare an ORIGINAL resume with an OPTIMIZED version and return a no_hallucination_score from 0.0 to 1.0.

SCORING GUIDE:
- 1.0: All content directly traceable to original
- 0.8-0.99: Aggressive skill extrapolations that are plausible from context
- 0.6-0.79: Significant embellishment of achievements, creative reframing
- 0.5-0.59: Very aggressive stretching but still plausible
- 0.0-0.49: Blatant fabrications - fake jobs, degrees, made-up credentials

ACCEPTABLE (score 0.7+):
- Aggressive technology extrapolation: Python user -> any Python library, web dev -> full stack
- Adding plausible tools from job context even if not explicitly stated
- Creative reframing of responsibilities to match job requirements
- Inferring leadership/mentoring from senior roles
- Adding industry-standard practices plausible for their role

BLOCK (score below 0.5):
- Fabricated job titles, companies, or employment dates
- Invented degrees, certifications, or institutions
- Made-up awards, publications, or patents
- Completely fictional projects or achievements
- Technologies with zero connection to stated experience
- Made up specific metrics
"""


def detect_hallucinations(
    optimized: HTMLResume | str,
    original_text: str,
    settings: AppSettings,
    job_text: str = "",
    no_shame: bool = True,
) -> FilterResult:
    optimized_content = optimized.html if isinstance(optimized, HTMLResume) else optimized
    threshold = 0.5 if no_shame else 0.9
    prompt = LENIENT_PROMPT if no_shame else STRICT_PROMPT
    agent = Agent(
        build_modal_model(settings),
        output_type=PromptedOutput(HallucinationResult, template="Return JSON matching this schema: {schema}"),
        instructions=prompt,
    )
    result = agent.run_sync(
        "Compare these two resumes and score the optimized version for hallucinations.\n\n"
        f"=== ORIGINAL RESUME ===\n{original_text}\n\n"
        f"=== JOB POSTING CONTEXT ===\n{job_text}\n\n"
        f"=== OPTIMIZED RESUME ===\n{optimized_content}"
    )
    output = result.output
    passed = output.no_hallucination_score >= threshold
    feedback = ""
    if not passed:
        concerns = "\n".join(f"- {item}" for item in output.concerns)
        feedback = f"Score {output.no_hallucination_score:.2f} below {threshold:.2f}. {output.reasoning}\n{concerns}".strip()
    return FilterResult(
        filter_name="hallucination",
        passed=passed,
        score=output.no_hallucination_score,
        feedback=feedback,
        detail=output.model_dump(mode="json") | {"threshold": threshold},
    )

