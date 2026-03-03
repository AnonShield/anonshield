#!/usr/bin/env python3
"""
convert_d1_to_d1c.py — Convert D1 (OpenVAS native formats) → D1C (converted formats)

Converts all four formats in D1_openvas/ to produce the D1C_converted/ dataset:
  • CSV  → XLSX  (via pandas + openpyxl)
  • TXT  → DOCX  (via python-docx)
  • XML  → JSON  (via xml.etree.ElementTree, @attributes convention)
  • PDF  → PDF-images  (via PyMuPDF: rasterise each page at 150 DPI → reassemble as PDF)

Output structure mirrors the original D1C_converted/:
  <output>/xlsx/<target>/<target>.xlsx
  <output>/docx/<target>/<target>.docx
  <output>/json/<target>/<target>_xml.json
  <output>/pdf_images/<target>/<target>_images.pdf

Usage (from workspace root, with .venv_benchmark activated):
  python3 paper_data/scripts/convert_d1_to_d1c.py \\
      --source  paper_data/datasets/D1_openvas \\
      --output  paper_data/datasets/D1C_converted \\
      --workers 4

Run python3 convert_d1_to_d1c.py --help for full options.
"""

import argparse
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Dependency check ──────────────────────────────────────────────────────────

def check_dependencies() -> bool:
    missing = []
    try:
        import fitz  # noqa: F401
    except ImportError:
        missing.append("PyMuPDF   → pip install PyMuPDF")
    try:
        import pandas  # noqa: F401
    except ImportError:
        missing.append("pandas    → pip install pandas")
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        missing.append("openpyxl  → pip install openpyxl")
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx → pip install python-docx")

    if missing:
        log.error("Missing required packages:")
        for m in missing:
            log.error("  %s", m)
        log.error("Activate .venv_benchmark: source .venv_benchmark/bin/activate")
        return False
    return True


# ── XML → JSON (recursive, @attributes convention) ───────────────────────────

def _elem_to_dict(elem: ET.Element):
    """Recursively convert an ElementTree Element to a Python dict.

    Convention (matching the original D1C dataset):
      - XML attributes  → stored under the "@attributes" key
      - XML text/tail   → stored under "text" (if non-whitespace)
      - Child elements  → stored by tag name; repeated tags become a list
    """
    d = {}
    if elem.attrib:
        d["@attributes"] = dict(elem.attrib)

    text = (elem.text or "").strip()
    if text:
        d["text"] = text

    for child in elem:
        child_dict = _elem_to_dict(child)
        tag = child.tag
        # Remove namespace prefix if present: {ns}tag → tag
        if tag.startswith("{"):
            tag = tag.split("}", 1)[1]
        if tag in d:
            existing = d[tag]
            if not isinstance(existing, list):
                d[tag] = [existing]
            d[tag].append(child_dict)
        else:
            d[tag] = child_dict

    return d


def convert_xml_to_json(src: Path, dst: Path) -> None:
    tree = ET.parse(src)
    root = tree.getroot()
    tag = root.tag
    if tag.startswith("{"):
        tag = tag.split("}", 1)[1]
    data = _elem_to_dict(root)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── CSV → XLSX ────────────────────────────────────────────────────────────────

def convert_csv_to_xlsx(src: Path, dst: Path) -> None:
    import pandas as pd
    dst.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    df.to_excel(dst, index=False, engine="openpyxl")


# ── TXT → DOCX ───────────────────────────────────────────────────────────────

def convert_txt_to_docx(src: Path, dst: Path) -> None:
    from docx import Document
    dst.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    text = src.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(dst)


# ── PDF (text) → PDF (images) ────────────────────────────────────────────────

def convert_pdf_to_images_pdf(src: Path, dst: Path, dpi: int = 150) -> None:
    """Rasterise every page of a text PDF at `dpi`, then bundle them back as a PDF.

    150 DPI matches the original D1C dataset. Use 200+ for better OCR quality
    at the cost of larger output files (~4× the text PDF size per 50 DPI increase).
    """
    import fitz  # PyMuPDF

    dst.parent.mkdir(parents=True, exist_ok=True)
    src_doc = fitz.open(str(src))
    out_doc = fitz.open()

    zoom = dpi / 72.0  # PyMuPDF internal resolution is 72 DPI
    mat = fitz.Matrix(zoom, zoom)

    for page in src_doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        # Create a new blank PDF page sized to match the rasterised image
        img_page = out_doc.new_page(width=pix.width, height=pix.height)
        # Insert the pixmap as a full-page image (no text layer — OCR-only)
        img_page.insert_image(
            fitz.Rect(0, 0, pix.width, pix.height),
            pixmap=pix,
        )

    out_doc.save(str(dst), deflate=True)
    out_doc.close()
    src_doc.close()


# ── Per-target conversion ─────────────────────────────────────────────────────

