# Privacy

PF Sahay is built so that it has nothing personal to lose. There are no user accounts, no user database and no stored uploads.

## What is stored

| Data | Stored? |
| --- | --- |
| Rejection remark you paste | No. Processed in memory for the request, then discarded. |
| Screenshot you upload | No. Read in memory by Tesseract, then discarded; never written to disk. |
| Answers to the five questions | No. Sent with each request, not kept. |
| Names, employer, dates typed for documents | No. Used to render the PDF in memory, then discarded. The response carries `Cache-Control: no-store`. |
| Aadhaar, PAN, UAN, bank account, mobile, email | Never accepted on purpose and removed from any text before it is logged or sent anywhere. The UAN field accepts only its last 4 digits. |
| UAN password or OTP | Never asked for, never accepted. PF Sahay does not log in to or automate the EPFO portal. |
| Server logs | Only the diagnosis code, confidence, model name and counts — no text you typed. |
| Corpus (`chunks.json`, `embeddings.npy`) | Yes — public EPFO circulars and rules only. |

The browser keeps nothing either: the app uses no cookies, `localStorage` or analytics.

## Who receives what

| Third party | Receives | When |
| --- | --- | --- |
| Anthropic (Claude API) | The rejection remark **after** identity numbers and names are removed, the diagnosis code, the claim form and Joint Declaration category, and up to five extracts from public EPFO circulars | Once per explanation. Not in demo mode, not when no API key is configured. |
| Hugging Face | A download request for the public embedding model | First run of the backend only |

Nobody else receives anything. Documents are generated on our server and returned to you; PF Sahay never sends them to your employer, EPFO or anyone else — you do that yourself.

## How identity numbers are removed

`backend/app/pii.py` replaces, in this order: email addresses, 12-digit numbers after the word "UAN", 9–18 digit numbers after "a/c", "acct" or "account", PAN (`ABCDE1234F`), any other 12-digit group (Aadhaar), Indian mobile numbers, and finally any remaining run of 9 or more digits. Personal names that follow words such as "Aadhaar", "UAN", "name" or "bank account" become `[NAME_1]`, `[NAME_2]`. The test suite checks 50 synthetic strings and greps the logs and the LLM prompt for every synthetic number.

Name masking is best-effort: a name typed with no cue word before it ("Ramesh says…") is not caught. Numbers are always caught by the catch-all rule.

## DPDP Act 2023 and DPDP Rules 2025

The Digital Personal Data Protection Rules, 2025 were notified on 14 November 2025 with an eighteen-month period for phased compliance (PIB backgrounder, 17 Nov 2025, in `datasets/circular_pdfs/`). The substantive duties of a Data Fiduciary therefore bind from 13 May 2027. PF Sahay's design already follows the core principles that will apply: purpose limitation (data is used only to produce your diagnosis and documents), data minimisation (only the last 4 UAN digits; no ID numbers), storage limitation (nothing is retained), and no sharing beyond the processor named above. Before a public launch, the team should still publish a notice in plain language, name a contact for grievances, and confirm the Anthropic data-processing terms that apply to the account.

## Not legal advice

Every document carries the footer *"AI-generated draft — verify before submission. Not legal advice. Sources cited for verification."* PF Sahay never promises that a claim will be approved; EPFO alone decides.
