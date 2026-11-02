"""PF Sahay API."""
import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal, Optional

import anthropic
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app import documents, pii
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
    return {**result, "remark_text": clean, "redactions": redactions,
            "recommended_documents": documents.recommended_documents(result["code"])}


@app.post("/explain")
def explain_diagnosis(req: ExplainRequest,
                      client: Optional[anthropic.Anthropic] = Depends(get_client)) -> dict:
    clean, _ = pii.strip(req.remark_text)
    return explain(req.code, clean, req.intake, client=client, force_canned=req.canned)


class DocumentsRequest(BaseModel):
    code: Code
    intake: Intake = Intake()
    fields: documents.DocFields = documents.DocFields()
    remark_text: str = Field("", max_length=2000)
    docs: Optional[list[documents.DocName]] = None  # default: recommended for the code


@app.post("/documents")
def generate_documents(req: DocumentsRequest) -> Response:
    """One PDF if exactly one doc is requested, otherwise a zip. Nothing is stored."""
    # Documents go back to the member only: keep names, remove identity numbers.
    clean, _ = pii.strip(req.remark_text, mask_names=False)
    files = documents.build(req.code, req.intake, req.fields, clean, req.docs)
    log.info("documents code=%s count=%d", req.code, len(files))
    no_store = {"Cache-Control": "no-store"}
    if len(files) == 1:
        name, data = files[0]
        return Response(data, media_type="application/pdf",
                        headers={**no_store, "Content-Disposition": f'attachment; filename="{name}"'})
    return Response(documents.zip_bytes(files), media_type="application/zip",
                    headers={**no_store, "Content-Disposition": f'attachment; filename="PFSahay_{req.code}_documents.zip"'})


@app.post("/documents/text")
def documents_text(req: DocumentsRequest) -> dict:
    """Plain text of the grievance, for the copy-to-clipboard button."""
    clean, _ = pii.strip(req.remark_text, mask_names=False)
    ctx = documents.context(req.code, req.intake, req.fields, clean)
    return {"grievance": documents.grievance_text(ctx)}


@app.get("/offices")
def list_offices() -> list[dict]:
    return documents.offices()
