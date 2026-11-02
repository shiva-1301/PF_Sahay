# PF Sahay

AI copilot that diagnoses rejected EPF (Employees' Provident Fund) claims and generates the documents to fix them — employer correction letters, EPFiGMS grievances, RTI applications and Joint Declaration checklists.

Built for Indiathon 2026 (E-Cell IIIT Bhubaneswar × LearnApart), "Build Your MVP – 14 Day Challenge".

## Repository layout

```
backend/           # FastAPI app (Python)
frontend/          # Next.js 14 single-page app (TypeScript + Tailwind)
scripts/           # dev runners and data helpers
datasets/          # all source data for the corpus, classifier and templates (see datasets/DATASETS.md)
docs/              # decisions, architecture, privacy, metrics
```

## Run locally

You need **Python 3.11+** and **Node.js 18+** installed.

1. Copy the example settings and add your Anthropic key (optional — without it the app uses canned explanations):
   ```bash
   cp .env.example .env        # then edit .env and fill in ANTHROPIC_KEY
   ```
2. Install the backend (one time):
   ```bash
   python -m venv .venv
   # Windows:        .venv\Scripts\pip install -r backend/requirements.txt
   # macOS / Linux:  .venv/bin/pip install -r backend/requirements.txt
   ```
3. Install the frontend (one time):
   ```bash
   cd frontend && npm install && cd ..
   ```
4. Start both servers:
   - macOS / Linux / WSL: `make dev`
   - Windows (Git Bash): `bash scripts/dev.sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`
5. Open http://localhost:3000. The API runs on http://localhost:8000 (`/health` should say `ok`).

Run the backend tests with `make test` (or `cd backend && ../.venv/Scripts/python -m pytest` on Windows).

## Pipeline (planned)

1. Capture — paste rejection text or upload a screenshot (OCR).
2. Strip PII — Aadhaar, PAN, bank, mobile and UAN numbers removed before anything leaves the server.
3. Classify — deterministic rules map the remark to one of 10 root-cause codes (`datasets/rejection_remarks/taxonomy_v1.yaml`).
4. Explain — LLM explains in plain language, citing only supplied EPFO circular chunks.
5. Generate — Jinja2 templates render ready-to-submit PDFs.

## Disclaimer

PF Sahay produces AI-assisted drafts for the user to verify before submission. It is not legal advice and does not guarantee claim approval. It never asks for UAN passwords or stores Aadhaar/PAN/bank numbers.
