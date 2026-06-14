from filters.base import Filter
from models.config import AppSettings
from models.cv import CVData
from models.filters import FilterResult


class ContentLengthFilter(Filter):
    name = "content_length"
    priority = 0

    def run(self, html: str, cv_data: CVData, jd_text: str, settings: AppSettings | None = None) -> FilterResult:
        length = len(html)
        passed = 500 <= length <= 50_000
        feedback = "" if passed else f"HTML length must be between 500 and 50000 characters; got {length}."
        score = min(length / 500, 1.0) if length < 500 else min(50_000 / max(length, 1), 1.0)
        return FilterResult(filter_name=self.name, passed=passed, score=score, feedback=feedback, detail={"length": length})
