"""Call the real Claude API for three sample remarks and print the explanations.

Uses ANTHROPIC_KEY from .env (costs a few cents). Run from the repo root:
    .venv/Scripts/python scripts/try_explain.py     (Windows)
    .venv/bin/python scripts/try_explain.py         (macOS / Linux)
"""
import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import pii  # noqa: E402
from app.classifier import classify  # noqa: E402
from app.explain import explain, get_client  # noqa: E402
from app.intake import Intake  # noqa: E402

CASES = [
    ("Name mismatch: Aadhaar RAMESH KUMAR SINGH vs UAN RAMESH K SINGH",
     Intake(claim_form="19", uan_issued="after_oct_2017", aadhaar_validated=True)),
    ("Date of exit not available", Intake(claim_form="19", exit_date_shown=False)),
    ("Multiple UAN found against the member", Intake(claim_form="19")),
]


def main() -> int:
    client = get_client()
    if client is None:
        print("ANTHROPIC_KEY is not set in .env; the app would use canned explanations.")
        return 1
    for remark, intake in CASES:
        clean, _ = pii.strip(remark)
        diag = classify(clean, intake)
        t = time.perf_counter()
        res = explain(diag["code"], clean, intake, client=client)
        secs = time.perf_counter() - t
        print("=" * 78)
        print(f"Remark : {remark}")
        print(f"Code   : {diag['code']} {diag['name']} ({diag['confidence_label']}, JD {diag['jd_category']})")
        print(f"Model  : {res['model']}  dropped={res['dropped_sentences']}  "
              f"fallback={res['fallback_reason']}  {secs:.1f}s\n")
        for p in res["paragraphs"]:
            print(textwrap.indent(p["text"], "  "))
            for c in p["citations"]:
                print(f"    -> [{c['id']}] {c['source_title'][:70]} ({c['source_date'] or 'n.d.'})")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
