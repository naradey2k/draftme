from collections.abc import Iterable
import re
from typing import TypeVar

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import PromptedOutput

from agents.modal_model import build_modal_model
from models.config import AppSettings
from models.cv import CVData, Contact, Education, Experience, Project, SkillsData, WorkExperience


_SUMMARY_PROMPT = """Extract career summaries from the document.
Include: professional headlines, "About" / LinkedIn summaries, career objective statements.
Each distinct paragraph = one list entry. Return [] if none found.
Do not invent anything not explicitly stated."""

_EXPERIENCE_PROMPT = """Extract work experience entries from the document.
Each distinct role = one entry: employer, title, start date, end date, bullet points.
Preserve exact dates, company names, and metrics as written.
Return [] if none found. Do not invent anything."""

_EDUCATION_PROMPT = """Extract education entries from the document.
Each degree or program = one entry: institution, degree, field, start/end dates, notes (GPA, honors, coursework).
Return [] if none found. Do not invent anything."""

_SKILLS_PROMPT = """Extract skills from the document into four categories:
- technical: programming languages, frameworks, tools, cloud platforms, databases
- languages: spoken/written human languages (English, Russian, etc.)
- certifications: ONLY named credentials, licenses, certificates, or exams explicitly listed as certifications (e.g. "AWS Certified Developer 2022", "PMP", "CPA"). Do NOT put job duties, experience bullets, projects, employers, roles, or education here.
- awards: prizes, honors, recognition
Return empty lists for absent categories. Do not invent anything."""

_PROJECTS_PROMPT = """Extract side projects, open-source work, and research projects.
Each project: name, short description, URL only if explicitly written in the document, key bullet points.
Return [] if none found.
STRICT: Do NOT construct or infer URLs — only copy URLs that appear verbatim in the document text."""

_PUBLICATIONS_PROMPT = """Extract publications, papers, patents, and articles.
One free-form string per item: authors, title, venue, year — and include the DOI at the end in parentheses if present in the document, e.g. "(DOI: 10.xxxx/xxxx)".
Return [] if none found. Do not invent anything.
STRICT: Do NOT include work experience bullet points, project bullet points, job achievements, repositories, dashboards, or internal tools unless they are explicitly listed as publications, papers, patents, or articles."""

_CONTACT_PROMPT = """Extract personal contact information from the document.
- name: full name of the candidate as written (first + last)
- email: email address
- phone: phone number (any format)
- linkedin: LinkedIn profile URL (full URL or linkedin.com/in/...)
- github: GitHub profile URL or username (full URL or github.com/...)
- website: personal website or portfolio URL
- other_links: ONLY URLs that are explicitly written in the document verbatim — do NOT construct or infer URLs from names or usernames

STRICT RULES:
- Return null for any field not explicitly present in the document
- NEVER construct a URL by combining a username with a domain (e.g. do NOT write github.com/user/project unless that exact URL appears in the text)
- other_links must only contain URLs copied verbatim from the document"""

_BASE_INSTRUCTIONS = (
    "You extract structured facts from CV text. Return only data supported by the document. "
    "Do not infer, normalize, summarize beyond the requested shape, or add commentary."
)

T = TypeVar("T")


class SummaryOutput(BaseModel):
    items: list[str] = []


class ExperienceOutput(BaseModel):
    items: list[WorkExperience] = []


class EducationOutput(BaseModel):
    items: list[Education] = []


class ProjectsOutput(BaseModel):
    items: list[Project] = []


class PublicationsOutput(BaseModel):
    items: list[str] = []


def extract(cv_text: str, settings: AppSettings) -> CVData:
    model = _build_model(settings)

    contact = _run_agent(model, Contact, _CONTACT_PROMPT, cv_text)
    summaries = _run_agent(model, SummaryOutput, _SUMMARY_PROMPT, cv_text).items
    work_entries = _run_agent(model, ExperienceOutput, _EXPERIENCE_PROMPT, cv_text).items
    education = _run_agent(model, EducationOutput, _EDUCATION_PROMPT, cv_text).items
    skills = _run_agent(model, SkillsData, _SKILLS_PROMPT, cv_text)
    projects = _run_agent(model, ProjectsOutput, _PROJECTS_PROMPT, cv_text).items
    publications = _run_agent(model, PublicationsOutput, _PUBLICATIONS_PROMPT, cv_text).items

    _apply_contact_fallbacks(contact, cv_text)
    name = contact.name or _fallback_name(cv_text)
    return CVData(
        name=name,
        contact=contact,
        summary="\n\n".join(summaries) if summaries else None,
        experience=[_to_legacy_experience(item) for item in work_entries],
        education=education,
        skills=_dedupe(skills.technical),
        certifications=_clean_certifications(skills.certifications, cv_text),
        awards=_dedupe(skills.awards),
        languages=_dedupe(skills.languages),
        projects=projects,
        publications=_clean_publications(publications, cv_text),
        raw_text=cv_text,
    )


