"""Build the retrieval corpus: backend/corpus/chunks.json + embeddings.npy.

Sources, in priority order:
  1. Text layer of PDFs in datasets/circular_pdfs/ and datasets/circular_pdfs/epfo/
  2. Joint Declaration JSON/CSV rendered as readable paragraphs
  3. OCR first pages of EPFO circulars (cleaned, tagged quality "ocr")
  4. Hand-written chunks (handwritten_chunks.yaml, tagged quality "handwritten")

Run from the repo root:  python backend/corpus/build_corpus.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

CORPUS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CORPUS_DIR.parent
REPO = BACKEND_DIR.parent
DATA = REPO / "datasets"

CHUNK_WORDS = 400
OVERLAP_WORDS = 50
MIN_CHUNK_WORDS = 40
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CODES = [f"R{i:02d}" for i in range(1, 11)]

# Metadata for the hand-fetched PDFs in datasets/circular_pdfs/ (see MANIFEST.json).
LOCAL_PDF_META = {
    "EPFO_JD_Simplification_16Jan2025_via_KEA.pdf": {
        "source_title": "Simplification of Joint Declaration Process (KEA summary of EPFO circular)",
        "source_url": "https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2025-2026/Circular_SimplificationOfJointDeclarationProcess.pdf",
        "source_date": "16/01/2025",
        "circular_no": "WSU/JointDeclaration/E-54018/2024-25/006",
        "codes": ["R01"],
    },
    "EPFO_Aadhaar_Seeding_Correction_UAN_13Aug2025.pdf": {
        "source_title": "Seeding/Correction of Aadhaar in Universal Account Number (UAN)",
        "source_url": "https://www.staffnews.in",
        "source_date": "13/08/2025",
        "circular_no": "WSU/MemberProfile/E-710137/2025-26/26",
        "codes": ["R05"],
    },
    # Privacy background only: kept in the corpus, never tagged to a rejection code.
    "DPDP_Rules_2025_PIB_Backgrounder_17Nov2025.pdf": {
        "source_title": "DPDP Rules, 2025 Notified (PIB backgrounder)",
        "source_url": "https://pib.gov.in",
        "source_date": "17/11/2025",
        "circular_no": "",
        "codes": [],
        "auto_tag": False,
    },
    "EPF_RTI_Letter_Template_jagoinvestor.pdf": {
        "source_title": "Sample RTI application to EPFO (community template)",
        "source_url": "https://www.jagoinvestor.com",
        "source_date": "",
        "circular_no": "",
        "codes": ["R00", "R02", "R07"],
        "auto_tag": False,
    },
}

ATTRIBUTION_JD = {
    "source_title": "Simplification of Joint Declaration Process - Annexures I and II",
    "source_url": "https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2025-2026/Circular_SimplificationOfJointDeclarationProcess.pdf",
    "source_date": "16/01/2025",
    "circular_no": "WSU/JointDeclaration/E-54018/2024-25/006",
}


# ---------------------------------------------------------------- helpers

def split_words(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)] if words else []
    out, step = [], size - overlap
    for start in range(0, len(words), step):
        piece = words[start : start + size]
        if len(piece) < MIN_CHUNK_WORDS and out:
            break  # tail already covered by the previous window's overlap
        out.append(" ".join(piece))
        if start + size >= len(words):
            break
    return out


def normalise_ws(text: str) -> str:
    text = text.replace(" ", " ").replace("�", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{2,}", "\n", text).strip()


class Tagger:
    def __init__(self) -> None:
        tax = yaml.safe_load((DATA / "rejection_remarks" / "taxonomy_v1.yaml").read_text(encoding="utf-8"))
        kw = yaml.safe_load((CORPUS_DIR / "code_keywords.yaml").read_text(encoding="utf-8"))
        self.min_hits = kw["min_hits"]
        self.title_weight = kw["title_weight"]
        self.triggers = {
            code: [re.compile(t, re.I) for t in spec.get("triggers", [])]
            for code, spec in tax["codes"].items()
        }
        self.keywords = {code: [re.compile(k, re.I) for k in kws] for code, kws in kw["codes"].items()}
        self.exclude = [re.compile(p, re.I) for p in kw["exclude_title_patterns"]]

    def excluded(self, title: str) -> bool:
        return any(p.search(title) for p in self.exclude)

    def tag(self, title: str, text: str) -> list[str]:
        """Codes whose taxonomy triggers + corpus keywords score >= min_hits."""
        codes = []
        for code in CODES:
            patterns = self.triggers.get(code, []) + self.keywords.get(code, [])
            hits = sum(
                (self.title_weight if p.search(title) else 0) + (1 if p.search(text) else 0)
                for p in patterns
            )
            if hits >= self.min_hits:
                codes.append(code)
        return codes


def circular_index() -> dict[str, dict]:
    """english_pdf_link -> row from the member-services CSV."""
    with (DATA / "epfo_circulars" / "member_services_circulars_2019_2026.csv").open(encoding="utf-8") as f:
        return {row["english_pdf_link"].strip(): row for row in csv.DictReader(f)}


def clean_circular_no(raw: str) -> str:
    return re.sub(r"^\s*No[.:]?\s*", "", raw or "").strip()


def english_vocab() -> set[str]:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    return {w for w in tok.get_vocab() if w.isalpha()}


def domain_vocab() -> set[str]:
    titles = []
    for path in (DATA / "epfo_circulars").glob("all_circulars_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("circulars", data.get("data", []))
        titles += [str(r.get("title", "")) for r in rows if isinstance(r, dict)]
    titles += [row["title"] for row in circular_index().values()]
    return set(re.findall(r"[a-z]{2,}", " ".join(titles).lower()))


# ---------------------------------------------------------------- sources

def pdf_sources(log: list[str]) -> list[dict]:
    import pdfplumber

    by_filename = {Path(u).name: row for u, row in circular_index().items()}
    docs = []
    pdfs = sorted((DATA / "circular_pdfs").glob("*.pdf")) + sorted((DATA / "circular_pdfs" / "epfo").glob("*.pdf"))
    for path in pdfs:
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        except Exception as e:  # corrupt download etc.
            log.append(f"pdf  SKIP {path.name}: {type(e).__name__}")
            continue
        text = normalise_ws(text)
        if len(text.split()) < MIN_CHUNK_WORDS:
            log.append(f"pdf  SKIP {path.name}: no text layer (scanned) - OCR first page used instead")
            continue
        meta = LOCAL_PDF_META.get(path.name)
        if meta is None and path.name in by_filename:
            row = by_filename[path.name]
            meta = {
                "source_title": row["title"],
                "source_url": row["english_pdf_link"],
                "source_date": row["date"],
                "circular_no": clean_circular_no(row["circular_no"]),
            }
        meta = meta or {"source_title": path.stem, "source_url": "", "source_date": "", "circular_no": ""}
        docs.append({**meta, "text": text, "quality": "pdf", "origin": path.name})
        log.append(f"pdf  OK   {path.name}: {len(text.split())} words")
    return docs


def jd_sources() -> list[dict]:
    jd = DATA / "joint_declaration"
    cats = json.loads((jd / "jd_categories.json").read_text(encoding="utf-8"))
    docs_json = json.loads((jd / "jd_acceptable_documents.json").read_text(encoding="utf-8"))
    with (jd / "jd_approval_matrix.csv").open(encoding="utf-8") as f:
        matrix = list(csv.DictReader(f))

    legend = cats["legend"]
    out = []

    out.append({
        "codes": ["R01", "R05"],
        "text": (
            "Joint Declaration (JD) is the EPFO process for correcting a member's profile details. "
            "EPFO sorts members into three categories that decide how a correction is filed and who approves it. "
            f"Category A: {cats['A']} "
            f"Category B: {cats['B']} "
            f"Category C: {cats['C']} "
            f"Documents: {cats['document_rule']} "
            f"Abbreviations: {legend}."
        ),
    })

    who = {"EE": "the employee", "ER": "the employer", "DA": "the Dealing Assistant",
           "AO": "the Accounts Officer", "APFC": "the Assistant PF Commissioner",
           "RO": "the Regional Office", "PRO": "the PRO counter"}

    def describe(chain: str) -> str:
        if "(" in chain or "Physical" in chain:
            return chain
        steps = [" or ".join(who.get(p, p) for p in step.split("/")) for step in chain.split(">")]
        if len(steps) == 1:
            return f"{steps[0]} can make the change directly"
        return "submitted by " + steps[0] + ", then approved by " + ", then ".join(steps[1:])

    def rows_text(rows: list[dict]) -> str:
        return " ".join(
            f"{r['field']}: in Category A, {describe(r['category_A'])}; in Category B, "
            f"{describe(r['category_B'])}; in Category C, {describe(r['category_C'])}."
            for r in rows
        )

    profile = [r for r in matrix if r["field"].split()[0] in {"Name", "Date", "Gender", "Nationality", "Father/Mother/Spouse", "Marital"} and "Joining" not in r["field"]]
    service = [r for r in matrix if "Joining" in r["field"]]
    aadhaar = [r for r in matrix if r["field"].startswith("Aadhaar")]
    head = "Who approves a Joint Declaration correction (Annexure I approval matrix). "
    out.append({"codes": ["R01"], "text": head + rows_text(profile)})
    out.append({"codes": ["R02", "R03"], "text": head + rows_text(service) +
                " Corrections to the Date of Joining, Date of Leaving (Date of Exit) and reason of leaving use the same Joint Declaration route."})
    out.append({"codes": ["R05"], "text": head + rows_text(aadhaar) +
                " Under the 13 August 2025 order a wrong Aadhaar linked to a UAN is corrected by the employer through an online Joint Declaration approved by the Regional Office; where the establishment is closed or the UAN is not Aadhaar-validated, a physical Joint Declaration is submitted at the PRO counter."})

    labels = {
        "name_gender": ("name or gender", ["R01"]),
        "date_of_birth": ("date of birth", ["R01"]),
        "family_details": ("father, mother or spouse name (family details)", ["R01"]),
        "marital_status": ("marital status", ["R01"]),
    }
    for key, (label, codes) in labels.items():
        out.append({
            "codes": codes,
            "text": (
                f"Documents accepted for correcting {label} through a Joint Declaration (Annexure II). "
                "At least two documents are needed for each field (one if submitted through DigiLocker); "
                "none are needed where the employee can self-correct (Category A). Accepted documents: "
                + "; ".join(docs_json[key]) + "."
            ),
        })
    out.append({
        "codes": ["R01", "R05"],
        "text": (
            "If the establishment is closed or the employer is not available, a physical Joint Declaration "
            "(Category C) can be attested by one of these authorities (MAP Part II-A para 10.18): "
            + "; ".join(docs_json["attesting_authorities_if_establishment_closed"])
            + ". The attested form is submitted at the Regional Office PRO counter."
        ),
    })
    return [{**ATTRIBUTION_JD, **d, "quality": "structured", "origin": "joint_declaration"} for d in out]


def ocr_sources(tagger: Tagger, log: list[str]) -> list[dict]:
    raw = json.loads((DATA / "epfo_circulars" / "ocr_first_pages.json").read_text(encoding="utf-8"))
    idx = circular_index()

    # Hindi letterheads OCR'd as Latin produce gibberish lines ("ota ufae Afay waa").
    # Keep a line only if most of its tokens are real words: English (the embedding
    # model's vocabulary) or domain terms (words used in any EPFO circular title).
    vocab = english_vocab() | domain_vocab()

    def keep_line(line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        if sum(c.isalpha() for c in s) / len(s) < 0.40:
            return False
        toks = re.findall(r"[a-z]{2,}", s.lower())
        if not toks:
            return False
        return sum(t in vocab for t in toks) / len(toks) >= 0.6

    docs, excluded, untagged = [], 0, 0
    for url, v in raw.items():
        title = v.get("title", "").strip()
        if tagger.excluded(title):
            excluded += 1
            continue
        lines = [ln.strip() for ln in (v.get("ocr_first_page") or "").splitlines()]
        text = normalise_ws(" ".join(ln for ln in lines if keep_line(ln)))
        if len(text.split()) < MIN_CHUNK_WORDS:
            continue
        if not tagger.tag(title, text):
            untagged += 1
            continue
        row = idx.get(url, {})
        docs.append({
            "source_title": title,
            "source_url": url,
            "source_date": v.get("date", ""),
            "circular_no": clean_circular_no(row.get("circular_no", "")),
            "text": text,
            "quality": "ocr",
            "origin": "ocr_first_pages",
        })
    log.append(f"ocr  {len(docs)} circulars kept, {excluded} excluded as staff/admin, {untagged} matched no code")
    return docs


def handwritten_sources() -> list[dict]:
    items = yaml.safe_load((CORPUS_DIR / "handwritten_chunks.yaml").read_text(encoding="utf-8"))
    return [{
        "source_title": it["source_title"],
        "source_url": it["source_url"],
        "source_date": it.get("source_date", ""),
        "circular_no": "",
        "text": normalise_ws(it["text"]),
        "quality": "handwritten",
        "origin": it["key"],
        "codes": it["codes"],
    } for it in items]


# ---------------------------------------------------------------- build

def build() -> list[dict]:
    log: list[str] = []
    tagger = Tagger()
    docs = pdf_sources(log) + jd_sources() + ocr_sources(tagger, log) + handwritten_sources()

    # Curated sources (structured JD data, hand-written chunks, and PDFs whose meta sets
    # auto_tag False) carry hand-assigned codes; circular text is tagged by keywords.
    chunks = []
    for doc in docs:
        fixed = doc.pop("codes", [])
        auto = doc.pop("auto_tag", doc["quality"] in ("pdf", "ocr"))
        for piece in split_words(doc["text"]):
            auto_codes = tagger.tag(doc["source_title"], piece) if auto else []
            codes = sorted(set(fixed) | set(auto_codes))
            chunks.append({**doc, "text": piece, "codes": codes})
    for i, c in enumerate(chunks, 1):
        c["id"] = f"C{i}"
    chunks = [{k: c[k] for k in ("id", "source_title", "source_url", "source_date", "circular_no",
                                   "quality", "origin", "codes", "text")} for c in chunks]
    print("\n".join(log))
    return chunks


def embed(chunks: list[dict]):
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL)
    vecs = model.encode([f"{c['source_title']}. {c['text']}" for c in chunks],
                        normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


def main() -> int:
    import numpy as np

    chunks = build()
    (CORPUS_DIR / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    np.save(CORPUS_DIR / "embeddings.npy", embed(chunks))

    per_code = Counter(code for c in chunks for code in c["codes"])
    per_quality = Counter(c["quality"] for c in chunks)
    print(f"\n{len(chunks)} chunks  ({', '.join(f'{q}={n}' for q, n in sorted(per_quality.items()))})")
    print("chunks per code:")
    short = []
    for code in ["R00"] + CODES:
        n = per_code.get(code, 0)
        print(f"  {code}: {n}")
        if code != "R00" and n < 2:
            short.append(code)
    if short:
        print(f"ERROR: fewer than 2 chunks for {', '.join(short)}", file=sys.stderr)
        return 1
    print("OK: every code R01-R10 has >= 2 chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
