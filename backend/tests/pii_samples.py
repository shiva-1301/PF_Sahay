"""Synthetic PII strings shared by the PII and log-leak tests. All numbers are fake."""
import random

_rng = random.Random(20261101)


def _digits(n: int) -> str:
    return "".join(_rng.choice("0123456789") for _ in range(n))


def _aadhaar(sep: str = " ") -> str:
    d = str(_rng.randint(2, 9)) + _digits(11)
    return sep.join([d[:4], d[4:8], d[8:]])


def _pan() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(_rng.choice(letters) for _ in range(3)) + "P" + _rng.choice(letters) + _digits(4) + _rng.choice(letters)


def _mobile() -> str:
    return str(_rng.choice("6789")) + _digits(9)


TEMPLATES = [
    lambda: f"KYC details not matching. Aadhaar {_aadhaar()} name differs",
    lambda: f"Aadhaar no: {_aadhaar('-')} not verified",
    lambda: f"aadhaar {_aadhaar('')} wrong aadhaar linked",
    lambda: f"UAN {_digits(12)} date of exit not available",
    lambda: f"UAN: {_aadhaar(' ')} still in service",
    lambda: f"UAN No. {_digits(12)}; claim already under process",
    lambda: f"PAN {_pan()} not verified",
    lambda: f"pan {_pan().lower()} tds deducted",
    lambda: f"Bank a/c {_digits(_rng.randint(9, 18))} IFSC SBIN0001234 mismatch",
    lambda: f"Account no: {_digits(_rng.randint(9, 18))} name in bank differs",
    lambda: f"acct {_digits(11)} not seeded",
    lambda: f"Call me on {_mobile()} about date of exit",
    lambda: f"mobile +91 {_mobile()} member details mismatch",
    lambda: f"Contact +91-{_mobile()[:5]} {_mobile()[:5]} for KYC",
    lambda: f"email ramesh.k{_digits(3)}@example.com, phone 0{_mobile()}",
    lambda: f"Member id MHBAN{_digits(17)} erroneously linked",
    lambda: f"Ref {_digits(10)} service overlap with {_digits(14)}",
    lambda: f"{_aadhaar()} / {_pan()} / {_mobile()} all mine",
    lambda: f"Name mismatch: Aadhaar RAMESH KUMAR SINGH ({_aadhaar()}) vs UAN RAMESH K SINGH ({_digits(12)})",
    lambda: f"Claim ID {_digits(9)} rejected, account {_digits(16)}",
]

SAMPLES: list[str] = [TEMPLATES[i % len(TEMPLATES)]() for i in range(50)]