def _build_model(settings: AppSettings) -> OpenAIChatModel:
    return build_modal_model(settings)


def _run_agent(model: OpenAIChatModel, output_type: type[T], prompt: str, cv_text: str) -> T:
    agent = Agent(
        model,
        output_type=PromptedOutput(output_type, template="Return JSON matching this schema: {schema}"),
        instructions=f"{_BASE_INSTRUCTIONS}\n\n{prompt}",
    )
    result = agent.run_sync(f"Document text:\n\n{cv_text}")
    return result.output


def _to_legacy_experience(item: WorkExperience) -> Experience:
    return Experience(
        company=item.employer or "",
        title=item.title or "",
        start=item.start_date or "",
        end=item.end_date,
        bullets=item.bullet_points,
    )


def _fallback_name(cv_text: str) -> str:
    for line in cv_text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:120]
    return "Unknown Candidate"


def _apply_contact_fallbacks(contact: Contact, cv_text: str) -> None:
    if not contact.email:
        match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", cv_text)
        if match:
            contact.email = match.group(0)
    if not contact.linkedin:
        match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[^\s|,;]+", cv_text, re.IGNORECASE)
        if match:
            contact.linkedin = match.group(0)
    if not contact.github:
        match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s|,;]+", cv_text, re.IGNORECASE)
        if match:
            contact.github = match.group(0)
    if not contact.website:
        urls = re.findall(r"https?://[^\s|,;]+", cv_text)
        known = {value for value in (contact.linkedin, contact.github) if value}
        for url in urls:
            if url not in known:
                contact.website = url
                break


def _clean_publications(items: Iterable[str], cv_text: str) -> list[str]:
    if not (_has_section_heading(cv_text, ("publications", "publication", "papers", "patents")) or _has_publication_identifier(cv_text)):
        return []

    publications: list[str] = []
    for item in _dedupe(items):
        if _looks_like_experience_bullet(item):
            continue
        if _has_publication_identifier(item) or _looks_like_publication_citation(item):
            publications.append(item)
    return publications


def _clean_certifications(items: Iterable[str], cv_text: str) -> list[str]:
    has_cert_section = _has_section_heading(cv_text, ("certifications", "certification", "certificates", "licenses"))
    certifications: list[str] = []
    for item in _dedupe(items):
        if _looks_like_experience_bullet(item):
            continue
        if _looks_like_certification(item) or has_cert_section and _looks_like_short_named_item(item):
            certifications.append(item)
    return certifications


def _has_section_heading(text: str, headings: tuple[str, ...]) -> bool:
    for line in text.splitlines():
        normalized = re.sub(r"[^a-z]+", " ", line.lower()).strip()
        if normalized in headings:
            return True
    return False


def _has_publication_identifier(text: str) -> bool:
    lowered = text.lower()
    return bool(
        re.search(r"\bdoi\s*:\s*10\.\S+", lowered)
        or re.search(r"\b10\.\d{4,9}/\S+", lowered)
        or re.search(r"\barxiv\s*:?\s*\d", lowered)
        or re.search(r"\bpatent(?:s|ed)?\b", lowered)
    )


def _looks_like_publication_citation(item: str) -> bool:
    lowered = item.lower()
    if any(word in lowered for word in ("journal", "conference", "proceedings", "transactions", "published", "publication")):
        return True
    return bool(re.search(r"\b(?:19|20)\d{2}\b", item) and re.search(r"[“\"].+[”\"]", item))


def _looks_like_certification(item: str) -> bool:
    lowered = item.lower()
    certification_markers = (
        "certified",
        "certification",
        "certificate",
        "license",
        "licence",
        "credential",
        "pmp",
        "cpa",
        "cfa",
        "ccna",
        "cissp",
        "aws certified",
        "azure certified",
        "google cloud certified",
    )
    return any(marker in lowered for marker in certification_markers) and _looks_like_short_named_item(item)


def _looks_like_short_named_item(item: str) -> bool:
    words = item.split()
    return 1 <= len(words) <= 12 and len(item) <= 120


def _looks_like_experience_bullet(item: str) -> bool:
    normalized = item.strip()
    lowered = normalized.lower()
    if not normalized:
        return False
    if len(normalized.split()) > 14:
        return True
    if re.search(r"\b(?:built|developed|created|implemented|managed|led|improved|deployed|maintained|designed|worked|processed|optimized|reduced|increased|delivered|collaborated)\b", lowered):
        return True
    if re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b\s*[-–]\s*(?:present|\d{4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", lowered):
        return True
    return False


def _dedupe(items: Iterable[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = " ".join(item.split())
        key = normalized.lower()
        if normalized and key not in seen:
            values.append(normalized)
            seen.add(key)
    return values
