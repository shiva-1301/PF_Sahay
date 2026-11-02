"""Remove identity numbers and contact details from free text.

Runs before anything is logged, classified or sent to an LLM. Order matters: the
labelled patterns (UAN, account) run before the bare-digit patterns so a 12-digit
UAN is tagged [UAN] rather than [AADHAAR].
"""
import re
from collections import Counter

_SEP = r"[\s\-]?"
_LABEL_TAIL = r"\.?\s*(?:no\.?|number|num)?\s*[:#\-]?\s*"

# Patterns with a "prefix" group keep the label ("UAN: ", "a/c no. ") and replace the digits.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("UAN", re.compile(rf"(?P<prefix>\buan{_LABEL_TAIL})\d{{4}}{_SEP}\d{{4}}{_SEP}\d{{4}}(?!\d)", re.I)),
    ("ACCOUNT", re.compile(rf"(?P<prefix>\b(?:a/c|acct|account){_LABEL_TAIL})\d(?:[\s\-]?\d){{8,17}}(?!\d)", re.I)),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)),
    ("AADHAAR", re.compile(rf"(?<!\d)\d{{4}}{_SEP}\d{{4}}{_SEP}\d{{4}}(?!\d)")),
    ("MOBILE", re.compile(r"(?<!\d)(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}(?!\d)")),
    # Anything still left with 9+ digits (unlabelled account numbers, member IDs, etc.)
    ("NUMBER", re.compile(r"(?<!\d)\d(?:[\s\-]?\d){8,}(?!\d)")),
]


def strip(text: str) -> tuple[str, dict[str, int]]:
    """Return (clean_text, redaction_counts)."""
    counts: Counter[str] = Counter()
    clean = text or ""
    for label, pat in PATTERNS:
        def sub(m: re.Match, label: str = label) -> str:
            counts[label] += 1
            prefix = m.groupdict().get("prefix") or ""
            return f"{prefix}[{label}]"

        clean = pat.sub(sub, clean)
    return clean, dict(counts)
