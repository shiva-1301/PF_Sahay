"""Explanation tests. The Anthropic client is always mocked: no API credit is used."""
import csv
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import pii
from app.classifier import classify
from app.explain import explain, get_client, validate
from app.main import app
from app.retrieval import chunk_by_id
from tests.pii_samples import SAMPLES

CASES = Path(__file__).resolve().parent / "cases.csv"
SUPPLIED = re.compile(r"^\[(C\d+)\]", re.M)
LONG_DIGITS = re.compile(r"\d(?:[\s\-]?\d){8,}")
PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)
INVALID_SENTENCE = "Your claim falls under a special rule [C9999]."


class FakeClient:
    """Mimics anthropic.Anthropic().messages.create; cites supplied IDs plus one invalid ID."""

    def __init__(self, invalid_sentences: int = 1, stop_reason: str = "end_turn"):
        self.invalid_sentences = invalid_sentences
        self.stop_reason = stop_reason
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        ids = SUPPLIED.findall(kwargs["messages"][0]["content"])
        a, b = ids[0], ids[-1]
        bad = " ".join([INVALID_SENTENCE] * self.invalid_sentences)
        text = (
            f"Your claim was stopped because a detail in your records is wrong [{a}]. "
            f"This is common and can be fixed. {bad}\n\n"
            f"The usual fix is described in the EPFO rules [{b}]. Your employer may need to help.\n\n"
            "Next steps:\n1. Check your details on the member portal.\n"
            f"2. Send the letter on this page [{a}].\n3. File the claim again."
        )
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                               stop_reason=self.stop_reason, model="fake-model")

    @property
    def supplied(self) -> set[str]:
        return set(SUPPLIED.findall(self.calls[-1]["messages"][0]["content"]))


def load_cases():
    with CASES.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def api():
    fake = FakeClient()
    app.dependency_overrides[get_client] = lambda: fake
    yield TestClient(app), fake
    app.dependency_overrides.clear()


@pytest.mark.parametrize("row", load_cases(), ids=lambda r: f"case{r['id']}")
def test_every_case_citations_resolve_and_invalid_is_dropped(api, row):
    client, fake = api
    code = classify(pii.strip(row["remark_text"])[0])["code"]
    r = client.post("/explain", json={"code": code, "remark_text": row["remark_text"], "intake": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "fake-model"
    assert body["dropped_sentences"] == 1
    corpus = chunk_by_id()
    cited = [c for p in body["paragraphs"] for c in p["citations"]]
    assert cited, "expected at least one citation"
    for c in cited:
        assert c["id"] in fake.supplied and c["id"] in corpus
        assert c["source_title"] == corpus[c["id"]]["source_title"]
    full = "\n".join(p["text"] for p in body["paragraphs"])
    assert "C9999" not in full
    assert "Next steps:" in full and "3. File the claim again." in full


def test_too_many_invalid_citations_falls_back_to_canned():
    res = explain("R02", "Date of exit not available", client=FakeClient(invalid_sentences=5))
    assert res["model"] == "canned" and res["fallback_reason"] == "citations_invalid"
    assert res["dropped_sentences"] == 5


def test_no_key_and_demo_mode_use_canned():
    assert explain("R01", "Name mismatch", client=None)["fallback_reason"] == "no_api_key"
    fake = FakeClient()
    assert explain("R01", "Name mismatch", client=fake, force_canned=True)["model"] == "canned"
    assert fake.calls == []


def test_refusal_uses_canned():
    assert explain("R04", "Bank KYC not verified", client=FakeClient(stop_reason="refusal"))["model"] == "canned"


@pytest.mark.parametrize("code", [f"R{i:02d}" for i in range(11)])
def test_canned_explanations_exist_and_make_no_promises(code):
    res = explain(code, "", client=None)
    text = " ".join(p["text"] for p in res["paragraphs"]).lower()
    assert "next steps:" in text
    for banned in ("will be approved", "will be settled", "guarantee", "will get your money"):
        assert banned not in text


def test_validator_keeps_trailing_citation_with_its_sentence():
    allowed = {"C1": {"id": "C1", "source_title": "t", "source_url": "u", "source_date": "d"}}
    paras, dropped, total = validate("Rule one applies. [C1] Rule two. [C7]", allowed)
    assert dropped == 1 and total == 2
    assert paras[0]["text"] == "Rule one applies. [C1]"


def test_one_llm_call_per_explanation(api):
    client, fake = api
    client.post("/explain", json={"code": "R02", "remark_text": "Date of exit not available"})
    assert len(fake.calls) == 1
    assert fake.calls[0]["max_tokens"] == 700


def test_no_pii_reaches_logs_or_llm(api, caplog):
    client, fake = api
    with caplog.at_level("DEBUG"):
        for text in SAMPLES:
            code = client.post("/classify", json={"remark_text": text}).json()["code"]
            client.post("/explain", json={"code": code, "remark_text": text})
    # The user-derived part of each prompt (everything before the public source
    # extracts, which contain EPFO office phone numbers) must hold no PII-shaped strings.
    prompts = "\n".join(c["messages"][0]["content"].split("Source extracts:")[0] for c in fake.calls)
    assert not LONG_DIGITS.search(prompts), LONG_DIGITS.search(prompts)
    assert not PAN.search(prompts)
    assert "@example.com" not in prompts
    # Logs include third-party debug lines (request IDs, ETags), so grep them for the
    # exact synthetic PII values rather than for generic digit patterns.
    logs = caplog.text
    logs_digits = re.sub(r"\D", "", logs)
    for text in SAMPLES:
        for m in LONG_DIGITS.finditer(text):
            assert m.group(0) not in logs
            assert re.sub(r"\D", "", m.group(0)) not in logs_digits
        for m in PAN.finditer(text):
            assert m.group(0) not in logs
    assert "@example.com" not in logs
