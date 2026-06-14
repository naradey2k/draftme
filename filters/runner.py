from filters.base import Filter
from models.config import AppSettings
from models.cv import CVData
from models.filters import FilterReport
from models.resume import HTMLResume


def run_all(
    html_resume: HTMLResume,
    cv_data: CVData,
    jd_text: str,
    filters: list[Filter],
    settings: AppSettings | None = None,
) -> FilterReport:
    results = []
    for item in sorted(filters, key=lambda x: x.priority):
        result = item.run(html_resume.html, cv_data, jd_text, settings)
        results.append(result)
        if not result.passed and item.hard_fail:
            return FilterReport(
                results=results,
                all_passed=False,
                combined_feedback=result.feedback,
                hard_failed=True,
            )
    all_passed = all(result.passed for result in results)
    combined = "\n".join(result.feedback for result in results if not result.passed)
    return FilterReport(results=results, all_passed=all_passed, combined_feedback=combined)
