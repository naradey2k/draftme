from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.job import JobPosting


SYSTEM_PROMPT = """You are a job posting parser. Extract structured information from job postings.

Extract:
- title: The job title
- company: Company name
- requirements: List of specific requirements (skills, experience, education)
- keywords: Technical keywords, tools, technologies mentioned
- description: Brief summary of the role

Be thorough in extracting keywords - include all technologies, tools, frameworks, methodologies mentioned.
"""


def parse_job_posting(job_text: str, settings: AppSettings) -> JobPosting:
    agent = Agent(
        _build_model(settings),
        output_type=PromptedOutput(JobPosting, template="Return JSON matching this schema: {schema}"),
        instructions=SYSTEM_PROMPT,
    )
    result = agent.run_sync(f"Job posting text:\n\n{job_text}")
    return result.output


def _build_model(settings: AppSettings) -> OpenAIChatModel:
    return build_modal_model(settings)
