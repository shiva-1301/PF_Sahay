"""Download the EPFO member-services circular PDFs listed in the dataset CSV.

Reads datasets/epfo_circulars/member_services_circulars_2019_2026.csv, fetches each
english_pdf_link into datasets/circular_pdfs/epfo/ with a 1-second delay between
requests and one retry, and writes download_log.csv (url, status, bytes, sha256).

Usage: python scripts/download_circulars.py [--limit N]
"""
import argparse
import csv
import hashlib
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

REPO = Path(__file__).resolve().parent.parent
CSV_PATH = REPO / "datasets" / "epfo_circulars" / "member_services_circulars_2019_2026.csv"
OUT_DIR = REPO / "datasets" / "circular_pdfs" / "epfo"
LOG_PATH = OUT_DIR / "download_log.csv"
HEADERS = {"User-Agent": "PF-Sahay-research/0.1 (Indiathon 2026; polite single-threaded fetch)"}
DELAY_S = 1.0
TIMEOUT_S = 30


def fetch(session: requests.Session, url: str) -> tuple[str, bytes | None]:
    """Return (status, body). Retries once on any failure."""
    last = "error"
    for attempt in range(2):
        try:
            r = session.get(url, headers=HEADERS, timeout=TIMEOUT_S, allow_redirects=True)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                return "200", r.content
            last = f"http_{r.status_code}" if r.status_code != 200 else "not_pdf"
        except requests.RequestException as e:
            last = type(e).__name__
        if attempt == 0:
            time.sleep(DELAY_S)
    return last, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only try the first N links")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open(encoding="utf-8") as f:
        urls = [row["english_pdf_link"].strip() for row in csv.DictReader(f) if row.get("english_pdf_link")]
    urls = list(dict.fromkeys(urls))  # dedupe, keep order
    if args.limit:
        urls = urls[: args.limit]

    ok = 0
    session = requests.Session()
    with LOG_PATH.open("w", newline="", encoding="utf-8") as logf:
        log = csv.writer(logf)
        log.writerow(["url", "status", "bytes", "sha256"])
        for i, url in enumerate(urls, 1):
            name = Path(urlparse(url).path).name or f"circular_{i}.pdf"
            dest = OUT_DIR / name
            if dest.exists() and dest.stat().st_size > 0:
                body = dest.read_bytes()
                status = "cached"
            else:
                status, body = fetch(session, url)
                if body:
                    dest.write_bytes(body)
                time.sleep(DELAY_S)
            size = len(body) if body else 0
            sha = hashlib.sha256(body).hexdigest() if body else ""
            log.writerow([url, status, size, sha])
            logf.flush()
            if body:
                ok += 1
            print(f"[{i}/{len(urls)}] {status:>12} {name}", flush=True)

    print(f"\n{ok}/{len(urls)} PDFs available in {OUT_DIR}")
    print(f"Log: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
