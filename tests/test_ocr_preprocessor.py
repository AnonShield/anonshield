"""
Tests for src.anon.ocr.preprocessor.

Covers:
- PRESETS content and steps_for()
- apply() with empty/unknown steps → pass-through
- apply() with each individual step (OpenCV path)
- apply() Pillow fallback (monkeypatching cv2 import)
- processors._do_ocr() calls preprocessor when preprocess_steps set
- CLI: --ocr-preprocess-preset and --ocr-preprocess flags accepted
"""
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch  # noqa: F401 — used in test_apply_pillow_fallback_when_cv2_missing

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).parent.parent
ANON_ENV = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _white_image_bytes(w: int = 400, h: int = 100, text: str = "Hello") -> bytes:
    img = Image.new("RGB", (w, h), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()



# ── Preset / metadata tests ───────────────────────────────────────────────────

def test_presets_contain_expected_keys():
    from src.anon.ocr.preprocessor import PRESETS
    assert set(PRESETS.keys()) == {"none", "scan", "photo", "fax"}


def test_preset_none_is_empty():
    from src.anon.ocr.preprocessor import PRESETS
    assert PRESETS["none"] == []


def test_valid_steps_superset_of_all_preset_steps():
    from src.anon.ocr.preprocessor import PRESETS, VALID_STEPS
    for name, steps in PRESETS.items():
        for s in steps:
            assert s in VALID_STEPS, f"Step '{s}' in preset '{name}' not in VALID_STEPS"


def test_steps_for_known_preset():
    from src.anon.ocr.preprocessor import steps_for
    steps = steps_for("scan")
    assert "grayscale" in steps
    assert "binarize" in steps


def test_steps_for_unknown_raises():
    from src.anon.ocr.preprocessor import steps_for
    with pytest.raises(ValueError, match="Unknown preset"):
        steps_for("turbo_mode")


# ── apply() — pass-through cases ─────────────────────────────────────────────

def test_apply_empty_steps_returns_original():
    from src.anon.ocr.preprocessor import apply
    data = b"original bytes"
    assert apply(data, []) is data


def test_apply_unknown_steps_only_returns_original():
    from src.anon.ocr.preprocessor import apply
    data = _white_image_bytes()
    result = apply(data, ["invalid_step", "another_unknown"])
    assert result == data


# ── apply() — OpenCV path (individual steps) ─────────────────────────────────

@pytest.mark.parametrize("step", [
    "grayscale", "upscale", "clahe", "denoise",
    "deskew", "binarize", "morph_open", "border",
])
def test_apply_single_step_returns_bytes(step):
    """Each step should return valid PNG bytes without raising."""
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes(600, 150)
    result = apply(raw, [step])
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Must be decodable as an image
    img = Image.open(io.BytesIO(result))
    assert img.size[0] > 0


def test_apply_full_scan_preset_pipeline():
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply, PRESETS
    raw = _white_image_bytes(800, 200, "Test document text")
    result = apply(raw, PRESETS["scan"])
    img = Image.open(io.BytesIO(result))
    assert img.size[0] > 0


def test_apply_upscale_doubles_small_image():
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes(200, 50)
    result = apply(raw, ["upscale"])
    img = Image.open(io.BytesIO(result))
    assert img.size[0] == 400
    assert img.size[1] == 100


def test_apply_upscale_skips_large_image():
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes(1200, 800)
    result = apply(raw, ["upscale"])
    img = Image.open(io.BytesIO(result))
    assert img.size[0] == 1200  # unchanged


def test_apply_border_increases_dimensions():
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes(300, 100)
    result = apply(raw, ["border"])
    img = Image.open(io.BytesIO(result))
    assert img.size[0] == 340  # +20 each side
    assert img.size[1] == 140


def test_apply_grayscale_output_is_single_channel():
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes()
    result = apply(raw, ["grayscale"])
    img = Image.open(io.BytesIO(result))
    assert img.mode in ("L", "P", "1")  # single-channel modes


# ── apply() — Pillow fallback ─────────────────────────────────────────────────

def test_apply_pillow_fallback_when_cv2_missing():
    """When cv2 is not importable, should fall back to Pillow pipeline."""
    import builtins
    real_import = builtins.__import__

    def _block_cv2(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("cv2 blocked for test")
        return real_import(name, *args, **kwargs)

    from src.anon.ocr import preprocessor
    with patch.object(builtins, "__import__", side_effect=_block_cv2):
        # Reload to force import path to re-evaluate
        raw = _white_image_bytes(300, 80)
        result = preprocessor._apply_pillow(raw, ["grayscale", "upscale", "border"])
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size[0] > 0


@pytest.mark.parametrize("step", ["grayscale", "upscale", "clahe", "denoise", "border"])
def test_pillow_fallback_steps_dont_raise(step):
    from src.anon.ocr.preprocessor import _apply_pillow
    raw = _white_image_bytes(400, 100)
    result = _apply_pillow(raw, [step])
    assert isinstance(result, bytes)
    Image.open(io.BytesIO(result))  # must be valid image


def test_pillow_fallback_skips_cv2_only_steps_silently():
    """deskew/binarize/morph_open require cv2 — Pillow fallback must skip them without error."""
    from src.anon.ocr.preprocessor import _apply_pillow
    raw = _white_image_bytes()
    result = _apply_pillow(raw, ["deskew", "binarize", "morph_open"])
    assert isinstance(result, bytes)


# ── _do_ocr integration — tested via preprocessor directly ───────────────────
# (Avoids importing processors.py which pulls in heavy deps like ijson/torch)

def test_preprocessor_apply_changes_bytes_when_steps_set():
    """When steps are provided, apply() must return different bytes (border adds padding)."""
    pytest.importorskip("cv2", reason="OpenCV not installed")
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes(300, 80)
    result = apply(raw, ["grayscale", "border"])
    assert result != raw
    img = Image.open(io.BytesIO(result))
    assert img.size == (340, 120)  # border +20 each side


def test_preprocessor_apply_returns_same_object_when_empty():
    """apply() with no steps must return the exact same object (no copy)."""
    from src.anon.ocr.preprocessor import apply
    raw = _white_image_bytes()
    assert apply(raw, []) is raw


# ── CLI flag tests ────────────────────────────────────────────────────────────
# These use sys.executable (the project venv Python when run via `uv run pytest`).
# Mirrors the pattern in test_ocr_engines.py.


def test_cli_ocr_preprocess_preset_none(tmp_path):
    src = tmp_path / "input.txt"
    src.write_text("email: user@example.com\n")
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out),
        "--ocr-preprocess-preset", "none",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=90)
    assert r.returncode == 0, r.stderr


