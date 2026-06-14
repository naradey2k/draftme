import json
from datetime import datetime
from html import escape
from pathlib import Path

import gradio as gr
from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse

from core.pipeline import run_pipeline
from models.config import AppSettings
from models.pipeline import PipelineResult, StatusEvent


APP_CSS = """
:root {
    color-scheme: light;
    --bg: #f5f6f8;
    --panel: #ffffff;
    --panel-soft: #fbfcfd;
    --ink: #1f242c;
    --muted: #687080;
    --line: #dce1e8;
    --line-strong: #c9d1db;
    --accent: #176b87;
    --accent-dark: #104f65;
    --accent-soft: #e7f3f6;
    --green: #18794e;
    --green-soft: #e7f5ee;
    --amber: #a15c07;
    --amber-soft: #fff4df;
    --red: #bf2c2c;
    --red-soft: #fdecec;
    --shadow: 0 12px 30px rgba(25, 35, 50, 0.08);
}
* {
    box-sizing: border-box;
}
body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
button,
input,
textarea {
    font: inherit;
}
.app {
    width: min(1220px, calc(100vw - 36px));
    margin: 0 auto;
    padding: 28px 0 36px;
}
.topbar {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 28px;
    margin-bottom: 22px;
}
.brand h1 {
    margin: 0;
    font-size: 34px;
    line-height: 1.05;
    letter-spacing: 0;
}
.brand p {
    margin: 8px 0 0;
    color: var(--muted);
}
.settings {
    width: 360px;
    padding: 14px 16px;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: var(--shadow);
}
.setting-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
}
.settings-grid {
    display: grid;
    gap: 14px;
}
.setting-field label {
    display: block;
    margin-bottom: 7px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 800;
}
.model-select {
    width: 100%;
    min-height: 38px;
    padding: 0 12px;
    border: 1px solid var(--line);
    border-radius: 8px;
    color: var(--ink);
    background: #ffffff;
    outline: none;
}
.model-select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(23, 107, 135, 0.15);
}
.range-row {
    display: grid;
    grid-template-columns: 1fr 34px;
    gap: 12px;
    align-items: center;
}
input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
}
.range-value {
    min-height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    color: var(--accent-dark);
    background: var(--accent-soft);
    font-size: 13px;
    font-weight: 800;
}
.workspace {
    display: grid;
    grid-template-columns: 0.78fr 1.22fr;
    gap: 18px;
    align-items: stretch;
}
.panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: var(--shadow);
}
.input-panel {
    padding: 18px;
}
.panel-title {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 800;
}
.icon {
    width: 18px;
    height: 18px;
    stroke: currentColor;
    stroke-width: 2;
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
}
.dropzone {
    position: relative;
    display: grid;
    place-items: center;
    min-height: 158px;
    padding: 20px;
    border: 1.5px dashed var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    transition: border-color 150ms ease, background 150ms ease;
}
.dropzone.dragging {
    border-color: var(--accent);
    background: var(--accent-soft);
}
.dropzone input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
}
.drop-inner {
    text-align: center;
    pointer-events: none;
}
.drop-inner strong {
    display: block;
    margin-bottom: 6px;
}
.file-name {
    color: var(--muted);
    font-size: 13px;
    overflow-wrap: anywhere;
}
.field {
    margin-top: 16px;
}
.field label {
    display: block;
    margin-bottom: 8px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 800;
}
textarea {
    width: 100%;
    min-height: 286px;
    resize: vertical;
    padding: 13px 14px;
    border: 1px solid var(--line);
    border-radius: 8px;
    color: var(--ink);
    background: #ffffff;
    outline: none;
}
textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(23, 107, 135, 0.15);
}
.actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
}
.primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    min-height: 42px;
    padding: 0 18px;
    border: 0;
    border-radius: 8px;
    color: #ffffff;
    background: var(--accent);
    font-weight: 800;
    cursor: pointer;
}
.primary:hover {
    background: var(--accent-dark);
}
.primary:disabled {
    cursor: not-allowed;
    opacity: 0.6;
}
.output-panel {
    display: grid;
    grid-template-rows: auto minmax(300px, 1fr) auto;
    overflow: hidden;
}
.gauge-panel {
    display: grid;
    grid-template-columns: 270px 1fr;
    gap: 18px;
    align-items: center;
    padding: 18px 18px 14px;
    border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, #fbfcfd 0%, #ffffff 100%);
}
.gauge {
    position: relative;
    height: 176px;
}
.gauge svg {
    width: 100%;
    height: 150px;
    display: block;
}
.gauge-track {
    stroke: #e3e8ee;
    stroke-width: 16;
    fill: none;
    stroke-linecap: round;
}
.gauge-fill {
    stroke: var(--accent);
    stroke-width: 16;
    fill: none;
    stroke-linecap: round;
    stroke-dasharray: 100;
    stroke-dashoffset: 100;
    transition: stroke-dashoffset 350ms ease, stroke 200ms ease;
}
.gauge-fill.done {
    stroke: var(--green);
}
.gauge-fill.error {
    stroke: var(--red);
}
.gauge-needle {
    stroke: var(--ink);
    stroke-width: 4;
    stroke-linecap: round;
    transform-origin: 120px 120px;
    transform: rotate(-90deg);
    transition: transform 350ms ease;
}
.gauge-hub {
    fill: var(--panel);
    stroke: var(--ink);
    stroke-width: 4;
}
.gauge-scale {
    position: absolute;
    left: 24px;
    right: 24px;
    bottom: 2px;
    display: flex;
    justify-content: space-between;
    margin: 0;
    color: var(--muted);
    font-size: 12px;
    font-weight: 800;
}
.gauge-readout {
    display: grid;
    gap: 8px;
}
.gauge-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.gauge-value {
    font-size: 42px;
    line-height: 1;
    font-weight: 900;
    letter-spacing: 0;
    font-variant-numeric: tabular-nums;
}
.gauge-stage {
    color: var(--muted);
    font-weight: 800;
}
.telemetry-title {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 14px;
    font-weight: 900;
}
.status-pill {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    padding: 0 10px;
    border-radius: 999px;
    color: var(--accent-dark);
    background: var(--accent-soft);
    font-size: 12px;
    font-weight: 900;
}
.status-pill.done {
    color: var(--green);
    background: var(--green-soft);
}
.status-pill.error {
    color: var(--red);
    background: var(--red-soft);
}
.telemetry-body {
    height: 100%;
    max-height: 420px;
    overflow-y: auto;
    padding: 12px 16px 18px;
}
.empty-state {
    height: 100%;
    min-height: 360px;
    display: grid;
    place-items: center;
    color: var(--muted);
    text-align: center;
}
.event {
    display: grid;
    grid-template-columns: 92px 112px 1fr;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px solid #edf0f4;
}
.event:last-child {
    border-bottom: 0;
}
.event-time {
    color: var(--muted);
    font-size: 12px;
    line-height: 24px;
    font-variant-numeric: tabular-nums;
}
.event-step {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 24px;
    padding: 0 9px;
    border-radius: 999px;
    color: var(--accent-dark);
    background: var(--accent-soft);
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
}
.event.active .event-step {
    color: var(--amber);
    background: var(--amber-soft);
}
.event.done .event-step {
    color: var(--green);
    background: var(--green-soft);
}
.event.error .event-step {
    color: var(--red);
    background: var(--red-soft);
}
.event-message {
    min-width: 0;
    line-height: 1.45;
    overflow-wrap: anywhere;
}
.event-meta {
    display: inline-flex;
    margin-left: 8px;
    padding: 1px 7px;
    border-radius: 999px;
    color: var(--muted);
    background: #f0f3f6;
    font-size: 12px;
    font-weight: 700;
}
.download-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 74px;
    padding: 14px 16px;
    border-top: 1px solid var(--line);
    background: var(--panel-soft);
}
.download-meta {
    min-width: 0;
}
.download-meta strong {
    display: block;
}
.download-meta span {
    display: block;
    margin-top: 3px;
    color: var(--muted);
    font-size: 13px;
    overflow-wrap: anywhere;
}
.download-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 38px;
    padding: 0 14px;
    border-radius: 8px;
    color: #ffffff;
    background: var(--green);
    text-decoration: none;
    font-weight: 800;
    white-space: nowrap;
}
.download-link.hidden {
    display: none;
}
@media (max-width: 900px) {
    .topbar,
    .workspace {
        display: block;
    }
    .settings {
        width: 100%;
        margin-top: 18px;
    }
    .output-panel {
        margin-top: 18px;
    }
    .gauge-panel {
        grid-template-columns: 1fr;
    }
    .gauge {
        max-width: 320px;
        margin: 0 auto;
        width: 100%;
    }
}
@media (max-width: 680px) {
    .app {
        width: min(100vw - 24px, 1220px);
        padding-top: 18px;
    }
    .brand h1 {
        font-size: 28px;
    }
    .event {
        grid-template-columns: 1fr;
        gap: 5px;
    }
    .event-time {
        line-height: 1.2;
    }
    .download-bar {
        align-items: stretch;
        flex-direction: column;
    }
}
"""


