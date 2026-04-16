"""Dataset downloaders and loaders for the OCR benchmark.

Public datasets used (see METHODOLOGY.md §4 and top-level research findings):

  BID   — Brazilian Identity Documents (CNH, CPF, RG), SIBGRAPI 2020
          https://github.com/ricardobnjunior/Brazilian-Identity-Document-Dataset
          28 800 images / classification labels + VIA bounding-box annotations

  ESTER — ESTER-Pt: Evaluation Suite for Text Recognition in Portuguese, ICDAR 2023
          https://zenodo.org/records/7872951
          ~19.6 GB / real scanned + synthetic / line-level GT (PT-BR, UFRGS)

  XFUND — Multilingual Form Understanding, ACL 2022 (Portuguese subset)
          https://github.com/doc-analysis/XFUND/releases/tag/v1.0
          199 images / word-level bbox + KV annotations / PT (variant unconfirmed)

Not implemented (future work — see METHODOLOGY.md §8):
  Level 2: Synthetic generation with Faker + document templates
  Level 3: Zero-shot GT via VLM oracle
"""
import hashlib
import json
import logging
import re
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .metrics import normalize

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class Sample:
    """One benchmarkable image + ground truth pair."""
    id: str
    image_path: Path
    reference_text: str                         # page-level plain text GT
    quality_tier: str                           # clean | degraded | synthetic
    doc_type: str                               # free_text | form | table | mixed
    fields: dict[str, str] = field(default_factory=dict)   # for form docs
    dataset: str = ""                           # BID | ESTER | XFUND


@dataclass
class DatasetInfo:
    name: str
    url: str
    sha256: str | None           # None = not verified (large files)
    expected_size_mb: float
    license: str
    doc_types: list[str]


# ---------------------------------------------------------------------------
# Registry of public datasets
# ---------------------------------------------------------------------------

_XFUND_PT_URLS = [
    "https://github.com/doc-analysis/XFUND/releases/download/v1.0/pt.train.json",
    "https://github.com/doc-analysis/XFUND/releases/download/v1.0/pt.train.zip",
    "https://github.com/doc-analysis/XFUND/releases/download/v1.0/pt.val.json",
    "https://github.com/doc-analysis/XFUND/releases/download/v1.0/pt.val.zip",
]

_DATASETS: dict[str, DatasetInfo] = {
    "bid_sample": DatasetInfo(
        name="BID Dataset (sample — CNH/CPF/RG)",
        url="https://drive.google.com/uc?export=download&id=144EqqmMtCziua9iYo-3afUEvZrJVxUXU",
        sha256=None,
        expected_size_mb=50,
        license="Unspecified — academic use only. Contact: ricardobnjunior@gmail.com",
        doc_types=["form"],
    ),
    "ester_pt": DatasetInfo(
        name="ESTER-Pt (ICDAR 2023, UFRGS)",
        url="https://zenodo.org/records/7872951/files/ESTER-Pt.zip",
        sha256=None,
        expected_size_mb=19_600,
        license="CC-BY 4.0",
        doc_types=["free_text", "degraded"],
    ),
    "xfund_pt": DatasetInfo(
        name="XFUND Portuguese Subset (ACL 2022)",
        url=_XFUND_PT_URLS[0],   # placeholder; download_dataset handles multi-file
        sha256=None,
        expected_size_mb=40,
        license="CC BY-NC-SA 4.0",
        doc_types=["form"],
    ),
}

NUMERIC_FIELDS: set[str] = {
    "rg_numero", "cpf_numero", "numero_registro", "data_nascimento",
    "data_expedicao", "validade", "livro", "folha", "termo",
}


# ---------------------------------------------------------------------------
# Download utilities
# ---------------------------------------------------------------------------

