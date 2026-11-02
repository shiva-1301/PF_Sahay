import re

import pytest

from app import pii
from tests.pii_samples import SAMPLES

LONG_DIGITS = re.compile(r"\d(?:[\s\-]?\d){8,}")  # 9+ digits, allowing spaces/hyphens
PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)


def test_fifty_samples():
    assert len(SAMPLES) == 50


@pytest.mark.parametrize("text", SAMPLES)
def test_no_long_digits_or_pan_survive(text):
    clean, counts = pii.strip(text)
    assert not LONG_DIGITS.search(clean), clean
    assert not PAN.search(clean), clean
    assert sum(counts.values()) >= 1


@pytest.mark.parametrize("text,label", [
    ("UAN 100123456789 date of exit not available", "[UAN]"),
    ("UAN: 1001 2345 6789", "[UAN]"),
    ("Aadhaar 2345 6789 0123 not verified", "[AADHAAR]"),
    ("PAN ABCPE1234F not verified", "[PAN]"),
    ("a/c no. 123456789012 mismatch", "[ACCOUNT]"),
    ("Account number: 00112233445566", "[ACCOUNT]"),
    ("call 9876543210", "[MOBILE]"),
    ("call +91 98765 43210", "[MOBILE]"),
    ("write to me@example.co.in", "[EMAIL]"),
])
def test_labels(text, label):
    clean, _ = pii.strip(text)
    assert label in clean, clean


def test_remark_text_untouched():
    for remark in ["Date of exit not available", "Form 15G not uploaded for amount above 50000",
                   "Service more than 9.5 years; apply for pension in Form 10D instead of 10C",
                   "IFSC code invalid or bank account not seeded", "UAN not Aadhaar validated"]:
        assert pii.strip(remark) == (remark, {})
