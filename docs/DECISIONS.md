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

## Phase 2 — PII, intake, classifier

- **PII stripping order:** email → `UAN` + 12 digits → `a/c|acct|account` + 9–18 digits → PAN → bare 12-digit groups (`[AADHAAR]`) → mobile → a catch-all `[NUMBER]` for any remaining run of 9+ digits (spaces/hyphens allowed). The catch-all is beyond the spec's list but guarantees the "no 9+ digit run survives" rule for member IDs, claim IDs and unlabelled account numbers. Labels like "UAN:" are kept so the remark still reads naturally.
- **The PII-stripped remark is echoed back** in the `/classify` response (`remark_text`, `redactions` counts) so the UI can show what was removed. Only `code` and `confidence` are logged.
- **Intake "not sure" is sent as null.** `uan_issued` has four values: `before_oct_2017`, `after_oct_2017`, `not_sure`, `no_uan`. JD category is `None` when the answers can't decide it; R01's fix path then lists all three categories.
- **Classifier scoring:** `0.60 + 0.15 × (matched/total triggers) + 0.25 × (share of the remark covered by matched phrases) + intake bonus`. Any trigger match reaches the 0.6 threshold on its own (the triggers are specific phrases); share and coverage break ties between codes. A match lying inside a longer match for another code is dropped ("10d instead" beats "10d"). If the runner-up is within 0.05, confidence drops by up to 0.10. Labels: ≥ 0.8 Likely, ≥ 0.6 Probable, otherwise Unsure → R00.
- **Intake weights** (`backend/app/rules/classifier_extra.yaml`): `exit_date_shown` false → R02 +0.15 / true → R02 −0.15; `aadhaar_validated` false → R05 +0.10 / true → R05 −0.05; claim form 10C/10D → R10 +0.05; Form 13 → R03, R06 +0.05; Form 31 → R08 +0.05. Bonuses only adjust codes that already have a trigger match.
- **Intake-only diagnosis:** when the remark matches nothing, `exit_date_shown = false` gives R02 and `aadhaar_validated = false` gives R05 at exactly 0.6 ("Probable"). This is what makes the clarifying question useful: answering it can resolve an R00.
- **Clarifying question per case:** low-confidence results ask the question for the top candidate code (one fixed question per code R01–R10). With no candidate at all, ask about the Date of Exit if unanswered (the most common rejection), then Aadhaar, then "copy the full reason from Track Claim Status".
- **Extra triggers and suppressions live in `backend/app/rules/classifier_extra.yaml`**, not in the dataset taxonomy, so `datasets/` stays untouched. One suppression: "date of exit" preceded by from/after/since is a reference point, not the problem ("two months not completed from date of exit" → R08).
- **Accuracy:** `cases.csv` 45/45 (100 %). Because the taxonomy triggers were written alongside those seed remarks, that number is optimistic. A set of 20 paraphrased remarks written before any tuning (`tests/heldout_paraphrases.csv`) scored **11/20 (55 %)** with taxonomy triggers + first extras; after adding general phrasings (not copies of the strings) it scores 20/20. The paraphrase set has therefore now been used for tuning and is a regression test, not a held-out estimate. A genuinely unseen set — the 15–30 real redacted screenshots DATASETS.md asks for — is needed for a trustworthy number.
- **YAML regex gotcha:** patterns in double-quoted YAML need `\b`; single-quoted YAML is used for the newer patterns so `\b` stays literal.

## Phase 3 — Grounded explanation

- **Model: `claude-sonnet-5-5`, not the spec's `claude-sonnet-4-5`.** On 2 Nov 2026 the API returned `404 not_found_error` for `claude-sonnet-4-5` with this key (it is deprecated and reaches end-of-life on 30 Nov 2026); `claude-sonnet-5-5` is the current Sonnet. Override with `PFSAHAY_EXPLAIN_MODEL`.
- **No `temperature`.** The installed `anthropic` SDK (2.3.0) sends API version 2026-10-21, which rejects `temperature`/`top_p`/`top_k` on every model, and the SDK no longer accepts the argument. Pinning an old SDK to keep 0.2 would hold the whole codebase back; consistency comes instead from the narrow system prompt, the citation validator and the canned fallback.
- **Thinking off for Sonnet 5.5** (`thinking: {"type": "between_tools"}`, effort `low`): thinking tokens count toward the 700-token cap, and a short explanation doesn't need them. Applied only when the model is Sonnet 5.5 (other models reject that value).
- **Fallbacks to the canned explanation:** no key, connection error, rate limit, any other API error, `refusal`, `max_tokens` (truncated "Next steps"), empty text, or > 30 % of sentences dropped. The response says which in `fallback_reason`. The SDK's server-side model fallback is not used: it can't be combined with `between_tools`, and the canned text is the designed fallback.
- **Retrieval query = stripped remark + the code's fix path**, cosine over chunks tagged with the code, k = 5. The embedding model loads from the local cache (no HF Hub call after the first download) and is warmed in a background thread at API startup.
- **Canned explanations are not tied to chunk IDs** (IDs change when the corpus is rebuilt). They carry the top 3 retrieved chunks as citations on the first paragraph instead.
- **Validator:** paragraphs split on blank lines, lines kept (numbered steps), sentences split on `.!?` + space but not after a list number; citations written after the full stop are attached to the sentence before. Sentences without a citation are kept.
- **`/explain` accepts `canned: true`** so demo mode never calls the API.
- **Latency:** a live explanation takes ≈ 4–5 s once warm (17 s on a cold start including the embedding model load). The UI will show the diagnosis from `/classify` (≈ 5 ms) immediately and fill in the explanation when it arrives.
- **Open question — personal names reach the LLM.** The spec's PII list (Aadhaar, PAN, UAN, account, mobile, email) does not include names, so a remark like "Aadhaar RAMESH KUMAR SINGH vs UAN RAMESH K SINGH" is sent to Anthropic as is. Flagged to the product owner.
