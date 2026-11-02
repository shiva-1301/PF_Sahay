"""Deterministic rejection-remark classifier (regex + intake rules, no LLM).

Scoring, per code with at least one trigger match:
    score = 0.60                       a trigger match is enough to reach the threshold
          + 0.15 * matched / total     share of the code's triggers that matched
          + 0.25 * coverage            share of the remark the matched phrases explain
          + intake bonus               from rules/classifier_extra.yaml
A trigger match lying wholly inside a longer match for another code is dropped
(the more specific phrase wins). If the runner-up is within 0.05 of the best, the
confidence is reduced by up to 0.10. Confidence < threshold -> R00 plus one
clarifying question.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from app.config import DATASETS_DIR
from app.intake import JD_MEANING, Intake, jd_category

RULES_PATH = Path(__file__).resolve().parent / "rules" / "classifier_extra.yaml"
FIX_STEPS_PATH = Path(__file__).resolve().parent / "rules" / "fix_steps.yaml"
TAXONOMY_PATH = DATASETS_DIR / "rejection_remarks" / "taxonomy_v1.yaml"

BASE = 0.60
W_SHARE = 0.15
W_COVERAGE = 0.25
AMBIGUITY_MARGIN = 0.05


@dataclass
class _Code:
    code: str
    name: str
    fix_path: str | dict
    documents: list[str]
    triggers: list[re.Pattern] = field(default_factory=list)
    suppress: list[re.Pattern] = field(default_factory=list)


@dataclass
class _Rules:
    threshold: float
    codes: dict[str, _Code]
    intake_bonus: dict
    intake_only: list[dict]
    questions: dict[str, str]


@lru_cache(maxsize=1)
def rules() -> _Rules:
    tax = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8"))
    extra = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    codes = {}
    for code, spec in tax["codes"].items():
        pats = spec.get("triggers", []) + extra["extra_triggers"].get(code, [])
        codes[code] = _Code(
            code=code,
            name=spec["name"],
            fix_path=spec["fix_path"],
            documents=spec.get("documents", []),
            triggers=[re.compile(p, re.I) for p in pats],
            suppress=[re.compile(p, re.I) for p in extra.get("suppress", {}).get(code, [])],
        )
    return _Rules(
        threshold=float(tax.get("confidence_threshold", 0.6)),
        codes=codes,
        intake_bonus=extra.get("intake_bonus", {}),
        intake_only=extra.get("intake_only", []),
        questions=extra["clarifying_questions"],
    )


def normalise(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def confidence_label(conf: float) -> str:
    if conf >= 0.8:
        return "Likely"
    if conf >= 0.6:
        return "Probable"
    return "Unsure"


def fix_steps(fix_path: str) -> list[str]:
    """Split a taxonomy fix_path into ordered, human-readable steps."""
    parts = re.split(r";\s*|\.\s+(?=[A-Z])|\s*->\s*|,?\s*then\s+", fix_path.strip().rstrip("."))
    return [p[0].upper() + p[1:] for p in (s.strip() for s in parts) if p]


@lru_cache(maxsize=1)
def plain_steps() -> dict:
    return yaml.safe_load(FIX_STEPS_PATH.read_text(encoding="utf-8"))


def steps_for(code: str, fix_path: str, cat: Optional[str]) -> list[str]:
    """Plain-language steps for the code (per JD category for R01); else split the taxonomy text."""
    steps = plain_steps().get(code)
    if isinstance(steps, dict):
        steps = steps.get(cat or "unknown")
    return list(steps) if steps else fix_steps(fix_path)


def _matches(spec: _Code, text: str) -> list[tuple[int, int, str]]:
    suppressed = [m.span() for p in spec.suppress for m in p.finditer(text)]
    found = []
    for pat in spec.triggers:
        for m in pat.finditer(text):
            s, e = m.span()
            if e > s and not any(ss <= s and e <= se for ss, se in suppressed):
                found.append((s, e, pat.pattern))
                break  # one hit per trigger is enough
    return found


def _coverage(spans: list[tuple[int, int, str]], length: int) -> float:
    covered: set[int] = set()
    for s, e, _ in spans:
        covered.update(range(s, e))
    return len(covered) / max(length, 1)


def _intake_bonus(intake: Intake, code: str, table: dict) -> float:
    bonus = 0.0
    for fld, by_value in table.items():
        val = getattr(intake, fld, None)
        if val is None:
            continue
        key = str(val).lower() if isinstance(val, bool) else str(val)
        for k, adj in by_value.items():
            if str(k).lower() == key:
                bonus += adj.get(code, 0.0)
    return bonus


def classify(remark: str, intake: Optional[Intake] = None) -> dict:
    """Classify a PII-stripped remark. Returns the API result dict."""
    intake = intake or Intake()
    r = rules()
    text = normalise(remark)

    hits = {code: _matches(spec, text) for code, spec in r.codes.items() if spec.triggers}
    # The more specific phrase wins: drop a match contained in a longer match for another code.
    all_spans = [(s, e, code) for code, hs in hits.items() for s, e, _ in hs]
    for code, hs in hits.items():
        hits[code] = [
            h for h in hs
            if not any(oc != code and os <= h[0] and h[1] <= oe and (oe - os) > (h[1] - h[0])
                       for os, oe, oc in all_spans)
        ]

    scores: dict[str, float] = {}
    for code, hs in hits.items():
        if not hs:
            continue
        share = len(hs) / len(r.codes[code].triggers)
        scores[code] = (BASE + W_SHARE * share + W_COVERAGE * _coverage(hs, len(text))
                        + _intake_bonus(intake, code, r.intake_bonus))

    if not scores:
        for rule in r.intake_only:
            if getattr(intake, rule["field"], None) == rule["value"]:
                scores[rule["code"]] = r.threshold
                hits.setdefault(rule["code"], [])
                break

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_code, best = ranked[0] if ranked else ("R00", 0.0)
    conf = best
    if len(ranked) > 1:
        margin = best - ranked[1][1]
        if margin < AMBIGUITY_MARGIN:
            conf -= (AMBIGUITY_MARGIN - margin) * 2
    conf = round(max(0.0, min(conf, 0.99)), 2)

    cat = jd_category(intake)
    code = best_code if conf >= r.threshold else "R00"
    spec = r.codes[code]
    question = None
    if code == "R00":
        question = _question(r, ranked, intake)

    fp = spec.fix_path
    if isinstance(fp, dict):  # R01: depends on the JD category
        fp = fp[cat] if cat in fp else " ".join(f"Category {k}: {v}" for k, v in fp.items())

    return {
        "code": code,
        "name": spec.name,
        "confidence": conf,
        "confidence_label": confidence_label(conf),
        "matched_phrases": [text[s:e] for s, e, _ in hits.get(best_code, [])] if ranked else [],
        "jd_category": cat,
        "jd_meaning": JD_MEANING.get(cat) if cat else None,
        "fix_path": fp,
        "fix_steps": steps_for(code, fp, cat),
        "documents": spec.documents,
        "clarifying_question": question,
        "candidates": [{"code": c, "score": round(s, 2)} for c, s in ranked[:3]],
    }


def _question(r: _Rules, ranked: list[tuple[str, float]], intake: Intake) -> str:
    if ranked and ranked[0][0] in r.questions:
        return r.questions[ranked[0][0]]
    if intake.exit_date_shown is None:
        return r.questions["R02"]
    if intake.aadhaar_validated is None:
        return r.questions["R05"]
    return r.questions["fallback"]
