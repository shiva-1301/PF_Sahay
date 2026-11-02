"""PF Sahay API."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import pii
from app.classifier import classify
from app.config import CORS_ORIGINS
from app.intake import Intake

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("pfsahay")

app = FastAPI(title="PF Sahay", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClassifyRequest(BaseModel):
    remark_text: str = Field(..., max_length=2000)
    intake: Intake = Intake()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify")
def classify_remark(req: ClassifyRequest) -> dict:
    clean, redactions = pii.strip(req.remark_text)
    result = classify(clean, req.intake)
    log.info("classify code=%s confidence=%.2f", result["code"], result["confidence"])
    return {**result, "remark_text": clean, "redactions": redactions}
