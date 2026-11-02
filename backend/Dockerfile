# PF Sahay backend. Build from the repository root (the backend reads datasets/):
#   docker build -f backend/Dockerfile -t pfsahay-api .
#   docker run -p 8000:8000 -e ANTHROPIC_KEY=... pfsahay-api
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

# Tesseract enables screenshot upload (OCR); remove it to shrink the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch first, so sentence-transformers does not pull the CUDA build.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r backend/requirements.txt

# Bake the embedding model into the image; no Hugging Face calls at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY datasets/rejection_remarks datasets/rejection_remarks
COPY datasets/joint_declaration datasets/joint_declaration
COPY datasets/epfo_offices datasets/epfo_offices
COPY backend backend

RUN useradd --create-home pfsahay && chown -R pfsahay /app /opt/hf
USER pfsahay
WORKDIR /app/backend

ENV HF_HUB_OFFLINE=1 \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
