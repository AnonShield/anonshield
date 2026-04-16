#!/usr/bin/env python3
"""
AnonShield OCR Benchmark — CLI entry point.

Usage:
    python -m benchmark.ocr [OPTIONS]

Examples:
    # Full benchmark with all available engines on XFUND-PT (smallest download)
    python -m benchmark.ocr --datasets xfund --engines tesseract,easyocr,surya

    # Download BID + ESTER and run all registered engines
    python -m benchmark.ocr --datasets bid,ester --engines all

    # Run with deskew+CLAHE preprocessing
    python -m benchmark.ocr --datasets xfund --engines tesseract --preprocess deskew,clahe

    # Report only from existing results (no new inference)
    python -m benchmark.ocr --report-only

    # List available engines and datasets
    python -m benchmark.ocr --list
"""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ocr_benchmark")


# ---------------------------------------------------------------------------
# Preprocessing factory
# ---------------------------------------------------------------------------

def _build_preprocess(steps: list[str]):
    """Build a preprocessing callable from a list of step names."""
    if not steps:
        return None

    def _preprocess(image_bytes: bytes) -> bytes:
        sys.path.insert(0, str(ROOT))
        from src.anon.ocr.preprocessor import apply
        return apply(image_bytes, steps)

    _preprocess.__name__ = "+".join(steps)
    return _preprocess


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m benchmark.ocr",
        description="AnonShield OCR Engine Benchmark",
    )
    p.add_argument(
        "--datasets", default="xfund",
        help="Comma-separated dataset keys: bid, ester, xfund. Default: xfund",
    )
    p.add_argument(
        "--engines", default="tesseract",
        help=(
            "Comma-separated engine names, or 'all' for every registered engine. "
            "Default: tesseract"
        ),
    )
    p.add_argument(
        "--preprocess", default="",
        help=(
            "Comma-separated preprocessing steps applied before OCR. "
            "Options: grayscale,upscale,clahe,denoise,deskew,binarize,morph_open,border. "
            "Default: none"
        ),
    )
    p.add_argument(
        "--data-dir", type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="Directory where dataset archives are downloaded. Default: benchmark/ocr/data/",
    )
    p.add_argument(
        "--out-dir", type=Path,
        default=Path(__file__).resolve().parent / "results",
        help="Output directory for results, CSV, JSON, and state. Default: benchmark/ocr/results/",
    )
    p.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for bootstrap CI. Default: 42",
    )
    p.add_argument(
        "--anls-threshold", type=float, default=0.5,
        help="ANLS threshold τ (DocVQA standard = 0.5). Default: 0.5",
    )
    p.add_argument(
        "--report-only", action="store_true",
        help="Skip inference; generate report from existing run_state.json",
    )
    p.add_argument(
        "--list", action="store_true",
        help="Print available engines and datasets, then exit",
    )
    p.add_argument(
        "--max-samples", type=int, default=0,
        help="Limit samples per dataset (0 = no limit). Useful for smoke tests.",
    )
    p.add_argument(
        "--store-texts", action="store_true",
        help="Persist normalized ref/hyp texts (enables T5 error analysis).",
    )
    return p.parse_args()


def _list_available() -> None:
    from benchmark.ocr.datasets import _DATASETS
    from src.anon.ocr.factory import AVAILABLE_ENGINES
    print("\nAvailable datasets:")
    for key, info in _DATASETS.items():
        print(f"  {key:<20} {info.license:<25} {info.expected_size_mb:.0f} MB")
    print("\nAvailable OCR engines:")
    for e in AVAILABLE_ENGINES:
        print(f"  {e}")


def main() -> None:
    args = _parse_args()

    if args.list:
        _list_available()
        return

    from benchmark.ocr.datasets import _DATASETS, download_dataset, load_dataset
    from benchmark.ocr.runner import run_benchmark, RunState
    from benchmark.ocr.report import print_full_report

    # --- Engine selection ---------------------------------------------------
    from src.anon.ocr.factory import AVAILABLE_ENGINES
    if args.engines.strip().lower() == "all":
        engine_names = AVAILABLE_ENGINES
    else:
        engine_names = [e.strip() for e in args.engines.split(",") if e.strip()]

    # --- Dataset selection and download ------------------------------------
    # Resolve short aliases: "xfund" → "xfund_pt", "bid" → "bid_sample", etc.
    _aliases = {k.split("_")[0]: k for k in _DATASETS}
    raw_keys = [d.strip() for d in args.datasets.split(",") if d.strip()]
    dataset_keys = [_aliases.get(k, k) for k in raw_keys]

    samples = []
    if not args.report_only:
        for key in dataset_keys:
            if key not in _DATASETS:
                logger.error("Unknown dataset: %r. Use --list to see options.", key)
                sys.exit(1)
            logger.info("Downloading dataset: %s", key)
            try:
                dataset_dir = download_dataset(key, args.data_dir)
            except RuntimeError as exc:
                logger.error("Download failed: %s", exc)
                sys.exit(1)

            logger.info("Loading samples from %s…", dataset_dir)
            loaded = list(load_dataset(key, dataset_dir))
            if args.max_samples:
                loaded = loaded[: args.max_samples]
            logger.info("  %d samples loaded", len(loaded))
            samples.extend(loaded)

        if not samples:
            logger.error("No samples loaded. Check dataset directories.")
            sys.exit(1)

        # --- Preprocessing ------------------------------------------------
        steps = [s.strip() for s in args.preprocess.split(",") if s.strip()]
        preprocess_fn = _build_preprocess(steps)

        # --- Run inference ------------------------------------------------
        aggregates = run_benchmark(
            engine_names=engine_names,
            samples=samples,
            output_dir=args.out_dir,
            preprocess=preprocess_fn,
            seed=args.seed,
            anls_threshold=args.anls_threshold,
            store_texts=args.store_texts,
        )
    else:
        # Report-only: load from existing state
        state_path = args.out_dir / "run_state.json"
        if not state_path.exists():
            logger.error("No run_state.json found at %s. Run inference first.", args.out_dir)
            sys.exit(1)
        state = RunState(state_path)
        from benchmark.ocr.runner import _aggregate
        aggregates = _aggregate(state.results, seed=args.seed)

    # --- Report -------------------------------------------------------------
    state_path = args.out_dir / "run_state.json"
    raw_results: list[dict] = []
    if state_path.exists():
        import json
        raw_results = json.loads(state_path.read_text()).get("results", [])

    print_full_report(aggregates, raw_results, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
