import io

from fastapi.testclient import TestClient
from PIL import Image

from app import ocr
from app.main import app


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 100), "white").save(buf, "PNG")
    return buf.getvalue()


def test_status_reports_availability():
    assert TestClient(app).get("/ocr/status").json() == {"available": ocr.available()}


def test_unavailable_returns_503(monkeypatch):
    monkeypatch.setattr(ocr, "available", lambda: False)
    r = TestClient(app).post("/ocr", files={"file": ("s.png", png(), "image/png")})
    assert r.status_code == 503


def test_extracted_text_is_pii_stripped(monkeypatch):
    monkeypatch.setattr(ocr, "available", lambda: True)
    monkeypatch.setattr(ocr, "extract_text", lambda data: "Rejected: Date of exit not available\nUAN 100123456789")
    r = TestClient(app).post("/ocr", files={"file": ("s.png", png(), "image/png")})
    assert r.status_code == 200
    assert r.json()["text"] == "Rejected: Date of exit not available\nUAN [UAN]"


def test_rejects_non_images(monkeypatch):
    monkeypatch.setattr(ocr, "available", lambda: True)
    r = TestClient(app).post("/ocr", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 415
