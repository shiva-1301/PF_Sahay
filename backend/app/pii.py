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


# Personal names: 2-5 capitalised words right after a cue word ("Aadhaar RAMESH K SINGH",
# "my name is Ramesh Kumar"). Each distinct name becomes [NAME_1], [NAME_2], ... so an
# explanation can still say the two names differ.
NAME_CUE = re.compile(
    # cue words match in any case; the name itself must be capitalised
    r"(?P<prefix>(?i:\b(?:aadhaar|uan|pan|bank|account|records?|name|father'?s? name|"
    r"mother'?s? name|spouse'?s? name|husband|wife|nominee|applicant|member)"
    r"\b\s*(?:is|was|as|reads|shows|says)?\s*[:\-=(\"']?\s*))"
    r"(?P<name>[A-Z][A-Za-z.']*(?:\s+[A-Z][A-Za-z.']*){1,4})"
)
NOT_NAME_WORDS = {
    "aadhaar", "uan", "pan", "pf", "epf", "epfo", "eps", "kyc", "bank", "ifsc", "name", "names",
    "not", "no", "and", "or", "vs", "v", "the", "of", "in", "as", "per", "is", "date", "birth",
    "dob", "doe", "doj", "gender", "father", "mother", "spouse", "member", "details", "records",
    "record", "mismatch", "matching", "match", "verified", "validated", "seeded", "linked",
    "account", "form", "claim", "rejected", "reason", "service", "exit", "joining", "employer",
    "uidai", "differs", "different", "updated", "available", "pending", "wrong", "invalid",
}


def _mask_names(text: str, counts: Counter) -> str:
    seen: dict[str, str] = {}

    def sub(m: re.Match) -> str:
        words = m.group("name").split()
        # trim leading/trailing words that are domain terms, not parts of a name
        while words and words[0].lower().strip(".'") in NOT_NAME_WORDS:
            words.pop(0)
        while words and words[-1].lower().strip(".'") in NOT_NAME_WORDS:
            words.pop()
        if len(words) < 2 or any(w.lower().strip(".'") in NOT_NAME_WORDS for w in words):
            return m.group(0)
        key = " ".join(w.upper().strip(".") for w in words)
        if key not in seen:
            seen[key] = f"[NAME_{len(seen) + 1}]"
            counts["NAME"] += 1
        name_text = " ".join(words)
        start = m.group(0).index(name_text, len(m.group("prefix")))
        return m.group(0)[:start] + seen[key] + m.group(0)[start + len(name_text):]

    return NAME_CUE.sub(sub, text)


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
    clean = _mask_names(clean, counts)
    return clean, dict(counts)
