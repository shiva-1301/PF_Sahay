import json
from pathlib import Path

import numpy as np

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def test_every_code_has_two_chunks_and_embeddings_align():
    chunks = json.loads((CORPUS / "chunks.json").read_text(encoding="utf-8"))
    emb = np.load(CORPUS / "embeddings.npy")
    assert emb.shape == (len(chunks), 384)
    assert len({c["id"] for c in chunks}) == len(chunks)
    for code in [f"R{i:02d}" for i in range(1, 11)]:
        assert sum(code in c["codes"] for c in chunks) >= 2, code
    for c in chunks:
        assert c["source_title"] and c["text"]
        assert len(c["text"].split()) <= 400
