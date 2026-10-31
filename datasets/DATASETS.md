# Datasets — provenance and status

Collected 31 Oct 2026. Everything here is either public Government of India material, community-archived metadata about it, or hand-curated seed data. Verify any figure against the original before quoting it in the deck.

| Folder | What it is | Source | Status |
| --- | --- | --- | --- |
| `epfo_circulars/` | Metadata (title, number, date, division, PDF URL) for **152 member-services circulars FY2019-20 → FY2026-27** filtered from the full EPFO circular list, plus OCR text of the first page of 149 of them (`ocr_first_pages.json`). `all_circulars_<FY>.json` are the unfiltered lists for FY23–FY27. | [gauravmeena0708/pf-circular](https://github.com/gauravmeena0708/pf-circular) — a community index that scrapes epfindia.gov.in and OCRs page 1. Not official. | Ready for corpus seeding. **Full PDFs still need downloading** (see below). |
| `circular_pdfs/` | 4 PDFs we could fetch via mirrors: the 13 Aug 2025 Aadhaar seeding/correction order (full, with Annexure I form), a KEA summary of the 16 Jan 2025 JD circular (annexures missing), the PIB DPDP Rules 2025 backgrounder, and a community RTI letter template. `MANIFEST.json` has SHA-256 hashes. | staffnews.in, kea.co.in, pib.gov.in, jagoinvestor.com | Ready. |
| `joint_declaration/` | Structured Category A/B/C definitions, the Annexure I approval matrix (who approves which field), and Annexure II acceptable-document lists per field. | Transcribed from the 16 Jan 2025 circular (via govtemployeeshub.com mirror) and the 13 Aug 2025 order. | Ready; Date-of-Joining/Leaving and Nationality document lists still to be added from the original PDF. |
| `epfo_offices/` | 108 EPFO regional/district offices with zone label and WhatsApp/helpline number. | taxguru.in reproduction of EPFO's WhatsApp helpline list (2020, numbers may have changed). | Partial — missing UP, West Bengal, some zones; **no CPIO postal addresses yet** (needed for RTI generator). |
| `rejection_remarks/` | `seed_remarks_labelled.csv`: 45 rejection remarks labelled with root-cause code, form and JD-category hint. `taxonomy_v1.yaml`: the 10-code taxonomy with trigger regexes, fix paths and corpus references. | Hand-curated from EPFO FAQs, consultant guides and forum posts (paraphrased; marked `portal-style` or `synthetic`). | Seed only. **Needs 15–30 real redacted screenshots** to become the test set. |
| `statistics/` | 19 figures: claims received/settled/rejected FY24 and FY25, rejection rates, EPFiGMS grievance counts 2012–2025, auto-settlement counts, corpus size — each with source and URL. | EPFO Annual Reports (via Business Today, Kotak811, Factly/Dataful), Lok Sabha USQ 2680 (Mar 2026), ministerial statements. | Ready for the deck. |

## Could not be fetched from this environment (download from India and drop into the folder named)

EPFO's own domains (`epfindia.gov.in`, `epfo.gov.in`, `pmvbry-cdn.epfindia.gov.in`) and India Code return 403/504 from the build sandbox. The URLs are known; they just need a browser in India:

| File → folder | URL |
| --- | --- |
| JD simplification circular 16 Jan 2025 (full, with Annexures I–III) → `circular_pdfs/` | https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2025-2026/Circular_SimplificationOfJointDeclarationProcess.pdf |
| Every PDF listed in `epfo_circulars/member_services_circulars_2019_2026.csv` column `english_pdf_link` (152 links; a script to batch-download them is the first Phase 1 task) → `circular_pdfs/epfo/` | see CSV |
| EPF & MP Act 1952 (India Code) → `statutes/` | https://www.indiacode.nic.in/bitstream/123456789/2152/1/a195219.pdf |
| EPF Scheme 1952 (paras 68–70, 72), EPS 1995 (paras 12, 14, Form 10C/10D), RTI Act 2005 (ss. 6, 7, 19) → `statutes/` | epfindia.gov.in → Acts & Schemes; indiacode.nic.in |
| EPFO Annual Report 2024-25 (claim tables by form type and zone) → `statistics/` | epfindia.gov.in → Publications → Annual Reports |
| Dataful "EPFO claims and rejections" dataset (login required) → `statistics/` | https://dataful.in/ |
| EPFO RO/SRO list with postal addresses + CPIO names → `epfo_offices/` | https://www.epfindia.gov.in/site_en/Contact_us.php and the RTI "CPIO" page on each zonal site |

## Licence note

Government of India circulars, statutes and statistics are public documents. The pf-circular metadata is used as an index only; its OCR text is machine-generated and must be checked against the PDF before being cited. Third-party mirrors are credited in `MANIFEST.json`.
