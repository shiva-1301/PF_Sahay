# Decisions log

One line of reasoning per decision. Newest phase at the bottom.

## Phase 0 — Skeleton

- **Python 3.12 locally, 3.11 in Docker.** Only 3.12 is installed on the dev machine; nothing in the stack needs 3.12-only features, so the code stays 3.11-compatible and the Dockerfile will pin 3.11.
- **No `make` on the Windows dev machine.** A `Makefile` is provided for macOS/Linux/WSL, plus `scripts/dev.sh` (Git Bash) and `scripts/dev.ps1` (PowerShell) that do the same thing.
- **Single venv at repo root (`.venv/`).** Simpler for beginners than one per folder; the dev scripts find it automatically.
- **Env var for the API key is `ANTHROPIC_KEY`** (not the SDK default); loaded from the repo-root `.env` via python-dotenv and passed explicitly to the client.
- **CORS** allows `http://localhost:3000` by default; override with `PFSAHAY_CORS_ORIGINS` for deployment.
- **Downloaded circular PDFs are git-ignored** (only `download_log.csv` is committed) — they are re-fetchable and would bloat the repo.
- **Downloader uses an honest, identifying User-Agent** and does not try to look like a browser.
- **Circular PDF download: 0 of 151 succeeded (2 Nov 2026).** Every `epfindia.gov.in/site_docs/...` link now 301-redirects to the same path on `epfo.gov.in`, which returns 404 — EPFO appears to have reorganised its file paths. The script follows redirects, retries once and logs every result in `datasets/circular_pdfs/epfo/download_log.csv`. We did not scrape for new paths; the corpus falls back to the 4 PDFs in `datasets/circular_pdfs/` plus the OCR first pages in `ocr_first_pages.json`. If someone fetches the PDFs by hand into `datasets/circular_pdfs/epfo/`, `make corpus` picks them up automatically.
