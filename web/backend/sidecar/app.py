"""HTTP wrapper around anon.ocr engines that need a non-default Python env.

Used by the legacy_vlm sidecar (transformers 4.51 → paddle_vl, monkey_ocr)
and the kerasocr sidecar (TensorFlow → kerasocr). The same code serves both
images — each one only has its own engines installed, so requests for an
unsupported engine return 503.
"""
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from anon.ocr.factory import get_ocr_engine

app = FastAPI()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/engines")
def engines() -> dict:
    """Probe every known engine name; return whichever ones load in this image."""
    avail = {}
    for name in [
        "tesseract", "easyocr", "paddleocr", "doctr", "onnxtr", "kerasocr",
        "surya", "rapidocr", "glm_ocr", "paddle_vl", "deepseek_ocr",
        "monkey_ocr", "lighton_ocr", "chandra_ocr", "dots_ocr", "qwen_vl",
    ]:
        try:
            avail[name] = get_ocr_engine(name).is_available()
        except Exception:
            avail[name] = False
    return avail


@app.post("/ocr/{engine}", response_class=PlainTextResponse)
async def ocr(engine: str, file: UploadFile) -> str:
    try:
        eng = get_ocr_engine(engine)
    except Exception:
        raise HTTPException(503, f"engine {engine!r} not in this sidecar")
    if not eng.is_available():
        raise HTTPException(503, f"engine {engine!r} is_available() returned False")
    data = await file.read()
    return eng.extract_text(data)
