# PF Sahay

AI copilot that diagnoses rejected EPF (Employees' Provident Fund) claims and generates the documents to fix them — employer correction letters, EPFiGMS grievances, RTI applications and Joint Declaration checklists.

Built for Indiathon 2026 (E-Cell IIIT Bhubaneswar × LearnApart), "Build Your MVP – 14 Day Challenge".

## Repository layout

```
datasets/          # all source data for the corpus, classifier and templates (see datasets/DATASETS.md)
```

Application code (Next.js frontend, FastAPI backend, classifier, templates) lands in later phases per the implementation plan.

## Pipeline (planned)

1. Capture — paste rejection text or upload a screenshot (OCR).
2. Strip PII — Aadhaar, PAN, bank, mobile and UAN numbers removed before anything leaves the server.
3. Classify — deterministic rules map the remark to one of 10 root-cause codes (`datasets/rejection_remarks/taxonomy_v1.yaml`).
4. Explain — LLM explains in plain language, citing only supplied EPFO circular chunks.
5. Generate — Jinja2 templates render ready-to-submit PDFs.

## Disclaimer

PF Sahay produces AI-assisted drafts for the user to verify before submission. It is not legal advice and does not guarantee claim approval. It never asks for UAN passwords or stores Aadhaar/PAN/bank numbers.
