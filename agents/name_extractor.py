from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings


class ExtractedName(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    language_code: str = "en"


SYSTEM_PROMPT = """Extract the person's name from this resume/CV content.

Return:
- first_name: The person's first/given name
- last_name: The person's last/family name (may include middle names)

If you cannot find a name, return null for both fields.
Handle any format: LaTeX, plain text, markdown, HTML, etc.
Ignore formatting commands - extract the actual name text only.
"""


def extract_name(content: str, settings: AppSettings) -> tuple[str | None, str | None, str]:
    agent = Agent(
        build_modal_model(settings),
        output_type=PromptedOutput(ExtractedName, template="Return JSON matching this schema: {schema}"),
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(f"Extract the name from this resume:\n\n{content[:3000]}")
    output = result.output
    return output.first_name, output.last_name, output.language_code

