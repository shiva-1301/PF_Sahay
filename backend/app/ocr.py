"""Screenshot -> text with Tesseract. Images are read in memory and never saved."""
from __future__ import annotations

import io
from functools import lru_cache

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ACCEPTED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@lru_cache(maxsize=1)
def available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:  # binary missing or not on PATH
        return False


def extract_text(data: bytes) -> str:
    import pytesseract
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as img:
        gray = ImageOps.grayscale(img)
        # small screenshots OCR better when upscaled
        if gray.width < 1200:
            factor = 1200 / gray.width
            gray = gray.resize((1200, int(gray.height * factor)))
        text = pytesseract.image_to_string(gray, lang="eng")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
