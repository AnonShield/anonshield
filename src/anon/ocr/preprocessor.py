"""Image preprocessing pipeline for OCR quality improvement.

Steps are applied in the order given. Recommended canonical order:
    grayscale → upscale → clahe → denoise → deskew → binarize → morph_open → border

Presets:
    none   — pass-through (no processing)
    scan   — scanned documents (uneven lighting, possible skew)
    photo  — camera-captured pages (noise, perspective, low DPI)
    fax    — fax / dot-matrix / heavy photocopy (thin strokes, speckles)
"""
from __future__ import annotations

import io
import logging
from collections.abc import Sequence

logger = logging.getLogger(__name__)

VALID_STEPS: frozenset[str] = frozenset({
    "grayscale",
    "upscale",
    "clahe",
    "denoise",
    "deskew",
    "binarize",
    "morph_open",
    "border",
})

PRESETS: dict[str, list[str]] = {
    "none": [],
    "scan": ["grayscale", "upscale", "clahe", "denoise", "deskew", "binarize", "border"],
    "photo": ["grayscale", "upscale", "clahe", "denoise", "deskew", "binarize", "morph_open", "border"],
    "fax": ["grayscale", "upscale", "clahe", "denoise", "binarize", "morph_open", "border"],
}


def steps_for(preset: str) -> list[str]:
    """Return the step list for a named preset. Raises ValueError for unknown names."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Valid: {sorted(PRESETS)}")
    return list(PRESETS[preset])


def apply(image_bytes: bytes, steps: Sequence[str]) -> bytes:
    """Apply preprocessing steps to raw image bytes. Returns processed PNG bytes.

    Falls back to a Pillow-only pipeline if OpenCV is not installed (limited steps).
    Unknown step names are silently skipped.
    """
    if not steps:
        return image_bytes
    valid = [s for s in steps if s in VALID_STEPS]
    if not valid:
        return image_bytes
    try:
        import cv2  # noqa: F401
        return _apply_cv2(image_bytes, valid)
    except ImportError:
        logger.debug("opencv not available — using Pillow fallback for preprocessing")
        return _apply_pillow(image_bytes, valid)


# ── OpenCV pipeline ───────────────────────────────────────────────────────────

def _apply_cv2(image_bytes: bytes, steps: Sequence[str]) -> bytes:
    import cv2
    import numpy as np
    from PIL import Image

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    for step in steps:
        img = _CV2_STEP[step](img)

    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("cv2.imencode failed on preprocessed image")
    return bytes(buf)


def _cv2_grayscale(img):
    import cv2
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img


def _cv2_upscale(img):
    import cv2
    h, w = img.shape[:2]
    if max(h, w) < 1000:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
    return img


def _cv2_clahe(img):
    import cv2
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)


def _cv2_denoise(img):
    import cv2
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(img, (3, 3), 0)


def _cv2_deskew(img):
    import cv2
    import numpy as np
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 10:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _cv2_binarize(img):
    import cv2
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)


def _cv2_morph_open(img):
    import cv2
    if len(img.shape) == 3:
        _, img = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)


def _cv2_border(img):
    import cv2
    return cv2.copyMakeBorder(img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


_CV2_STEP = {
    "grayscale": _cv2_grayscale,
    "upscale":   _cv2_upscale,
    "clahe":     _cv2_clahe,
    "denoise":   _cv2_denoise,
    "deskew":    _cv2_deskew,
    "binarize":  _cv2_binarize,
    "morph_open":_cv2_morph_open,
    "border":    _cv2_border,
}

# ── Pillow fallback ───────────────────────────────────────────────────────────

def _apply_pillow(image_bytes: bytes, steps: Sequence[str]) -> bytes:
    from PIL import Image, ImageFilter, ImageOps

    img = Image.open(io.BytesIO(image_bytes))

    for step in steps:
        if step == "grayscale":
            img = img.convert("L")
        elif step == "upscale":
            w, h = img.size
            if max(w, h) < 1000:
                img = img.resize((w * 2, h * 2), Image.LANCZOS)
        elif step == "clahe":
            if img.mode != "L":
                img = img.convert("L")
            img = ImageOps.equalize(img)
        elif step == "denoise":
            img = img.filter(ImageFilter.GaussianBlur(radius=1))
        elif step == "border":
            fill = 255 if img.mode == "L" else (255, 255, 255)
            img = ImageOps.expand(img, border=20, fill=fill)
        # deskew / binarize / morph_open require OpenCV — skip gracefully

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