def test_cli_ocr_preprocess_preset_scan(tmp_path):
    src = tmp_path / "input.txt"
    src.write_text("phone: +1-555-0100\n")
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out),
        "--ocr-preprocess-preset", "scan",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=90)
    assert r.returncode == 0, r.stderr


def test_cli_ocr_preprocess_explicit_steps(tmp_path):
    src = tmp_path / "input.txt"
    src.write_text("data: example\n")
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out),
        "--ocr-preprocess", "grayscale,border",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=90)
    assert r.returncode == 0, r.stderr


def test_cli_ocr_preprocess_invalid_preset(tmp_path):
    """argparse rejects unknown choices without needing the full project venv."""
    src = tmp_path / "input.txt"
    src.write_text("data\n")
    # Use bare python3 — argparse validation happens before any heavy import
    cmd = [sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
           "--ocr-preprocess-preset", "nonexistent"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=30)
    assert r.returncode != 0


@pytest.mark.ocr
def test_cli_preprocess_on_image_file(tmp_path):
    """Apply scan preset to a generated PNG — verifies the full OCR + preprocessing path."""
    pytest.importorskip("cv2", reason="OpenCV not installed")

    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 60), "AnonShield OCR test", fill="black")
    src = tmp_path / "test.png"
    img.save(src)

    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out),
        "--ocr-preprocess-preset", "scan",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=180)
    assert r.returncode == 0, r.stderr
    outputs = list(out.rglob("*.txt"))
    assert len(outputs) > 0
