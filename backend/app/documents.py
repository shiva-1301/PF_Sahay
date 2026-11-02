"""Deterministic document generation: Jinja2 templates -> ReportLab PDFs.

Nothing here is written by an LLM. User-supplied fields are used to render the PDF
in memory and are never written to disk or logged.
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import date
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, Optional
from xml.sax.saxutils import escape

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.classifier import rules
from app.config import BACKEND_DIR, DATASETS_DIR
from app.intake import Intake, jd_category

TEMPLATES_DIR = BACKEND_DIR / "templates"
DISCLAIMER = "AI-generated draft — verify before submission. Not legal advice. Sources cited for verification."
GRIEVANCE_MAX_CHARS = 1500
OFFICE_ADDRESS_PLACEHOLDER = "[Insert Regional Office address — see epfindia.gov.in > Contact Us]"

DocName = Literal["employer_letter", "jd_checklist", "grievance", "rti"]
DOC_ORDER: list[str] = ["employer_letter", "jd_checklist", "grievance", "rti"]
DOC_TITLES = {
    "employer_letter": "Letter to employer",
    "jd_checklist": "Joint Declaration checklist",
    "grievance": "EPFiGMS grievance",
    "rti": "RTI application",
}
# taxonomy document names -> our generators (others, e.g. portal walkthroughs, are
# covered by the on-screen fix steps rather than a PDF)
TAXONOMY_DOCS = {
    "employer_letter_jd": "employer_letter",
    "employer_letter_exit_date": "employer_letter",
    "employer_letter_aadhaar": "employer_letter",
    "employer_letter_kyc": "employer_letter",
    "employer_letter_eps": "employer_letter",
    "jd_checklist": "jd_checklist",
    "grievance": "grievance",
    "rti": "rti",
}

CorrectionField = Literal["name", "gender", "date_of_birth", "father_mother_spouse",
                          "marital_status", "service_dates", "aadhaar"]
# field -> (label, Annexure II document-list key, Annexure I matrix rows)
CORRECTION_FIELDS = {
    "name": ("Name", "name_gender", ["Name"]),
    "gender": ("Gender", "name_gender", ["Gender"]),
    "date_of_birth": ("Date of birth", "date_of_birth", ["Date of Birth"]),
    "father_mother_spouse": ("Father / mother / spouse name", "family_details", ["Father/Mother/Spouse Name"]),
    "marital_status": ("Marital status", "marital_status", ["Marital Status"]),
    "service_dates": ("Date of joining / date of exit", None, ["Date of Joining / Date of Leaving / Reason of Leaving"]),
    "aadhaar": ("Aadhaar linked to UAN", None, ["Aadhaar (wrong Aadhaar linked)"]),
}
DEFAULT_CORRECTION = {"R03": "service_dates", "R05": "aadhaar"}

LETTER_SUBJECTS = {
    "exit_date": "Request to mark my Date of Exit on the EPFO portal",
    "jd_attestation": "Request to approve my Joint Declaration for correction of details",
    "aadhaar_correction": "Request to correct the Aadhaar linked to my UAN",
    "bank_kyc": "Request to approve my bank account KYC on the EPFO portal",
    "eps": "Request to check and rectify my EPS (pension) contributions",
    "general": "Request for help with my rejected PF claim",
}

ROLE_NAMES = {"EE": "Employee", "ER": "Employer", "DA": "Dealing Assistant", "AO": "Accounts Officer",
              "APFC": "Assistant PF Commissioner", "RO": "Regional Office", "PRO": "PRO counter"}

JD_STEPS = {
    "A": [
        "Log in to the EPFO member portal (Member e-Sewa) and open Manage > Joint Declaration.",
        "Choose the detail to correct and enter it exactly as it appears on your Aadhaar.",
        "Submit the request. In Category A most details need no documents and no employer approval (see the table below).",
        "When the correction shows in your profile, file your claim again.",
    ],
    "B": [
        "File the Joint Declaration online on the member portal (Manage > Joint Declaration).",
        "Upload the supporting documents: at least two for each detail, or one if you use DigiLocker.",
        "Ask your employer to approve it on the employer portal. You can give them the employer letter from PF Sahay.",
        "When the correction is approved, file your claim again.",
    ],
    "C": [
        "Get the physical Joint Declaration form (Annexure I format).",
        "Attach at least two supporting documents for each detail you are correcting.",
        "Get the form signed by your employer. If the establishment is closed, get it attested by one of the authorities listed below.",
        "Submit it at the PRO counter of your EPFO Regional Office and keep the acknowledgement.",
        "When the correction is approved, file your claim again.",
    ],
}
JD_STEPS_AADHAAR = {
    "A": [
        "Ask your employer to file the Aadhaar correction through an online Joint Declaration on the employer portal. You can give them the employer letter from PF Sahay.",
        "Share the correct Aadhaar details with your employer directly, not through anyone else.",
        "The EPFO Regional Office then approves the correction.",
        "When Aadhaar shows as verified in your UAN profile, file your claim again.",
    ],
    "C": [
        "Fill in the physical Joint Declaration form (Annexure I of the order dated 13 August 2025).",
        "Attach your supporting documents.",
        "Submit it at the PRO counter of your EPFO Regional Office; it is approved by the Assistant PF Commissioner.",
        "When Aadhaar shows as verified in your UAN profile, file your claim again.",
    ],
}
JD_STEPS_AADHAAR["B"] = JD_STEPS_AADHAAR["A"]


class DocFields(BaseModel):
    """Extra details for the documents. All optional; blanks print as [placeholders]."""

    member_name: str = Field("", max_length=80)
    member_address: str = Field("", max_length=200)
    employer_name: str = Field("", max_length=120)
    employer_address: str = Field("", max_length=200)
    uan_last4: str = Field("", pattern=r"^(\d{4})?$")
    member_id: str = Field("", max_length=30)
    claim_id: str = Field("", max_length=30)
    claim_date: str = Field("", max_length=20)
    rejection_date: str = Field("", max_length=20)
    date_of_joining: str = Field("", max_length=20)
    date_of_exit: str = Field("", max_length=20)
    regional_office: str = Field("", max_length=60)
    correction_field: Optional[CorrectionField] = None
    correction_details: str = Field("", max_length=150)
    grievance_no: str = Field("", max_length=30)
    place: str = Field("", max_length=40)
    contact: str = Field("", max_length=80)


PLACEHOLDERS = {
    "member_name": "[Your full name]",
    "member_address": "[Your postal address]",
    "employer_name": "[Employer / establishment name]",
    "employer_address": "[Employer address]",
    "member_id": "[Member ID]",
    "claim_id": "[Claim ID]",
    "claim_date": "[date of claim]",
    "rejection_date": "[date of rejection]",
    "date_of_joining": "[date of joining]",
    "date_of_exit": "[last working day]",
    "regional_office": "[Regional Office]",
    "correction_details": "[detail to correct, e.g. Name as per Aadhaar]",
    "grievance_no": "[grievance registration no.]",
    "place": "[Place]",
    "contact": "[your phone number or email]",
}


# ---------------------------------------------------------------- data

@lru_cache(maxsize=1)
def doc_text() -> dict:
    return yaml.safe_load((TEMPLATES_DIR / "doc_text.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def taxonomy_refs() -> dict[str, list[str]]:
    tax = yaml.safe_load((DATASETS_DIR / "rejection_remarks" / "taxonomy_v1.yaml").read_text(encoding="utf-8"))
    return {code: spec.get("corpus_refs", []) for code, spec in tax["codes"].items()}


@lru_cache(maxsize=1)
def jd_data() -> dict:
    jd = DATASETS_DIR / "joint_declaration"
    with (jd / "jd_approval_matrix.csv").open(encoding="utf-8") as f:
        matrix = list(csv.DictReader(f))
    return {
        "categories": json.loads((jd / "jd_categories.json").read_text(encoding="utf-8")),
        "documents": json.loads((jd / "jd_acceptable_documents.json").read_text(encoding="utf-8")),
        "matrix": matrix,
    }


@lru_cache(maxsize=1)
def offices() -> list[dict]:
    with (DATASETS_DIR / "epfo_offices" / "epfo_offices_zones_whatsapp.csv").open(encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def office_address(name: str) -> str:
    for row in offices():
        if row["office"].lower() == name.strip().lower() and row.get("postal_address"):
            return row["postal_address"]
    return OFFICE_ADDRESS_PLACEHOLDER


def recommended_documents(code: str) -> list[str]:
    """Documents for a code: the taxonomy's list, plus the grievance + RTI escalation pair."""
    wanted = {TAXONOMY_DOCS[d] for d in rules().codes[code].documents if d in TAXONOMY_DOCS}
    wanted |= {"grievance", "rti"}
    return [d for d in DOC_ORDER if d in wanted]


