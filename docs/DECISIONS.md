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

## Phase 1 — Corpus

- **Chunk size: 400-word windows, 50-word overlap, minimum 40 words.** The middle of the 300–500 range; most OCR first pages (150–600 words) become one or two chunks, so citations stay specific.
- **Chunk IDs are `C1…Cn` in build order** (PDFs, then JD data, then OCR, then hand-written). They change if the corpus is rebuilt, which is fine because citations are only resolved within one request.
- **Corpus tagging uses `backend/corpus/code_keywords.yaml` alongside the taxonomy triggers.** Taxonomy triggers are written for portal remarks ("kyc details not match") and almost never occur in circular prose, so each code also has circular-language keywords. A chunk gets a code when triggers + keywords score ≥ 2 (a hit in the title counts 2). A single broad trigger like `pension` no longer tags on its own.
- **Curated sources carry hand-assigned codes** (JD data, hand-written chunks, the RTI template PDF); keyword tagging is only applied to circular text (PDF/OCR). The DPDP backgrounder is kept in the corpus but tagged to no code.
- **Staff/admin circulars are excluded** from the OCR source by title pattern (CCS pension, budgets, EDLI, ELI scheme, life certificates, etc. — list in `code_keywords.yaml`): 103 of 149 excluded, 39 kept, 7 matched no code and were dropped.
- **OCR cleaning:** besides the required "< 40 % alphabetic" rule, a line is kept only if ≥ 60 % of its tokens are real words (the MiniLM tokenizer's English vocabulary plus every word used in an EPFO circular title). The Hindi letterhead OCRs to the same Latin gibberish in every circular, so a frequency-based filter could not catch it.
- **The 13 Aug 2025 Aadhaar order PDF is a scan with no text layer** and Tesseract is not installed, so only its OCR first page is in the corpus, plus a structured chunk derived from the JD approval matrix row for "wrong Aadhaar linked".
- **Hand-written chunks (8):** the 5 requested (Form 19 two-month rule, EPS 6-month / 9.5-year / 10-year rules, EPFiGMS, RTI ss. 6/7/19, Form 121) plus Date-of-Exit self-marking, pending/duplicate claims and bank KYC, which had thin circular coverage. Each names a public source URL to verify against.
- **Dataset gap:** R09 (tax) has only 2 chunks — the 13 Apr 2026 Form 121 circular's OCR page and the hand-written Form 121 note. Adding the full circular PDF would help.
- **`chunks.json` and `embeddings.npy` are committed** (≈ 110 kB of vectors) so the API starts without downloading the embedding model when only serving.