APP_JS = """
const form = document.querySelector("#optimize-form");
const fileInput = document.querySelector("#cv-file");
const fileName = document.querySelector("#file-name");
const dropzone = document.querySelector("#dropzone");
const modelSelect = document.querySelector("#model-select");
const iterations = document.querySelector("#max-iterations");
const iterationValue = document.querySelector("#iteration-value");
const runButton = document.querySelector("#run-button");
const telemetryBody = document.querySelector("#telemetry-body");
const statusPill = document.querySelector("#status-pill");
const downloadLink = document.querySelector("#download-link");
const downloadName = document.querySelector("#download-name");
const gaugeFill = document.querySelector("#gauge-fill");
const gaugeNeedle = document.querySelector("#gauge-needle");
const gaugeValue = document.querySelector("#gauge-value");
const gaugeStage = document.querySelector("#gauge-stage");

const icons = {
    run: '<svg class="icon" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>',
    busy: '<svg class="icon" viewBox="0 0 24 24"><path d="M12 2v4"/><path d="M12 18v4"/><path d="m4.93 4.93 2.83 2.83"/><path d="m16.24 16.24 2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="m4.93 19.07 2.83-2.83"/><path d="m16.24 7.76 2.83-2.83"/></svg>'
};

function setStatus(label, state) {
    statusPill.textContent = label;
    statusPill.className = "status-pill" + (state ? " " + state : "");
    gaugeFill.className.baseVal = "gauge-fill" + (state ? " " + state : "");
}

function clearTelemetry() {
    telemetryBody.innerHTML = '<div class="empty-state">Waiting for workflow events.</div>';
    downloadLink.classList.add("hidden");
    downloadName.textContent = "No PDF generated yet.";
    updateGauge(0, "Ready");
}

function addEvent(event, active) {
    const empty = telemetryBody.querySelector(".empty-state");
    if (empty) empty.remove();
    telemetryBody.querySelectorAll(".event.active").forEach((node) => {
        node.classList.remove("active");
        node.classList.add("done");
    });

    const row = document.createElement("div");
    const state = event.step === "error" ? "error" : active ? "active" : "done";
    row.className = "event " + state;
    const attempt = event.iteration === null || event.iteration === undefined
        ? ""
        : `<span class="event-meta">Attempt ${event.iteration + 1}</span>`;
    row.innerHTML = `
        <div class="event-time">${escapeHtml(event.time)}</div>
        <div><span class="event-step">${escapeHtml(event.step)}</span></div>
        <div class="event-message">${escapeHtml(event.message)}${attempt}</div>
    `;
    telemetryBody.appendChild(row);
    telemetryBody.scrollTop = telemetryBody.scrollHeight;
    updateGauge(progressForEvent(event), event.message);
}

function updateGauge(progress, label) {
    const bounded = Math.max(0, Math.min(100, Math.round(progress)));
    const angle = -90 + bounded * 1.8;
    gaugeFill.style.strokeDashoffset = String(100 - bounded);
    gaugeNeedle.style.transform = `rotate(${angle}deg)`;
    gaugeValue.textContent = `${bounded}%`;
    gaugeStage.textContent = label || "Ready";
}

function progressForEvent(event) {
    const maxIterations = Number(iterations.value || 1);
    const attempt = event.iteration === null || event.iteration === undefined ? 0 : Number(event.iteration);
    const attemptShare = maxIterations <= 1 ? 0 : (attempt / Math.max(maxIterations - 1, 1)) * 24;
    if (event.step === "extract") return event.message.toLowerCase().includes("parsed") ? 24 : 12;
    if (event.step === "optimize") return 34 + attemptShare;
    if (event.step === "filter") return event.message.toLowerCase().includes("all filters") ? 82 : 56 + attemptShare;
    if (event.step === "render") return 90;
    if (event.step === "done") return 100;
    if (event.step === "error") return 100;
    return 8;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function setBusy(isBusy) {
    runButton.disabled = isBusy;
    runButton.innerHTML = isBusy ? `${icons.busy}<span>Running</span>` : `${icons.run}<span>Optimize Resume</span>`;
}

iterations.addEventListener("input", () => {
    iterationValue.textContent = iterations.value;
});

fileInput.addEventListener("change", () => {
    fileName.textContent = fileInput.files[0]?.name || "No file selected";
});

["dragenter", "dragover"].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        dropzone.classList.add("dragging");
    });
});

["dragleave", "drop"].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        dropzone.classList.remove("dragging");
    });
});

dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    fileName.textContent = file.name;
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!fileInput.files[0]) {
        setStatus("Missing PDF", "error");
        return;
    }

    const formData = new FormData(form);
    clearTelemetry();
    setStatus("Running", "");
    setBusy(true);

    try {
        const response = await fetch("/api/optimize", {
            method: "POST",
            body: formData
        });
        if (!response.ok || !response.body) {
            throw new Error(`Request failed with status ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\\n");
            buffer = lines.pop() || "";
            for (const line of lines) {
                if (!line.trim()) continue;
                handleMessage(JSON.parse(line));
            }
        }
        if (buffer.trim()) {
            handleMessage(JSON.parse(buffer));
        }
    } catch (error) {
        addEvent({
            step: "error",
            time: new Date().toLocaleTimeString("en-US", { hour12: false }),
            message: error.message
        }, true);
        setStatus("Error", "error");
    } finally {
        setBusy(false);
    }
});

function handleMessage(message) {
    if (message.type === "event") {
        addEvent(message.event, true);
        return;
    }
    if (message.type === "done") {
        setStatus("Complete", "done");
        updateGauge(100, "Resume PDF ready");
        downloadLink.href = message.download_url;
        downloadLink.classList.remove("hidden");
        downloadName.textContent = message.filename;
        return;
    }
    if (message.type === "error") {
        addEvent({
            step: "error",
            time: new Date().toLocaleTimeString("en-US", { hour12: false }),
            message: message.error
        }, true);
        setStatus("Error", "error");
        updateGauge(100, "Workflow stopped");
    }
}

clearTelemetry();
setBusy(false);
"""


