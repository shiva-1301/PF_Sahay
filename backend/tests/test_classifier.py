import csv
import time
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import pii
from app.classifier import classify, fix_steps
from app.intake import Intake, jd_category
from app.main import app

CASES = Path(__file__).resolve().parent / "cases.csv"
CODES = ["R00"] + [f"R{i:02d}" for i in range(1, 11)]


def load_cases() -> list[dict]:
    with CASES.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def intake_for(row: dict) -> Intake:
    form = row["claim_form"].replace("Form", "").replace("(offline)", "").strip()
    return Intake(claim_form=form if form in {"19", "10C", "10D", "31", "13"} else None)


def confusion_table(pairs: list[tuple[str, str]]) -> str:
    m: dict[str, Counter] = defaultdict(Counter)
    for gold, pred in pairs:
        m[gold][pred] += 1
    head = "gold\\pred " + " ".join(f"{c:>4}" for c in CODES)
    rows = [f"{g:>9} " + " ".join(f"{m[g][p] or '.':>4}" for p in CODES) for g in CODES if m[g]]
    return "\n".join([head, *rows])


def test_accuracy_at_least_80_percent():
    rows = load_cases()
    pairs, misses = [], []
    for row in rows:
        clean, _ = pii.strip(row["remark_text"])
        pred = classify(clean, intake_for(row))["code"]
        pairs.append((row["root_cause_code"], pred))
        if pred != row["root_cause_code"]:
            misses.append(f"  #{row['id']} gold={row['root_cause_code']} pred={pred}: {row['remark_text']}")
    acc = sum(g == p for g, p in pairs) / len(pairs)
    print(f"\naccuracy {acc:.1%} ({sum(g == p for g, p in pairs)}/{len(pairs)})")
    print(confusion_table(pairs))
    print("\n".join(misses))
    assert acc >= 0.80, f"accuracy {acc:.1%}\n{confusion_table(pairs)}\n" + "\n".join(misses)


@pytest.mark.parametrize("uan,aadhaar,expected", [
    ("after_oct_2017", True, "A"),
    ("before_oct_2017", True, "B"),
    ("after_oct_2017", False, "C"),
    ("no_uan", None, "C"),
    ("not_sure", True, None),
    (None, None, None),
])
def test_jd_category(uan, aadhaar, expected):
    assert jd_category(Intake(uan_issued=uan, aadhaar_validated=aadhaar)) == expected


def test_low_confidence_gives_r00_with_question():
    res = classify("Claim rejected. Reason: others")
    assert res["code"] == "R00"
    assert res["clarifying_question"]


def test_intake_answer_resolves_unclassified_remark():
    res = classify("Claim rejected. Reason: others", Intake(exit_date_shown=False))
    assert res["code"] == "R02"
    assert res["confidence_label"] == "Probable"


def test_exit_date_shown_false_boosts_r02():
    base = classify("Date of exit not available")["confidence"]
    boosted = classify("Date of exit not available", Intake(exit_date_shown=False))["confidence"]
    assert boosted > base


def test_r01_fix_path_follows_jd_category():
    a = classify("Name mismatch", Intake(uan_issued="after_oct_2017", aadhaar_validated=True))
    c = classify("Name mismatch", Intake(aadhaar_validated=False))
    assert a["jd_category"] == "A" and "Member e-Sewa" in a["fix_path"]
    assert c["jd_category"] == "C" and "Physical JD" in c["fix_path"]


def test_fix_steps_split():
    steps = fix_steps("Wait for earlier claim; request closure via EPFiGMS if stale.")
    assert steps == ["Wait for earlier claim", "Request closure via EPFiGMS if stale"]


def test_classify_endpoint_strips_pii_and_logs_only_code(caplog):
    client = TestClient(app)
    with caplog.at_level("INFO"):
        r = client.post("/classify", json={
            "remark_text": "UAN 100123456789 Date of exit not available, PAN ABCPE1234F",
            "intake": {"claim_form": "19", "exit_date_shown": False},
        })
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "R02"
    assert body["redactions"] == {"UAN": 1, "PAN": 1}
    assert "100123456789" not in caplog.text and "ABCPE1234F" not in caplog.text
    assert "date of exit" not in caplog.text.lower()


def test_classify_p95_latency_under_200ms():
    client = TestClient(app)
    rows = load_cases()
    times = []
    for i in range(100):
        row = rows[i % len(rows)]
        t = time.perf_counter()
        r = client.post("/classify", json={"remark_text": row["remark_text"], "intake": {}})
        times.append(time.perf_counter() - t)
        assert r.status_code == 200
    times.sort()
    p95 = times[94]
    print(f"\n/classify p95 = {p95 * 1000:.1f} ms")
    assert p95 < 0.2


def test_paraphrases_at_least_80_percent():
    """Regression guard on remarks phrased differently from the seed set."""
    with (Path(__file__).resolve().parent / "heldout_paraphrases.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok = sum(classify(pii.strip(r["remark_text"])[0])["code"] == r["root_cause_code"] for r in rows)
    print(f"\nparaphrase accuracy {ok}/{len(rows)}")
    assert ok / len(rows) >= 0.80