# ---------------------------------------------------------------- rendering

@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR), undefined=StrictUndefined,
                       trim_blocks=False, lstrip_blocks=True, keep_trailing_newline=True,
                       autoescape=False)


def _fields_ns(fields: DocFields) -> SimpleNamespace:
    data = fields.model_dump()
    ns = {k: (v.strip() if isinstance(v, str) and v.strip() else PLACEHOLDERS.get(k, v or ""))
          for k, v in data.items()}
    for k in ("member_id", "claim_id", "grievance_no"):
        ns[f"{k}_given"] = bool(data[k].strip())
    ns["uan_last4"] = data["uan_last4"]
    return SimpleNamespace(**ns)


def _role_chain(chain: str) -> str:
    if "(" in chain or " " in chain:
        return chain
    return " then ".join(" or ".join(ROLE_NAMES.get(p, p) for p in step.split("/")) for step in chain.split(">"))


def context(code: str, intake: Intake, fields: DocFields, remark: str) -> dict:
    spec = rules().codes[code]
    text = doc_text()[code]
    jd = jd_category(intake)
    corr = fields.correction_field or DEFAULT_CORRECTION.get(code, "name")
    label, doc_key, rows = CORRECTION_FIELDS[corr]
    data = jd_data()
    remark = remark.strip() or "[rejection reason as shown on the portal]"
    return {
        "f": _fields_ns(fields),
        "today": date.today().strftime("%d %B %Y"),
        "uan_masked": f"XXXXXXXX{fields.uan_last4}" if fields.uan_last4 else "XXXXXXXXXXXX",
        "remark": remark,
        "remark_short": remark if len(remark) <= 160 else remark[:157] + "...",
        "code_name": spec.name,
        "form": intake.claim_form or "[form]",
        "problem": text["problem"],
        "relief": text["relief"],
        "variant": text["letter"],
        "subject": LETTER_SUBJECTS[text["letter"]],
        "refs": taxonomy_refs().get(code, []),
        "jd": jd,
        "jd_definition": data["categories"].get(jd, "") if jd else "",
        "categories": [jd] if jd else ["A", "B", "C"],
        "steps": JD_STEPS_AADHAAR if corr == "aadhaar" else JD_STEPS,
        "field_label": label,
        "matrix": [{"field": r["field"], "A": _role_chain(r["category_A"]), "B": _role_chain(r["category_B"]),
                    "C": _role_chain(r["category_C"])} for r in data["matrix"] if r["field"] in rows],
        "legend": "Legend: " + data["categories"]["legend"] + ".",
        "documents": data["documents"].get(doc_key, []) if doc_key else [],
        "document_rule": data["categories"]["document_rule"],
        "attesting": data["documents"]["attesting_authorities_if_establishment_closed"],
        "source": data["categories"]["source"] + ".",
        "office_address": office_address(fields.regional_office) if fields.regional_office else OFFICE_ADDRESS_PLACEHOLDER,
    }


