import io
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app import documents
from app.documents import DISCLAIMER, DOC_ORDER, DocFields, build, context, document_text, grievance_text
from app.intake import Intake
from app.main import app

CODES = [f"R{i:02d}" for i in range(11)]
FULL = DocFields(
    member_name="Ramesh Kumar Singh", member_address="12 Gandhi Road, Guntur 522001",
    employer_name="Acme Textiles Pvt Ltd", employer_address="Plot 4, Industrial Estate, Guntur",
    uan_last4="1234", member_id="APGNT00123450000012345", claim_id="GNT2026110100123",
    claim_date="01/10/2026", rejection_date="15/10/2026", date_of_joining="01/04/2019",
    date_of_exit="31/07/2026", regional_office="Guntur", correction_details="Name as per Aadhaar",
    grievance_no="EPFIGMS/12345", place="Guntur", contact="the email I gave you",
)
LONGEST = DocFields(**{k: ("W" * f.metadata[0].max_length if f.annotation is str and f.metadata
                          and hasattr(f.metadata[0], "max_length") else getattr(FULL, k))
                       for k, f in DocFields.model_fields.items()})
INTAKES = [Intake(), Intake(claim_form="19", uan_issued="after_oct_2017", aadhaar_validated=True),
           Intake(uan_issued="before_oct_2017", aadhaar_validated=True), Intake(aadhaar_validated=False)]
LEFTOVER = re.compile(r"\{\{|\}\}|\{%|%\}|\bNone\b|Undefined|\[\]")
PROMISES = re.compile(r"will be (approved|settled|paid)|guarantee|definitely", re.I)


def pdf_text(data: bytes) -> str:
    return " ".join(" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(data)).pages)


@pytest.mark.parametrize("code", CODES)
@pytest.mark.parametrize("doc", DOC_ORDER)
def test_every_template_renders_for_every_code(code, doc):
    for intake in INTAKES:
        for fields in (DocFields(), FULL):
            text = document_text(doc, context(code, intake, fields, "Date of exit not available"))
            assert not LEFTOVER.search(text), (code, doc, LEFTOVER.search(text).group(0))
            assert not PROMISES.search(text)
            assert len(text) > 200


@pytest.mark.parametrize("code", CODES)
def test_pdfs_are_real_and_carry_disclaimer(code):
    files = build(code, Intake(claim_form="19"), FULL, "Date of exit not available", list(DOC_ORDER))
    assert len(files) == 4
    for name, data in files:
        assert data[:4] == b"%PDF"
        assert len(data) > 5 * 1024, name
        text = pdf_text(data)
        assert DISCLAIMER in text, name
        assert "DRAFT" in text


def test_disclaimer_on_every_page():
    many = DocFields(correction_field="name")  # JD checklist with all categories spans pages
    data = build("R01", Intake(), many, "Name mismatch", ["jd_checklist"])[0][1]
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) >= 2
    for page in reader.pages:
        assert DISCLAIMER in " ".join((page.extract_text() or "").split())


@pytest.mark.parametrize("code", CODES)
def test_grievance_under_1500_chars_even_with_longest_fields(code):
    long_remark = "Claim rejected because " + "details not matching " * 100
    ctx = context(code, Intake(claim_form="10C"), LONGEST, long_remark)
    assert len(grievance_text(ctx)) <= 1500
    assert len(grievance_text(context(code, Intake(), FULL, "Date of exit not available"))) < 1500


def test_uan_is_masked_to_last_four():
    text = document_text("employer_letter", context("R02", Intake(), FULL, "x"))
    assert "XXXXXXXX1234" in text
    text = document_text("employer_letter", context("R02", Intake(), DocFields(), "x"))
    assert "XXXXXXXXXXXX" in text


def test_letter_variants_and_circular_refs():
    variant = {code: documents.doc_text()[code]["letter"] for code in CODES}
    assert variant["R02"] == "exit_date" and variant["R01"] == "jd_attestation"
    assert variant["R05"] == "aadhaar_correction" and variant["R04"] == "bank_kyc" and variant["R10"] == "eps"
    letter = document_text("employer_letter", context("R05", Intake(), FULL, "Wrong Aadhaar linked"))
    assert "WSU/MemberProfile/E-710137/2025-26/26 (13 Aug 2025)" in letter
    assert "15 days" in letter


def test_rti_contents():
    text = document_text("rti", context("R02", Intake(), FULL, "Date of exit not available"))
    assert "The Central Public Information Officer," in text and "Regional Office, Guntur" in text
    assert "[Insert Regional Office address" in text  # no postal addresses in our data
    assert "Rs 10" in text and "rtionline.gov.in" in text
    assert len(re.findall(r"^\d+\. ", text.split("## 3. Information sought")[1].split("## 4.")[0], re.M)) == 10


def test_jd_checklist_category_c_lists_attesting_authorities():
    c = document_text("jd_checklist", context("R01", Intake(aadhaar_validated=False), FULL, "x"))
    a = document_text("jd_checklist", context("R01", Intake(uan_issued="after_oct_2017", aadhaar_validated=True), FULL, "x"))
    assert "Notary Public" in c and "Notary Public" not in a
    assert "Category C" in c and "Steps for Category A" in a and "Steps for Category C" not in a


def test_recommended_documents():
    assert documents.recommended_documents("R01") == ["employer_letter", "jd_checklist", "grievance", "rti"]
    assert documents.recommended_documents("R08") == ["grievance", "rti"]
    assert documents.recommended_documents("R02") == ["employer_letter", "grievance", "rti"]


def test_documents_endpoint_zip_and_single_pdf():
    client = TestClient(app)
    body = {"code": "R02", "intake": {"claim_form": "19"}, "fields": FULL.model_dump(),
            "remark_text": "UAN 100123456789 date of exit not available"}
    r = client.post("/documents", json=body)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert r.headers["cache-control"] == "no-store"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert names == ["PFSahay_R02_employer_letter.pdf", "PFSahay_R02_grievance.pdf", "PFSahay_R02_rti.pdf"]
    one = client.post("/documents", json={**body, "docs": ["rti"]})
    assert one.headers["content-type"] == "application/pdf"
    assert "100123456789" not in pdf_text(one.content)  # remark is PII-stripped


def test_bad_uan_last4_rejected():
    r = TestClient(app).post("/documents", json={"code": "R02", "fields": {"uan_last4": "100123456789"}})
    assert r.status_code == 422


def test_offices_endpoint():
    rows = TestClient(app).get("/offices").json()
    assert len(rows) > 100 and {"office", "zone_label"} <= rows[0].keys()


def test_grievance_text_endpoint():
    r = TestClient(app).post("/documents/text", json={"code": "R07", "remark_text": "Claim already under process"})
    assert "Relief sought:" in r.json()["grievance"]