CONVERTERS = {
    ".csv": (convert_csv_to_xlsx,  "xlsx",       lambda s: s.stem + ".xlsx"),
    ".txt": (convert_txt_to_docx,  "docx",       lambda s: s.stem + ".docx"),
    ".xml": (convert_xml_to_json,  "json",       lambda s: s.stem + "_xml.json"),
    ".pdf": (convert_pdf_to_images_pdf, "pdf_images", lambda s: s.stem + "_images.pdf"),
}


def convert_target(target_dir: Path, output_root: Path, force: bool, dpi: int) -> list[str]:
    """Convert all files in one D1 target directory.  Returns list of error strings."""
    errors = []
    target_name = target_dir.name

    for src_file in sorted(target_dir.iterdir()):
        ext = src_file.suffix.lower()
        if ext not in CONVERTERS:
            continue

        fn, fmt_dir, dst_name_fn = CONVERTERS[ext]
        dst = output_root / fmt_dir / target_name / dst_name_fn(src_file)

        if dst.exists() and not force:
            continue  # already converted, skip

        try:
            if ext == ".pdf":
                fn(src_file, dst, dpi=dpi)
            else:
                fn(src_file, dst)
        except Exception as exc:
            errors.append(f"{src_file.name}: {exc}")

    return errors


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--source", "-s",
        default="paper_data/datasets/D1_openvas",
        help="Path to D1_openvas directory (default: paper_data/datasets/D1_openvas)",
    )
    p.add_argument(
        "--output", "-o",
        default="paper_data/datasets/D1C_converted",
        help="Output directory for D1C_converted (default: paper_data/datasets/D1C_converted)",
    )
    p.add_argument(
        "--workers", "-w",
        type=int,
        default=2,
        help="Parallel worker threads (default: 2; PDF conversion is CPU-bound)",
    )
    p.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for PDF page rasterisation (default: 150; use 200+ for higher quality)",
    )
    p.add_argument(
        "--formats",
        nargs="+",
        choices=["xlsx", "docx", "json", "pdf_images"],
        default=["xlsx", "docx", "json", "pdf_images"],
        help="Which formats to generate (default: all four)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-convert even if output file already exists",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be converted without doing it",
    )
    p.add_argument(
        "--cpu-only",
        action="store_true",
        help="No-op flag (accepted for compatibility with benchmark pipeline scripts)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if not check_dependencies():
        sys.exit(1)

    source = Path(args.source)
    output = Path(args.output)

    if not source.is_dir():
        log.error("Source directory not found: %s", source)
        sys.exit(1)

    # Collect target directories
    target_dirs = sorted(
        d for d in source.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    if not target_dirs:
        log.error("No target directories found in %s", source)
        sys.exit(1)

    # Restrict converters to requested formats
    active_exts = {
        ext for ext, (_, fmt, _) in CONVERTERS.items()
        if fmt in args.formats
    }

    total_files = sum(
        1 for td in target_dirs
        for f in td.iterdir()
        if f.suffix.lower() in active_exts
    )

    log.info("=" * 72)
    log.info("DATASET CONVERSION STARTED")
    log.info("=" * 72)
    log.info("Source   : %s", source)
    log.info("Output   : %s", output)
    log.info("Formats  : %s", ", ".join(args.formats))
    log.info("Workers  : %d", args.workers)
    log.info("DPI      : %d (PDF rasterisation)", args.dpi)
    log.info("Force    : %s", args.force)
    log.info("Dry-run  : %s", args.dry_run)
    log.info("Targets  : %d  |  Expected conversions: %d", len(target_dirs), total_files)
    log.info("")

    if args.dry_run:
        for td in target_dirs:
            for src_file in sorted(td.iterdir()):
                ext = src_file.suffix.lower()
                if ext not in active_exts:
                    continue
                _, fmt_dir, dst_name_fn = CONVERTERS[ext]
                dst = output / fmt_dir / td.name / dst_name_fn(src_file)
                log.info("  [DRY] %s → %s", src_file.relative_to(source), dst.relative_to(output))
        return

    start = time.time()
    done = 0
    errors = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(convert_target, td, output, args.force, args.dpi): td
            for td in target_dirs
        }
        for fut in as_completed(futures):
            td = futures[fut]
            errs = fut.result()
            done += 1
            if errs:
                for e in errs:
                    errors.append(f"{td.name}/{e}")
                log.warning("[%d/%d] %-40s — %d error(s)", done, len(target_dirs), td.name, len(errs))
            else:
                log.info("[%d/%d] Completed: %s", done, len(target_dirs), td.name)

    elapsed = time.time() - start
    log.info("")
    log.info("=" * 72)
    log.info("DONE — %d targets processed in %.1f s", len(target_dirs), elapsed)
    if errors:
        log.warning("%d error(s):", len(errors))
        for e in errors:
            log.warning("  %s", e)
        sys.exit(1)
    else:
        log.info("All conversions completed successfully.")


if __name__ == "__main__":
    main()
