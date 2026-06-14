import re

from rapidfuzz import fuzz

from agents.hallucination_detector import detect_hallucinations
from filters.base import Filter
from models.config import AppSettings
from models.cv import CVData
from models.filters import FilterResult


class HallucinationFilter(Filter):
    name = "hallucination"
    priority = 2
    hard_fail = True
    threshold = 0.5

    def run(self, html: str, cv_data: CVData, jd_text: str, settings: AppSettings | None = None) -> FilterResult:
        optimized_text = _html_to_text(html)
        if settings is None:
            return _heuristic_result(optimized_text, cv_data, jd_text)

        try:
            return detect_hallucinations(optimized_text, cv_data.raw_text, settings, job_text=jd_text, no_shame=True)
        except Exception as exc:
            fallback = _heuristic_result(optimized_text, cv_data, jd_text)
            fallback.feedback = f"Verifier agent failed; used heuristic fallback. Error: {exc}\n{fallback.feedback}".strip()
            fallback.detail["verifier_error"] = str(exc)
            return fallback


def _html_to_text(html: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _heuristic_result(text: str, cv_data: CVData, jd_text: str) -> FilterResult:
    claims = _extract_claims(_strip_style_noise(text))
    flagged = []
    evidence = _build_evidence_text(cv_data)
    for claim in claims:
        claim = _collapse_repeated_claim(claim)
        if _is_ignorable_claim(claim, jd_text):
            continue
        score = fuzz.partial_ratio(claim.lower(), evidence.lower())
        if score < 85:
            flagged.append({"claim": claim, "score": score})
    feedback = ""
    if flagged:
        feedback = "Potential unsupported claims found:\n" + "\n".join(
            f"- {item['claim']} ({item['score']:.0f})" for item in flagged[:20]
        )
    return FilterResult(
        filter_name="hallucination",
        passed=not flagged,
        score=1.0 if not flagged else 0.0,
        feedback=feedback,
        detail={"flagged": flagged[:50], "mode": "heuristic"},
    )


def _extract_claims(text: str) -> list[str]:
    patterns = [
        r"\b(?:[A-Z][a-zA-Z&.-]+(?:\s+[A-Z][a-zA-Z&.-]+){1,3})\b",
        r"\b\d+(?:[.,]\d+)?%?\b",
        r"\b(?:19|20)\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)?\d{2,4}\b",
    ]
    claims: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, text):
            claim = match.strip()
            if _is_noisy_claim_candidate(claim):
                continue
            if len(claim) < 3 or claim.lower() in seen:
                continue
            seen.add(claim.lower())
            claims.append(claim)
    return claims


def _strip_style_noise(text: str) -> str:
    style_words = ("Arial", "Calibri", "Georgia", "Helvetica", "Times New Roman", "font", "margin", "padding", "color", "border")
    cleaned = text
    for word in style_words:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned)


def _is_noisy_claim_candidate(claim: str) -> bool:
    lowered_words = [word.lower().strip(".") for word in claim.split()]
    section_words = {
        "experience",
        "education",
        "skills",
        "projects",
        "summary",
        "profile",
        "contact",
        "work",
        "professional",
        "technical",
        "languages",
        "certifications",
        "certification",
        "awards",
        "publications",
    }
    if any(word in section_words for word in lowered_words):
        return True
    if all(len(word) <= 3 for word in lowered_words):
        return True
    return False


def _build_evidence_text(cv_data: CVData) -> str:
    parts = [cv_data.raw_text, cv_data.name]
    contact = cv_data.contact
    parts.extend(value for value in (contact.name, contact.email, contact.phone, contact.linkedin, contact.github, contact.website, contact.location) if value)
    parts.extend(contact.other_links)
    if cv_data.summary:
        parts.append(cv_data.summary)
    for experience in cv_data.experience:
        parts.extend([experience.company, experience.title, experience.start, experience.end or ""])
        parts.extend(experience.bullets)
    for education in cv_data.education:
        parts.extend([education.institution, education.degree, education.field or "", education.start_date or "", education.end_date or "", education.year or ""])
        parts.extend(education.notes)
    parts.extend(cv_data.skills)
    parts.extend(cv_data.certifications)
    parts.extend(cv_data.awards)
    parts.extend(cv_data.languages)
    for project in cv_data.projects:
        parts.extend([project.name or "", project.short_description or "", project.url or ""])
        parts.extend(project.key_bullet_points)
    parts.extend(cv_data.publications)
    return "\n".join(part for part in parts if part)


def _is_ignorable_claim(claim: str, jd_text: str) -> bool:
    normalized = claim.strip()
    lowered = normalized.lower()
    generic_claims = {
        "experience",
        "education",
        "skills",
        "projects",
        "summary",
        "profile",
        "contact",
        "work experience",
        "professional experience",
        "technical skills",
        "languages",
        "certifications",
        "present",
        "resume",
        "cv",
        "senior",
        "engineer",
        "software engineer",
        "arial",
        "calibri",
        "georgia",
        "helvetica",
    }
    if lowered in generic_claims:
        return True
    if len(normalized) <= 3:
        return True
    if lowered in jd_text.lower():
        return True
    if normalized.isdigit() and len(normalized) < 4:
        return True
    return False


def _collapse_repeated_claim(claim: str) -> str:
    words = claim.split()
    if len(words) % 2 != 0:
        return claim
    midpoint = len(words) // 2
    if words[:midpoint] == words[midpoint:]:
        return " ".join(words[:midpoint])
    return claim
