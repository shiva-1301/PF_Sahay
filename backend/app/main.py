"""PF Sahay API."""
import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal, Optional

import anthropic
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import pii
from app.classifier import classify
from app.config import CORS_ORIGINS
from app.explain import explain, get_client
from app.intake import Intake
from app.retrieval import embed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("pfsahay")

Code = Literal["R00", "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the embedding model in the background so the first /explain is fast.
    threading.Thread(target=embed, args=("warm up",), daemon=True).start()
    yield


app = FastAPI(title="PF Sahay", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClassifyRequest(BaseModel):
    remark_text: str = Field(..., max_length=2000)
    intake: Intake = Intake()


class ExplainRequest(BaseModel):
    code: Code
    remark_text: str = Field("", max_length=2000)
    intake: Intake = Intake()
    canned: bool = False  # demo mode: never call the API


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify")
def classify_remark(req: ClassifyRequest) -> dict:
    clean, redactions = pii.strip(req.remark_text)
    result = classify(clean, req.intake)
    log.info("classify code=%s confidence=%.2f", result["code"], result["confidence"])
    return {**result, "remark_text": clean, "redactions": redactions}


@app.post("/explain")
def explain_diagnosis(req: ExplainRequest,
                      client: Optional[anthropic.Anthropic] = Depends(get_client)) -> dict:
    clean, _ = pii.strip(req.remark_text)
    return explain(req.code, clean, req.intake, client=client, force_canned=req.canned)
