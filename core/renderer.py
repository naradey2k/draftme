import json
import os
import platform
import re
from datetime import datetime
from pathlib import Path

from models.config import AppSettings
from models.cv import CVData
from models.output import IndexRecord, OutputIndex
from models.resume import HTMLResume

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_pdf(
    html_resume: HTMLResume,
    cv_data: CVData,
    settings: AppSettings,
    input_filename: str = "",
    jd_text: str = "",
    iterations_used: int = 0,
    all_filters_passed: bool = False,
    duration_seconds: float = 0.0,
) -> Path:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%m%d_%H%M")
    name = _slugify(cv_data.name or "resume")
    filename = f"{timestamp}_{name}_{settings.language}.pdf"
    output_path = settings.output_dir / filename

    try:
        _ensure_homebrew_library_path()
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(f"WeasyPrint system dependencies are missing: {exc}") from exc

    html_document = _wrap_resume_html(html_resume.html)
    HTML(string=html_document).write_pdf(output_path)

    if settings.debug:
        debug_dir = settings.output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"iter_{html_resume.iteration}.html").write_text(html_document, encoding="utf-8")

    record = IndexRecord(
        input_filename=input_filename,
        jd_snippet=jd_text[:300],
        output_pdf=str(output_path),
        iterations_used=iterations_used,
        model=settings.model.name,
        all_filters_passed=all_filters_passed,
        duration_seconds=duration_seconds,
    )
    index_path = settings.output_dir / "index.json"
    index = _load_index(index_path)
    index.append_and_save(record, index_path)
    return output_path


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "resume"


def _wrap_resume_html(html: str) -> str:
    if re.search(r"<\s*html[\s>]", html, re.IGNORECASE):
        return html
    wrapper_path = TEMPLATE_DIR / "resume_wrapper.html"
    if not wrapper_path.exists():
        return f"<!doctype html><html><body>{html}</body></html>"
    wrapper = wrapper_path.read_text(encoding="utf-8")
    return wrapper.replace("{{HEADER}}", "").replace("{{BODY}}", html)


def _ensure_homebrew_library_path() -> None:
    if platform.system() != "Darwin":
        return
    homebrew_lib = "/opt/homebrew/lib"
    if not Path(homebrew_lib).exists():
        homebrew_lib = "/usr/local/lib"
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    paths = [path for path in existing.split(":") if path]
    if homebrew_lib not in paths:
        paths.insert(0, homebrew_lib)
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(paths)


def _load_index(path: Path) -> OutputIndex:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return OutputIndex()
    return OutputIndex.model_validate(json.loads(path.read_text(encoding="utf-8")))
