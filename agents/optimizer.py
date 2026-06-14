import logging
import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.cv import CVData
from models.resume import HTMLResume

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class OptimizerResult(BaseModel):
    html: str
    changes: list[str] = []


def _load_resume_guide() -> str:
    guide_path = TEMPLATE_DIR / "resume_guide.md"
    if not guide_path.exists():
        return ""
    return guide_path.read_text(encoding="utf-8")


OPTIMIZER_BASE = r"""
You are a resume optimization expert. Use the parsed resume data and create optimized HTML for a job posting.

INPUT: Parsed candidate resume JSON and job posting text.

OUTPUT: Generate HTML for the <body> of a resume PDF. Do NOT include <html>, <head>, or <body> tags - only the body content.

CONTENT RULES:
- When describing job experiences, show concrete results: focus on impact, not tasks.
- Include specific technologies within achievement descriptions.
- Feature keywords matching job requirements IF they exist in the original resume. You can add umbrella terms if relevant (e.g. if user was making transformer LLM models you can add "NLP").
- Prioritize and highlight experiences most relevant to the role.
- If going over one page: remove unrelated content to save space.
- Remove obvious skills (Excel, VS Code, Jupyter, GitHub, Jira) unless specifically required by job or very relevant to it.
- Exclude: location, language proficiency, age, hobbies unless required by job posting.
- Add a summary section highlighting the most relevant experiences.
- Try to preserve the original writing style if possible.
- Avoid leaving empty space at the bottom of the page if useful relevant content can fill it.
- PROJECTS: Only include projects directly relevant to this job. Skip projects already listed under Publications. If no projects are relevant, omit the section.
- PUBLICATIONS: Always use "PUBLICATIONS" as the section title when publications are present.
- EDUCATION: By default include only the most recent / highest degree. Include multiple degrees only if both are relevant.

{content_rules}

CONTENT BUDGET:
- Target: about 500 words and about 4000 characters.
- The pipeline will validate length, structure, keyword coverage, hallucination risk, and renderability after you return.
- If previous feedback is provided, make the smallest possible change to address that feedback.

LINKS:
- Preserve contact info from the original and never delete it.
- Preserve URLs from the original resume: email, LinkedIn, GitHub, website, project links.
- Use full URLs (include https://) in the href attribute of every <a> tag.
- Link display text must NOT start with https:// or http://. Show just the domain+path.

PUBLICATIONS:
- Always append the DOI in parentheses at the end if available, e.g. "Author et al., Title, Venue Year (DOI: 10.xxxx/xxxx)".

TEMPLATE AND CSS:
- Use the provided template guide and CSS classes exactly where possible.
- Prefer semantic tags from the guide: header.header, h1.name, div.contact-line, section.section, h2.section-title, div.entry, ul.bullets, div.skills-list, ul.simple-list.
- You MUST include a header with the candidate name and available contact links.
- Do not emit Markdown.
- Do not emit wrapper tags.
- The guide examples are FORMAT EXAMPLES ONLY. Never copy example facts from the guide, including fake GPA, Dean's List, dates, companies, emails, URLs, projects, certifications, or publication titles.
- For education notes, include GPA, honors, coursework, or awards ONLY if they appear in the parsed resume JSON or original resume text.

{resume_guide}
"""

OPTIMIZER_STRICT_RULES = """
ALLOWED:
- You CAN add related technologies plausible from context (e.g. Python user likely knows pip, venv; React user likely knows npm, webpack).
- General/umbrella terms inferable from context: "NLP" if they did text processing, "SQL" if they used databases.
- Rephrasing metrics with same values: "1% - 10%" -> "1-10%", "$10k" -> "$10,000".
- Reordering and emphasizing existing content.

STRICT RULES - NEVER VIOLATE:
- NEVER add specific named products or platforms absent from the original unless they are a direct, obvious companion to something explicitly present and there is no other way to improve fit.
- NEVER fabricate job titles, companies, degrees, certifications, achievements, publications, patents, awards, or projects.
- NEVER copy example facts from the template guide into the candidate resume.
- NEVER invent metrics, numbers, and achievements not in original.
- Do NOT drop critical work experience or achievements unless they decrease fit.
- Never use the em dash symbol, the word "delve", or other common markers of LLM-generated text.
- NEVER add <script> tags.
- Do not cut critical content if you can cut lower-value content like summary.
"""

