import re
import tempfile
from html.parser import HTMLParser

from core.renderer import _ensure_homebrew_library_path, _wrap_resume_html
from filters.base import Filter
from models.config import AppSettings
from models.cv import CVData
from models.filters import FilterResult


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


class StructureFilter(Filter):
    name = "structure"
    priority = 1
    min_words = 300
    ideal_min_words = 400
    max_words = 750

    def run(self, html: str, cv_data: CVData, jd_text: str, settings: AppSettings | None = None) -> FilterResult:
        parser = _TextExtractor()
        parser.feed(html)
        text = re.sub(r"\s+", " ", parser.text).strip()
        lowered = text.lower()
        failures: list[str] = []

        if not any(keyword in lowered for keyword in ("experience", "work")):
            failures.append("Missing Experience/Work section.")
        if "education" not in lowered:
            failures.append("Missing Education section.")
        if "skills" not in lowered:
            failures.append("Missing Skills section.")
        if any(marker.lower() in lowered for marker in ("[your name]", "lorem ipsum", "insert")):
            failures.append("Contains placeholder text.")

        word_count = len(re.findall(r"\b\w+\b", text))
        warnings: list[str] = []
        if word_count < self.min_words:
            failures.append(f"Word count is too low; expected at least {self.min_words}, got {word_count}.")
        elif word_count < self.ideal_min_words:
            warnings.append(f"Resume is concise ({word_count} words); ideal range starts around {self.ideal_min_words}.")
        elif word_count > self.max_words:
            failures.append(f"Word count is too high; expected at most {self.max_words}, got {word_count}.")

        page_count = None
        try:
            _ensure_homebrew_library_path()
            from pypdf import PdfReader
            from weasyprint import HTML

            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                HTML(string=_wrap_resume_html(html)).write_pdf(tmp.name)
                page_count = len(PdfReader(tmp.name).pages)
            if page_count != 1:
                failures.append(f"Rendered PDF must be exactly 1 page; got {page_count}.")
        except Exception as exc:
            failures.append(f"Could not render HTML to PDF: {exc}")

        return FilterResult(
            filter_name=self.name,
            passed=not failures,
            score=_word_count_score(word_count, self.min_words, self.ideal_min_words, self.max_words) if not failures else 0.0,
            feedback="\n".join(failures),
            detail={"word_count": word_count, "page_count": page_count, "warnings": warnings},
        )


def _word_count_score(word_count: int, min_words: int, ideal_min_words: int, max_words: int) -> float:
    if ideal_min_words <= word_count <= max_words:
        return 1.0
    if min_words <= word_count < ideal_min_words:
        return max(0.75, word_count / ideal_min_words)
    return 0.0