def _sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    logger.info("Downloading %s → %s", url, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AnonShield-OCR-Bench/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
            shutil.copyfileobj(resp, fh)
    except Exception as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc


def download_dataset(key: str, data_dir: Path) -> Path:
    """Download a dataset archive if not already present. Returns local extracted path."""
    info = _DATASETS[key]
    dest_dir = data_dir / key
    done_marker = dest_dir / ".downloaded"
    if done_marker.exists():
        logger.info("%s already downloaded.", key)
        return dest_dir

    dest_dir.mkdir(parents=True, exist_ok=True)

    # XFUND-PT: 4 separate files (train+val JSON + ZIP)
    if key == "xfund_pt":
        for url in _XFUND_PT_URLS:
            fname = url.rsplit("/", 1)[-1]
            local = dest_dir / fname
            if not local.exists():
                _download(url, local)
            if local.suffix == ".zip":
                with zipfile.ZipFile(local, "r") as zf:
                    zf.extractall(dest_dir)
        done_marker.touch()
        return dest_dir

    # Default: single zip archive
    archive = dest_dir / f"{key}.zip"
    if not archive.exists():
        _download(info.url, archive)
    if info.sha256:
        actual = _sha256_file(archive)
        if actual != info.sha256:
            archive.unlink()
            raise RuntimeError(
                f"SHA-256 mismatch for {key}: expected {info.sha256}, got {actual}"
            )
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(dest_dir)
    done_marker.touch()
    return dest_dir


# ---------------------------------------------------------------------------
# Loaders  (one per dataset format)
# ---------------------------------------------------------------------------

def _tier_from_path(path: Path) -> str:
    """Infer quality tier from directory name conventions used by ESTER-Pt."""
    parts = {p.lower() for p in path.parts}
    if any(k in parts for k in ("clean", "limpo", "original")):
        return "clean"
    if any(k in parts for k in ("synthetic", "sintetico", "generated")):
        return "synthetic"
    return "degraded"


def load_bid(dataset_dir: Path) -> Iterator[Sample]:
    """
    Load BID dataset samples. Supports two layouts:

    1. BID Sample Dataset (SIBGRAPI 2020 — has OCR ground truth):
        dataset_dir/
          (BID Sample Dataset/)?
            CNH_Aberta/  CNH_Frente/  CNH_Verso/
            CPF_Frente/  CPF_Verso/
            RG_Aberto/   RG_Frente/   RG_Verso/
              <id>_in.jpg            ← input image
              <id>_gt_ocr.txt        ← CSV: x,y,w,h,transcription (ISO-8859-1)
              <id>_gt_segmentation.jpg

    2. Full BID Dataset (classification labels only):
        dataset_dir/
          CNH_FRENTE/ CNH_VERSO/ ...
          VIA_ANNOTATIONS/ (optional bbox annotations)

    Format is auto-detected from presence of ``*_gt_ocr.txt`` files.
    """
    root = dataset_dir
    nested = dataset_dir / "BID Sample Dataset"
    if nested.is_dir():
        root = nested

    if next(root.rglob("*_gt_ocr.txt"), None) is not None:
        yield from _load_bid_sample(root)
    else:
        yield from _load_bid_fullset(root)


def _parse_bid_sample_gt(gt_path: Path) -> str:
    """Extract joined transcription text from a BID Sample ``*_gt_ocr.txt`` CSV."""
    import csv
    lines: list[str] = []
    with gt_path.open(encoding="iso-8859-1", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header: x, y, width, height, transcription
        for row in reader:
            if len(row) >= 5 and row[4].strip():
                lines.append(row[4].strip())
    return "\n".join(lines)


def _load_bid_sample(root: Path) -> Iterator[Sample]:
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        doc_class = folder.name.upper()
        for img_path in sorted(folder.glob("*_in.jpg")):
            gt_path = img_path.with_name(img_path.stem.replace("_in", "_gt_ocr") + ".txt")
            if not gt_path.exists():
                continue
            try:
                ref_text = normalize(_parse_bid_sample_gt(gt_path))
            except Exception as exc:
                logger.debug("BID GT parse failed %s: %s", gt_path, exc)
                continue
            yield Sample(
                id=f"bid_{doc_class}_{img_path.stem}",
                image_path=img_path,
                reference_text=ref_text,
                quality_tier="degraded",
                doc_type="form",
                fields={"doc_class": doc_class},
                dataset="BID",
            )


def _load_bid_fullset(dataset_dir: Path) -> Iterator[Sample]:
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    via_path = dataset_dir / "VIA_ANNOTATIONS"
    for folder in sorted(dataset_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        doc_class = folder.name.upper()
        for img_path in sorted(folder.rglob("*")):
            if img_path.suffix.lower() not in image_exts:
                continue
            fields: dict[str, str] = {"doc_class": doc_class}
            via_json = via_path / f"{img_path.stem}.json" if via_path.exists() else None
            if via_json and via_json.exists():
                try:
                    fields.update(_parse_via_annotation(via_json))
                except Exception:
                    pass
            yield Sample(
                id=f"bid_{doc_class}_{img_path.stem}",
                image_path=img_path,
                reference_text="",
                quality_tier="degraded",
                doc_type="form",
                fields=fields,
                dataset="BID",
            )


def _parse_via_annotation(via_json: Path) -> dict[str, str]:
    """Parse a VIA (VGG Image Annotator) JSON file into field→value dict."""
    data = json.loads(via_json.read_text())
    fields: dict[str, str] = {}
    for region in data.get("regions", {}).values():
        attrs = region.get("region_attributes", {})
        for k, v in attrs.items():
            if v:
                fields[k.lower()] = str(v)
    return fields


def load_ester(dataset_dir: Path) -> Iterator[Sample]:
    """
    Load ESTER-Pt samples.

    Expected layout (see ICDAR 2023 paper — exact structure depends on
    downloaded archive; adapt if ESTER-Pt uses a different convention):
        dataset_dir/
          images/       *.png / *.jpg
          ground_truth/ *.txt  (same stem as image)

    Each .txt file contains the full-page transcription, one line per text line.
    Quality tier is inferred from subdirectory name.
    """
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    gt_root = dataset_dir / "ground_truth"
    img_root = dataset_dir / "images"

    if not img_root.exists():
        # Flatten: some archives put images at root
        img_root = dataset_dir

    for img_path in sorted(img_root.rglob("*")):
        if img_path.suffix.lower() not in image_exts:
            continue
        gt_file = (gt_root / img_path.relative_to(img_root)).with_suffix(".txt")
        if not gt_file.exists():
            gt_file = img_path.with_suffix(".txt")
        if not gt_file.exists():
            continue

        ref_text = normalize(gt_file.read_text(encoding="utf-8"))
        yield Sample(
            id=f"ester_{img_path.stem}",
            image_path=img_path,
            reference_text=ref_text,
            quality_tier=_tier_from_path(img_path),
            doc_type="free_text",
            dataset="ESTER",
        )


def load_xfund(dataset_dir: Path) -> Iterator[Sample]:
    """
    Load the XFUND Portuguese subset.

    XFUND release layout:
        pt.train.json  pt.val.json
        images/  *.jpg (named by document id)

    JSON schema per document:
      { "id": ..., "uid": ..., "form": [
          { "id": ..., "text": "...", "box": [...], "label": "header|question|answer|other",
            "linking": [[src_id, dst_id], ...], "words": [...] }
        ]
      }

    This loader yields one Sample per document image, with:
      - reference_text = all text blocks joined with newlines
      - fields         = {question_text: answer_text} for question→answer links
    """
    for json_file in sorted(dataset_dir.rglob("*.json")):
        split = "train" if "train" in json_file.name else "val"
        data = json.loads(json_file.read_text(encoding="utf-8"))
        documents = data.get("documents", data) if isinstance(data, dict) else data

        for doc in documents:
            doc_id = str(doc.get("id") or doc.get("uid", ""))

            # Image filename may be in doc["img"]["fname"] or just <uid>.jpg
            img_fname = doc.get("img", {}).get("fname") if isinstance(doc.get("img"), dict) else None
            if img_fname:
                img_path = dataset_dir / img_fname
            else:
                img_path = dataset_dir / f"{doc_id}.jpg"
            if not img_path.exists():
                candidates = list(dataset_dir.rglob(f"*{doc_id}*.jpg")) + \
                             list(dataset_dir.rglob(f"*{doc_id}*.png"))
                if not candidates:
                    continue
                img_path = candidates[0]

            # XFUND uses "document" key (not "form")
            form_items: list[dict] = doc.get("document", doc.get("form", []))
            all_text = "\n".join(
                item["text"] for item in form_items if item.get("text")
            )
            # Build KV pairs from question→answer linking
            id_to_item = {item["id"]: item for item in form_items}
            fields: dict[str, str] = {}
            for item in form_items:
                if item.get("label") == "question":
                    for link in item.get("linking", []):
                        answer_id = link[1] if link[0] == item["id"] else link[0]
                        answer_item = id_to_item.get(answer_id)
                        if answer_item and answer_item.get("label") == "answer":
                            q_key = re.sub(r"\W+", "_", item["text"].lower()).strip("_")
                            fields[q_key] = answer_item.get("text", "")

            yield Sample(
                id=f"xfund_{split}_{doc_id}",
                image_path=img_path,
                reference_text=normalize(all_text),
                quality_tier="degraded",    # XFUND = real-world scanned forms
                doc_type="form",
                fields=fields,
                dataset="XFUND",
            )


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

_LOADERS = {
    "bid": load_bid,
    "ester": load_ester,
    "xfund": load_xfund,
}


def load_dataset(key: str, dataset_dir: Path) -> Iterator[Sample]:
    """
    Load samples from a dataset directory.
    `key` must be one of: bid, ester, xfund.
    """
    loader_key = key.split("_")[0]   # "bid_sample" → "bid"
    loader = _LOADERS.get(loader_key)
    if loader is None:
        raise ValueError(f"Unknown dataset key: {key!r}. Available: {list(_LOADERS)}")
    yield from loader(dataset_dir)
