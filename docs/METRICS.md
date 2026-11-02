# Metrics

Measured on 2 November 2026 on the development laptop (Windows 11, Python 3.12, CPU only). Reproduce with `make test`, `python scripts/eval_explain.py` and `python scripts/try_explain.py`.

## Test suite

**231 tests, all passing** (`cd backend && pytest`).

| File | Tests | Covers |
| --- | --- | --- |
| `test_pii.py` | 71 | 50 synthetic PII strings, labels, name masking, remarks left untouched |
| `test_documents.py` | 76 | every template × every code × 4 intakes × 2 field sets; PDF size, disclaimer on every page, grievance length, endpoints |
| `test_explain.py` | 62 | citation validator on every labelled case (mocked Claude), fallbacks, PII in logs and prompts |
| `test_classifier.py` | 16 | accuracy, paraphrases, JD category, clarifying questions, fix steps, latency |
| `test_ocr.py` | 4 | OCR endpoint (mocked Tesseract) |
| `test_corpus.py`, `test_health.py` | 2 | corpus coverage, health check |

## Classifier (deterministic, no LLM)

| Set | Accuracy | Notes |
| --- | --- | --- |
| `backend/tests/cases.csv` — 45 labelled seed remarks | **45 / 45 (100 %)** | Optimistic: the taxonomy triggers were written alongside these remarks. |
| 20 paraphrased remarks, **before** tuning | **11 / 20 (55 %)** | The honest estimate of how the original rules handle unseen wording. |
| Same 20 paraphrases, after adding general phrasings | 20 / 20 (100 %) | Now a regression test, no longer held out. |

Confusion table on `cases.csv`: all 45 on the diagonal (R00 ×3, R01 ×7, R02 ×5, R03 ×4, R04 ×5, R05 ×4, R06 ×4, R07 ×2, R08 ×4, R09 ×3, R10 ×4).

**What is still needed:** 15–30 real, redacted rejection screenshots as a held-out set. Until then, treat 55 % as the floor and 100 % as the ceiling.

## Citation validity

| Run | Explanations | Sentences | Dropped by validator | Citations returned | Citations that resolve to a corpus chunk | Fell back to canned text |
| --- | --- | --- | --- | --- | --- | --- |
| Live, `claude-sonnet-5-5`, all 45 cases (`scripts/eval_explain.py`) | 45 | 794 | **0 (0.0 %)** | 205 | **205 / 205 (100 %)** | 0 |
| Mocked client, all 45 cases (tests; each response cites one invalid ID) | 45 | 405 | 45 — every injected invalid citation | — | 100 % | 0 |

What this shows: the model cited only the extracts it was given, and the validator removes any citation that is not. What it does **not** show: that each cited extract actually supports the sentence it is attached to. That needs a human (or a separate grading pass) to read a sample — a sensible next step before the pitch.

## Latency

| Step | Measured | Where |
| --- | --- | --- |
| `/classify` | p95 **6.6 ms** (in-process, 100 calls); 3 ms over HTTP to 127.0.0.1 | `test_classifier.py`, curl |
| `/documents` (zip of 3 PDFs) | 56 ms | curl |
| `/explain`, live Sonnet 5.5 | p50 **5.0 s**, p95 **7.6 s**, max 15.5 s (first call, cold) | `eval_explain.py`, 45 calls |
| `/explain`, canned / demo mode | < 50 ms | — |

The UI shows the diagnosis, fix steps and documents straight after `/classify`; the explanation fills in when it arrives. Text-in to diagnosis is well under 5 s; text-in to a **live** explanation is not.

## Corpus

72 chunks (PDF text 9, Joint Declaration data 9, OCR first pages 46, hand-written 8), 384-dimension MiniLM embeddings. Chunks per code: R01 23 · R02 8 · R03 6 · R04 6 · R05 21 · R06 12 · R07 5 · R08 5 · R09 2 · R10 13. All 151 EPFO circular PDF links returned 404 (`datasets/circular_pdfs/epfo/download_log.csv`).

## Documents

Every template renders for every code with no unrendered Jinja; every PDF is 40–45 kB (embedded font) and carries the disclaimer on every page; the grievance text is at most ~910 characters with every field at maximum length (portal limit 1,500).