def create_app(settings: AppSettings) -> gr.Server:
    server = gr.Server(title="EZ JOB", docs_url=None, redoc_url=None, openapi_url=None)

    @server.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(_render_page(settings))

    @server.head("/")
    async def index_head() -> Response:
        return Response(status_code=200)

    @server.post("/api/optimize")
    async def optimize(
        cv: UploadFile = File(...),
        jd: str = Form(...),
        model_key: str = Form(...),
        max_iterations: int = Form(...),
    ) -> StreamingResponse:
        cv_bytes = await cv.read()
        if not cv_bytes:
            raise HTTPException(status_code=400, detail="Upload a PDF CV first.")
        if not jd.strip():
            raise HTTPException(status_code=400, detail="Paste a job description first.")

        run_settings = _settings_for_model(settings, model_key, int(max_iterations))
        filename = cv.filename or "resume.pdf"
        return StreamingResponse(
            _run_workflow(cv_bytes, filename, jd, run_settings),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache"},
        )

    @server.get("/download/{filename}")
    async def download(filename: str) -> FileResponse:
        path = _resolve_output_file(settings.output_dir, filename)
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    return server


def _run_workflow(cv_bytes: bytes, filename: str, jd: str, settings: AppSettings):
    pipeline = run_pipeline(cv_bytes, filename, jd, settings)
    final_result: PipelineResult | None = None
    while True:
        try:
            event = next(pipeline)
        except StopIteration as stop:
            final_result = stop.value
            break
        yield _json_line({"type": "event", "event": _event_payload(event)})

    if final_result and final_result.output_pdf:
        yield _json_line(
            {
                "type": "done",
                "filename": final_result.output_pdf.name,
                "download_url": f"/download/{final_result.output_pdf.name}",
            }
        )
        return

    error = final_result.error if final_result else "Pipeline ended without a result."
    yield _json_line({"type": "error", "error": error})


