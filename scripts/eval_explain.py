"""Live citation-validity check: run the real explanation for every case in cases.csv.

Costs roughly $0.30 of API credit with claude-sonnet-5-5. Only PII-stripped remarks are sent.
Run from the repo root:  .venv/Scripts/python scripts/eval_explain.py   (Windows)
"""
import csv
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import pii  # noqa: E402
from app.classifier import classify  # noqa: E402
from app.explain import explain, get_client  # noqa: E402
from app.retrieval import chunk_by_id  # noqa: E402

CASES = Path(__file__).resolve().parent.parent / "backend" / "tests" / "cases.csv"


def main() -> int:
    client = get_client()
    if client is None:
        print("ANTHROPIC_KEY not set")
        return 1
    corpus = chunk_by_id()
    rows = list(csv.DictReader(CASES.open(encoding="utf-8")))
    times, dropped, sentences, cites, unresolved, fallbacks, uncited_paras = [], 0, 0, 0, 0, {}, 0
    for row in rows:
        clean, _ = pii.strip(row["remark_text"])
        code = classify(clean)["code"]
        t = time.perf_counter()
        res = explain(code, clean, client=client)
        times.append(time.perf_counter() - t)
        if res["fallback_reason"]:
            fallbacks[res["fallback_reason"]] = fallbacks.get(res["fallback_reason"], 0) + 1
        dropped += res["dropped_sentences"]
        sentences += res["sentences"]
        for p in res["paragraphs"]:
            cites += len(p["citations"])
            unresolved += sum(c["id"] not in corpus for c in p["citations"])
            uncited_paras += not p["citations"]
        print(f"#{row['id']:>2} {code} {res['model']:<18} dropped={res['dropped_sentences']}/{res['sentences']} "
              f"{times[-1]:.1f}s", flush=True)
    times.sort()
    live = len(rows) - sum(fallbacks.values())
    print("\nSUMMARY")
    print(f"cases={len(rows)} live={live} fallbacks={fallbacks or 0}")
    print(f"sentences={sentences} dropped={dropped} ({dropped / max(sentences, 1):.1%})")
    print(f"citations returned={cites} unresolved={unresolved}")
    print(f"latency p50={statistics.median(times):.1f}s p95={times[int(0.95 * (len(times) - 1))]:.1f}s max={times[-1]:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
