"""Paths and settings shared across the backend."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATASETS_DIR = REPO_ROOT / "datasets"

load_dotenv(REPO_ROOT / ".env")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
EXPLAIN_MODEL = os.environ.get("PFSAHAY_EXPLAIN_MODEL", "claude-sonnet-4-5")
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("PFSAHAY_CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