def _settings_for_model(settings: AppSettings, model_key: str, max_iterations: int) -> AppSettings:
    option = settings.model_options.get(model_key)
    if option is None:
        raise HTTPException(status_code=400, detail="Unknown model selection.")
    model = settings.model.model_copy(
        update={
            "name": option.name,
            "base_url": option.base_url,
            "api_key": option.api_key,
        }
    )
    return settings.model_copy(update={"model": model, "max_iterations": max_iterations})


def _event_payload(event: StatusEvent) -> dict:
    return {
        "step": event.step,
        "message": event.message,
        "iteration": event.iteration,
        "time": event.timestamp.strftime("%H:%M:%S"),
    }


def _json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True) + "\n"


def _resolve_output_file(output_dir: Path, filename: str) -> Path:
    root = output_dir.resolve()
    path = (root / filename).resolve()
    if root not in path.parents or not path.exists() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF not found.")
    return path


def _render_page(settings: AppSettings) -> str:
    selected_key = _selected_model_key(settings)
    options = _render_model_options(settings, selected_key)
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>EZ JOB</title>
    <style>{APP_CSS}</style>
</head>
<body>
    <main class="app">
        <header class="topbar">
            <div class="brand">
                <h1>EZ JOB</h1>
                <p>Upload a PDF CV, paste a job description, and generate an ATS-friendly resume.</p>
            </div>
            <section class="settings" aria-label="Settings">
                <div class="settings-grid">
                    <div class="setting-field">
                        <label for="model-select">Model</label>
                        <select id="model-select" class="model-select" name="model_key" form="optimize-form">
                            {options}
                        </select>
                    </div>
                    <div>
                        <div class="setting-head">
                            <span>Max Iterations</span>
                            <span id="iteration-value" class="range-value">{settings.max_iterations}</span>
                        </div>
                        <div class="range-row">
                            <input id="max-iterations" name="max_iterations" form="optimize-form" type="range" min="1" max="6" step="1" value="{settings.max_iterations}">
                            <span></span>
                        </div>
                    </div>
                </div>
            </section>
        </header>

        <section class="workspace">
            <form id="optimize-form" class="panel input-panel">
                <h2 class="panel-title">{_icon_upload()} Inputs</h2>
                <label id="dropzone" class="dropzone">
                    <input id="cv-file" name="cv" type="file" accept="application/pdf,.pdf">
                    <span class="drop-inner">
                        <strong>PDF CV</strong>
                        <span id="file-name" class="file-name">No file selected</span>
                    </span>
                </label>

                <div class="field">
                    <label for="jd">Job Description</label>
                    <textarea id="jd" name="jd" placeholder="Paste the job description here"></textarea>
                </div>

                <div class="actions">
                    <button id="run-button" class="primary" type="submit">
                        {_icon_arrow()} <span>Optimize Resume</span>
                    </button>
                </div>
            </form>

            <section class="panel output-panel">
                <div class="gauge-panel">
                    <div class="gauge" aria-label="Workflow speedometer">
                        <svg viewBox="0 0 240 140" role="img">
                            <path class="gauge-track" pathLength="100" d="M24 120 A96 96 0 0 1 216 120"/>
                            <path id="gauge-fill" class="gauge-fill" pathLength="100" d="M24 120 A96 96 0 0 1 216 120"/>
                            <line id="gauge-needle" class="gauge-needle" x1="120" y1="120" x2="120" y2="48"/>
                            <circle class="gauge-hub" cx="120" cy="120" r="8"/>
                        </svg>
                        <div class="gauge-scale"><span>Start</span><span>PDF</span></div>
                    </div>
                    <div class="gauge-readout">
                        <div class="gauge-title">
                            <div class="telemetry-title">{_icon_activity()} Workflow Telemetry</div>
                        <div id="status-pill" class="status-pill">Ready</div>
                        </div>
                        <div id="gauge-value" class="gauge-value">0%</div>
                        <div id="gauge-stage" class="gauge-stage">Ready</div>
                    </div>
                </div>
                <div id="telemetry-body" class="telemetry-body"></div>
                <div class="download-bar">
                    <div class="download-meta">
                        <strong>Generated PDF</strong>
                        <span id="download-name">No PDF generated yet.</span>
                    </div>
                    <a id="download-link" class="download-link hidden" href="#" download>
                        {_icon_download()} Download
                    </a>
                </div>
            </section>
        </section>
    </main>
    <script>{APP_JS}</script>
</body>
</html>"""


def _icon_upload() -> str:
    return '<svg class="icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>'


def _icon_arrow() -> str:
    return '<svg class="icon" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>'


def _icon_activity() -> str:
    return '<svg class="icon" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>'


def _icon_download() -> str:
    return '<svg class="icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>'


def _selected_model_key(settings: AppSettings) -> str:
    for key, option in settings.model_options.items():
        if option.name == settings.model.name:
            return key
    return next(iter(settings.model_options), "qwen")


def _render_model_options(settings: AppSettings, selected_key: str) -> str:
    parts = []
    for key, option in settings.model_options.items():
        selected = " selected" if key == selected_key else ""
        parts.append(f'<option value="{escape(key)}"{selected}>{escape(option.label)}</option>')
    return "\n".join(parts)
