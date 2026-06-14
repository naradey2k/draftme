# DraftMe

DraftMe is an AI resume tailoring tool. Upload a PDF resume, paste a job description, choose a model, and generate a targeted one-page resume PDF.

The app extracts structured information from the resume, parses the job posting, optimizes the resume against the role, validates the result, and renders the final HTML to PDF.

## What It Does

- Extracts resume content from uploaded PDFs with PyMuPDF
- Parses job postings into title, company, requirements, keywords, and summary
- Uses Modal-hosted vLLM endpoints for LLM inference
- Lets users choose between Qwen and NVIDIA Nemotron backends
- Runs validation filters for structure, length, hallucination risk, and keyword coverage
- Shows live workflow telemetry while the resume is being generated
- Renders the optimized resume to PDF with WeasyPrint

## Models

DraftMe currently supports:

- Qwen 3.5 27B FP8
- NVIDIA Nemotron 3 Nano 30B BF16

Both models are served through OpenAI-compatible Modal endpoints.

## Stack

- Python 3.11
- Gradio Server with custom HTML, CSS, and JavaScript UI
- FastAPI / ASGI
- Pydantic and Pydantic AI
- OpenAI SDK for Modal vLLM calls
- PyMuPDF for PDF text extraction
- WeasyPrint for PDF rendering
- Jinja2 resume templates

## Deployment

DraftMe runs as a Dockerized ASGI app. The UI can be hosted on Hugging Face Spaces, while model inference is handled by separate Modal-hosted vLLM endpoints.

## Local Run

```bash
uv run --with-requirements requirements.txt uvicorn app:app --host 127.0.0.1 --port 8801
```

Then open:

```text
http://127.0.0.1:8801
```

## Hugging Face Spaces

This project is configured as a Docker Space because it serves a custom ASGI app instead of a standard Gradio Blocks interface.

The container starts with:

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Notes

Generated PDFs are written to the local `output/` directory and are ignored during Space uploads.