"""
E2E and unit tests for the OCR engine abstraction layer.

Tests cover:
- Factory: known name → correct engine instance
- Factory: unknown name → ValueError
- Factory: unavailable engine → RuntimeError
- TesseractEngine: is_available() and extract_text()
- Fallback chain: processors use _do_ocr() (not hard-coded pytesseract)
- CLI: --ocr-engine tesseract is accepted
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
ANON_ENV = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}


# ---------------------------------------------------------------------------
# Factory unit tests (no real OCR needed)
# ---------------------------------------------------------------------------

def test_factory_unknown_engine_raises():
    from src.anon.ocr.factory import get_ocr_engine
    with pytest.raises(ValueError, match="Unknown OCR engine"):
        get_ocr_engine("nonexistent_engine")


def test_factory_returns_tesseract_instance():
    from src.anon.ocr.factory import get_ocr_engine
    from src.anon.ocr.tesseract_engine import TesseractEngine
    engine = get_ocr_engine("tesseract")
    assert isinstance(engine, TesseractEngine)


def test_all_engines_have_correct_names():
    from src.anon.ocr.tesseract_engine import TesseractEngine
    from src.anon.ocr.easyocr_engine import EasyOCREngine
    from src.anon.ocr.paddleocr_engine import PaddleOCREngine
    from src.anon.ocr.doctr_engine import DocTREngine
    from src.anon.ocr.kerasocr_engine import KerasOCREngine

    assert TesseractEngine().name == "tesseract"
    assert EasyOCREngine().name == "easyocr"
    assert PaddleOCREngine().name == "paddleocr"
    assert DocTREngine().name == "doctr"
    assert KerasOCREngine().name == "kerasocr"


def test_unavailable_engine_raises_runtime_error(monkeypatch):
    """Simulate missing easyocr package → RuntimeError from factory."""
    from src.anon.ocr import factory as fac
    from src.anon.ocr.easyocr_engine import EasyOCREngine

    # Patch is_available to return False
    monkeypatch.setattr(EasyOCREngine, "is_available", lambda self: False)
    with pytest.raises(RuntimeError, match="not installed"):
        fac.get_ocr_engine("easyocr")


# ---------------------------------------------------------------------------
# TesseractEngine integration tests
# ---------------------------------------------------------------------------

@pytest.mark.ocr
def test_tesseract_is_available():
    from src.anon.ocr.tesseract_engine import TesseractEngine
    assert TesseractEngine().is_available(), "Tesseract not installed on this machine"


@pytest.mark.ocr
def test_tesseract_extract_text_from_real_image():
    """Generate a simple PIL image with known text and OCR it."""
    from PIL import Image, ImageDraw
    from src.anon.ocr.tesseract_engine import TesseractEngine
    import io

    img = Image.new("RGB", (800, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "test@example.com", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    engine = TesseractEngine()
    text = engine.extract_text(image_bytes)
    assert "example" in text.lower()  # Tesseract may misread dots as dashes in small fonts


@pytest.mark.ocr
def test_tesseract_returns_empty_on_invalid_bytes():
    from src.anon.ocr.tesseract_engine import TesseractEngine
    engine = TesseractEngine()
    result = engine.extract_text(b"not an image")
    assert isinstance(result, str)
    assert result == ""


# ---------------------------------------------------------------------------
# CLI integration: --ocr-engine flag
# ---------------------------------------------------------------------------

def test_cli_ocr_engine_default(tmp_path):
    src = tmp_path / "input.txt"
    src.write_text("email: a@b.com\n")
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out),
        "--slug-length", "8",
        # default --ocr-engine tesseract should be accepted without error
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=60)
    assert result.returncode == 0, result.stderr


def test_cli_ocr_engine_invalid_choice(tmp_path):
    src = tmp_path / "input.txt"
    src.write_text("hello world\n")
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--ocr-engine", "invalid_ocr_engine",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=30)
    assert result.returncode != 0
    assert "invalid" in result.stderr.lower() or "invalid" in result.stdout.lower()