TEMPLATE_FILES = {
    "employer_letter": "employer_letter.jinja",
    "jd_checklist": "jd_checklist.jinja",
    "grievance": "epfigms_grievance.jinja",
    "rti": "rti_application.jinja",
}


def render_text(doc: str, ctx: dict) -> str:
    text = _env().get_template(TEMPLATE_FILES[doc]).render(**ctx)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def grievance_text(ctx: dict) -> str:
    text = render_text("grievance", ctx).strip()
    if len(text) > GRIEVANCE_MAX_CHARS:  # the portal truncates; never exceed it
        text = text[: GRIEVANCE_MAX_CHARS - 3].rstrip() + "..."
    return text


# ---------------------------------------------------------------- PDF

_FONTS_READY = False


def _fonts() -> tuple[str, str]:
    """Bitstream Vera ships with ReportLab and covers the dash/quote glyphs we use."""
    global _FONTS_READY
    if not _FONTS_READY:
        import reportlab

        font_dir = Path(reportlab.__file__).parent / "fonts"
        pdfmetrics.registerFont(TTFont("Vera", str(font_dir / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("VeraBd", str(font_dir / "VeraBd.ttf")))
        _FONTS_READY = True
    return "Vera", "VeraBd"


def _styles() -> dict[str, ParagraphStyle]:
    reg, bold = _fonts()
    body = ParagraphStyle("body", fontName=reg, fontSize=11, leading=15, spaceAfter=7)
    return {
        "body": body,
        "h1": ParagraphStyle("h1", parent=body, fontName=bold, fontSize=13, leading=17, spaceAfter=9),
        "h2": ParagraphStyle("h2", parent=body, fontName=bold, spaceBefore=6, spaceAfter=5),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=4, spaceAfter=2),
        "num": ParagraphStyle("num", parent=body, leftIndent=18, firstLineIndent=-14, spaceAfter=3),
        "mono": ParagraphStyle("mono", parent=body, fontSize=10.5, leading=14),
    }


def _flowables(text: str, styles: dict[str, ParagraphStyle]) -> list:
    out: list = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        plain: list[str] = []

        def flush():
            if plain:
                out.append(Paragraph("<br/>".join(escape(p) for p in plain), styles["body"]))
                plain.clear()

        for ln in lines:
            if ln.startswith("## "):
                flush(); out.append(Paragraph(escape(ln[3:]), styles["h2"]))
            elif ln.startswith("# "):
                flush(); out.append(Paragraph(escape(ln[2:]), styles["h1"]))
            elif ln.startswith("- "):
                flush(); out.append(Paragraph(escape(ln[2:]), styles["bullet"], bulletText="•"))
            elif re.match(r"^\d+\. ", ln):
                flush(); out.append(Paragraph(escape(ln), styles["num"]))
            else:
                plain.append(ln)
        flush()
        out.append(Spacer(1, 3))
    return out


def _decorate(canvas, doc) -> None:
    reg, bold = _fonts()
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.5))
    canvas.setFont(bold, 96)
    canvas.translate(w / 2, h / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, -30, "DRAFT")
    canvas.restoreState()
    canvas.saveState()
    canvas.setFont(reg, 8)
    canvas.setFillColor(colors.Color(0.3, 0.3, 0.3))
    canvas.drawString(18 * mm, 10 * mm, DISCLAIMER)
    canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def to_pdf(title: str, text: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title, author="PF Sahay (draft)",
                            leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm)
    doc.build(_flowables(text, _styles()), onFirstPage=_decorate, onLaterPages=_decorate)
    return buf.getvalue()


def document_text(doc: str, ctx: dict) -> str:
    """Full text of a document as it is printed in the PDF."""
    if doc == "grievance":
        return ("# EPFiGMS grievance\n\n"
                "Copy the text below into the grievance form on epfigms.gov.in "
                "(Register Grievance). It is kept under 1,500 characters because the portal cuts off longer text.\n\n"
                + grievance_text(ctx) + "\n")
    return render_text(doc, ctx)


def build(code: str, intake: Intake, fields: DocFields, remark: str,
          docs: Optional[list[str]] = None) -> list[tuple[str, bytes]]:
    """Return [(filename, pdf_bytes)] for the requested (or recommended) documents."""
    ctx = context(code, intake, fields, remark)
    wanted = docs or recommended_documents(code)
    return [(f"PFSahay_{code}_{d}.pdf", to_pdf(DOC_TITLES[d], document_text(d, ctx)))
            for d in DOC_ORDER if d in wanted]


def zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files:
            z.writestr(name, data)
    return buf.getvalue()
