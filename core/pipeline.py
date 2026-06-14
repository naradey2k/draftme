import time
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

from agents.extractor import extract
from agents.optimizer import optimize
from core.llm_client import LLMClient
from core.pdf_reader import read_pdf
from core.renderer import render_pdf
from filters.content_length import ContentLengthFilter
from filters.hallucination import HallucinationFilter
from filters.keyword import KeywordFilter
from filters.runner import run_all
from filters.structure import StructureFilter
from models.config import AppSettings
from models.pipeline import PipelineResult, StatusEvent
from models.resume import HTMLResume


def run_pipeline(
    cv_bytes: bytes,
    cv_filename: str,
    jd_text: str,
    settings: AppSettings,
) -> Generator[StatusEvent, None, PipelineResult]:
    start = time.time()
    trace_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    debug_dir = settings.output_dir / "debug" if settings.debug else None
    client = LLMClient(settings.model, debug=settings.debug, debug_dir=debug_dir)
    validation_filters = [ContentLengthFilter(), StructureFilter(), HallucinationFilter(), KeywordFilter()]

    try:
        yield _trace(trace_id, start, StatusEvent(step="extract", message=f"Starting workflow for {cv_filename}"))
        yield _trace(trace_id, start, StatusEvent(step="extract", message="Extracting text from PDF..."))
        cv_text, _ = read_pdf(cv_bytes)
        _trace_line(trace_id, start, "extract", f"Extracted {len(cv_text)} characters from PDF")

        yield _trace(trace_id, start, StatusEvent(step="extract", message="Parsing CV structure..."))
        cv_data = extract(cv_text, settings)
        cv_data.raw_text = cv_text
        _trace_line(
            trace_id,
            start,
            "extract",
            (
                f"Parsed CV: name={cv_data.name or 'unknown'}, "
                f"experience={len(cv_data.experience)}, education={len(cv_data.education)}, "
                f"skills={len(cv_data.skills)}, projects={len(cv_data.projects)}, "
                f"publications={len(cv_data.publications)}"
            ),
        )

        feedback = ""
        html_resume: HTMLResume | None = None
        report = None
        attempts_used = 0

        for iteration in range(settings.max_iterations):
            attempts_used = iteration + 1
            yield _trace(
                trace_id,
                start,
                StatusEvent(
                step="optimize",
                iteration=iteration,
                message=f"Generating resume (attempt {attempts_used}/{settings.max_iterations})...",
                ),
            )
            html_resume = optimize(cv_data, jd_text, feedback, iteration, client, settings)
            _trace_line(trace_id, start, "optimize", f"Generated {len(html_resume.html)} HTML characters")

            yield _trace(trace_id, start, StatusEvent(step="filter", iteration=iteration, message="Running validation filters..."))
            report = run_all(html_resume, cv_data, jd_text, validation_filters, settings)
            _trace_filter_report(trace_id, start, report)

            if report.hard_failed:
                yield _trace(trace_id, start, StatusEvent(step="error", message="Hallucination detected; aborting."))
                return PipelineResult(
                    success=False,
                    error="Hallucination detected",
                    filter_report=report,
                    iterations_used=attempts_used,
                    debug_dir=debug_dir,
                )

            if report.all_passed:
                yield _trace(trace_id, start, StatusEvent(step="filter", iteration=iteration, message="All filters passed."))
                break

            feedback = report.combined_feedback
            yield _trace(trace_id, start, StatusEvent(step="filter", iteration=iteration, message="Filters failed; retrying with feedback..."))

        if html_resume is None:
            raise RuntimeError("Resume generation did not produce HTML.")

        if not report or not report.all_passed:
            error = "Validation filters did not pass; PDF render skipped."
            yield _trace(trace_id, start, StatusEvent(step="error", message=error))
            return PipelineResult(
                success=False,
                error=error,
                filter_report=report,
                iterations_used=attempts_used,
                debug_dir=debug_dir,
            )

        yield _trace(trace_id, start, StatusEvent(step="render", message="Rendering PDF..."))
        duration = time.time() - start
        pdf_path = render_pdf(
            html_resume,
            cv_data,
            settings,
            input_filename=cv_filename,
            jd_text=jd_text,
            iterations_used=attempts_used,
            all_filters_passed=bool(report and report.all_passed),
            duration_seconds=duration,
        )
        _trace_line(trace_id, start, "render", f"Wrote PDF to {pdf_path}")

        yield _trace(trace_id, start, StatusEvent(step="done", message=f"Done in {attempts_used} attempt(s); {duration:.1f}s"))
        return PipelineResult(
            success=True,
            output_pdf=pdf_path,
            iterations_used=attempts_used,
            filter_report=report,
            debug_dir=debug_dir,
        )
    except Exception as exc:
        yield _trace(trace_id, start, StatusEvent(step="error", message=str(exc)))
        return PipelineResult(success=False, error=str(exc), debug_dir=debug_dir)


def read_uploaded_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, (str, Path)):
        return Path(value).read_bytes()
    if isinstance(value, dict):
        for key in ("path", "name"):
            if value.get(key):
                return Path(value[key]).read_bytes()
    raise ValueError("Could not read uploaded CV file.")


def _trace(trace_id: str, started_at: float, event: StatusEvent) -> StatusEvent:
    _trace_line(trace_id, started_at, event.step, event.message, event.iteration)
    return event


def _trace_filter_report(trace_id: str, started_at: float, report) -> None:
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        score = f"{result.score:.2f}" if isinstance(result.score, int | float) else str(result.score)
        message = f"{result.filter_name}: {status} score={score}"
        if result.feedback:
            message += f" feedback={_compact(result.feedback)}"
        warnings = result.detail.get("warnings") if isinstance(result.detail, dict) else None
        if warnings:
            message += f" warnings={_compact('; '.join(str(item) for item in warnings))}"
        _trace_line(trace_id, started_at, "filter", message)


def _trace_line(
    trace_id: str,
    started_at: float,
    step: str,
    message: str,
    iteration: int | None = None,
) -> None:
    elapsed = time.time() - started_at
    iteration_part = f" iter={iteration + 1}" if iteration is not None else ""
    print(f"[WORKFLOW {trace_id} +{elapsed:06.1f}s] [{step.upper()}]{iteration_part} {message}", flush=True)


def _compact(value: str, limit: int = 300) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