OPTIMIZER_LENIENT_RULES = """
ALLOWED:
- You CAN add related technologies plausible from context (e.g. Python user likely knows pip, venv; React user likely knows npm, webpack).
- You CAN extrapolate skills from adjacent experience.
- You CAN make light assumptions about the candidate.
- General/umbrella terms inferable from context: "NLP" if they did text processing, "SQL" if they used databases.
- Rephrasing metrics with same values: "1% - 10%" -> "1-10%".
- Reordering and emphasizing existing content.

STRICT RULES - NEVER VIOLATE:
- NEVER fabricate job titles, companies, degrees, certifications, or achievements.
- NEVER copy example facts from the template guide into the candidate resume.
- NEVER invent metrics, numbers, and achievements not in original.
- Never use the em dash symbol, the word "delve", or other common markers of LLM-generated text.
- NEVER add <script> tags.
- Do not cut critical content if you can cut lower-value content like summary.
"""


def optimize(
    cv_data: CVData,
    jd_text: str,
    feedback: str,
    iteration: int,
    client,
    settings: AppSettings,
) -> HTMLResume:
    agent = Agent(
        _build_model(settings),
        output_type=PromptedOutput(OptimizerResult, template="Return JSON matching this schema: {schema}"),
        instructions=_build_system_prompt(settings),
    )
    result = agent.run_sync(_build_user_prompt(cv_data, jd_text, feedback, iteration, settings)).output
    html = _sanitize_template_examples(result.html, cv_data.raw_text, jd_text)
    return HTMLResume(
        html=html,
        iteration=iteration,
        model_used=settings.model.name,
        changes=result.changes,
    )


def _build_model(settings: AppSettings) -> OpenAIChatModel:
    return build_modal_model(settings)


def _build_system_prompt(settings: AppSettings) -> str:
    content_rules = OPTIMIZER_LENIENT_RULES
    return OPTIMIZER_BASE.format(content_rules=content_rules, resume_guide=_load_resume_guide())


def _build_user_prompt(
    cv_data: CVData,
    jd_text: str,
    feedback: str,
    iteration: int,
    settings: AppSettings,
) -> str:
    prompt = f"""Today's date: {date.today().strftime('%B %Y')}

## Parsed Resume JSON:
{cv_data.model_dump_json(indent=2)}

## Original Resume Text:
{cv_data.raw_text}

## Job Posting:
{jd_text}

## Target:
- Tone: {settings.tone}
- Language: {settings.language}
- Iteration: {iteration}
"""
    if feedback:
        prompt += f"""
## Previous Validation Feedback:
{feedback}

IMPORTANT: This is a refinement iteration. Make the smallest possible change to pass failed filters.
- Do NOT rewrite from scratch.
- Change only what is needed to pass the failed filters.
- Preserve everything that already works.
"""
    prompt += """
Return JSON with:
- html: resume body HTML only, no <html>, <head>, or <body>
- changes: short list of changes made
"""
    return prompt


def _sanitize_template_examples(html: str, source_text: str, jd_text: str) -> str:
    evidence = f"{source_text}\n{jd_text}".lower()
    cleaned = html

    if "gpa" not in evidence and "dean" not in evidence:
        cleaned = re.sub(
            r"\s*<li>\s*GPA:\s*3\.8/4\.0,\s*Dean[’']s List\s*</li>",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    guide_only_terms = [
        "JavaScript",
        "TypeScript",
        "Go",
        "React",
        "Node.js",
        "Django",
        "Kubernetes",
    ]
    for term in guide_only_terms:
        if term.lower() not in evidence:
            cleaned = re.sub(rf"(?<![A-Za-z0-9.+#-]){re.escape(term)}(?![A-Za-z0-9.+#-])", "", cleaned)

    cleaned = re.sub(r",\s*,+", ",", cleaned)
    cleaned = re.sub(r":\s*,\s*", ": ", cleaned)
    cleaned = re.sub(r",\s*(<br>|</)", r"\1", cleaned)
    cleaned = re.sub(r"<ul class=\"bullets\">\s*</ul>", "", cleaned)
    cleaned = re.sub(r"<ul class='bullets'>\s*</ul>", "", cleaned)
    cleaned = re.sub(r"<ul class=\"simple-list\">\s*</ul>", "", cleaned)
    cleaned = re.sub(r"<ul class='simple-list'>\s*</ul>", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned
