"""Write four sample PDFs so you can open and check them.

Output: /tmp/pfsahay_samples/ (macOS/Linux) or %TEMP%\\pfsahay_samples (Windows),
or the folder given with --out. All names and numbers are synthetic.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import pii  # noqa: E402
from app.documents import DocFields, build  # noqa: E402
from app.intake import Intake  # noqa: E402

FIELDS = DocFields(
    member_name="Ramesh Kumar Singh", employer_name="Acme Textiles Pvt Ltd",
    employer_address="Plot 4, Industrial Estate, Guntur", uan_last4="1234",
    claim_id="GNT2026110100123", claim_date="01/10/2026", rejection_date="15/10/2026",
    date_of_joining="01/04/2019", date_of_exit="31/07/2026", regional_office="Guntur", place="Guntur",
)
SAMPLES = [
    ("R01", Intake(claim_form="19", uan_issued="before_oct_2017", aadhaar_validated=True),
     "Name mismatch: Aadhaar RAMESH KUMAR SINGH vs UAN RAMESH K SINGH", "employer_letter"),
    ("R01", Intake(claim_form="19", aadhaar_validated=False),
     "Name mismatch: Aadhaar RAMESH KUMAR SINGH vs UAN RAMESH K SINGH", "jd_checklist"),
    ("R02", Intake(claim_form="19", exit_date_shown=False), "Date of exit not available", "grievance"),
    ("R02", Intake(claim_form="19", exit_date_shown=False), "Date of exit not available", "rti"),
]


def default_out() -> Path:
    base = Path(tempfile.gettempdir()) if os.name == "nt" else Path("/tmp")
    return base / "pfsahay_samples"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=default_out())
    out = ap.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for code, intake, remark, doc in SAMPLES:
        clean, _ = pii.strip(remark, mask_names=False)
        for name, data in build(code, intake, FIELDS, clean, [doc]):
            path = out / name
            path.write_bytes(data)
            print(f"{len(data) / 1024:6.1f} kB  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
