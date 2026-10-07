import json
import csv
import io
import re
import logging
from typing import List, Dict, Any, Optional, Union, Iterable

import ijson

logger = logging.getLogger(__name__)

def flatten_keys(obj: Any, prefix: str = "", depth: int = 0, max_depth: int = 2) -> List[str]:
    """Recursively flattens object keys into dot-notation paths."""
    if depth > max_depth:
        return [prefix] if prefix else []
    
    if isinstance(obj, dict):
        out = []
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and depth < max_depth - 1:
                out.extend(flatten_keys(v, path, depth + 1, max_depth))
            else:
                out.append(path)
        return out
    return [prefix] if prefix else []

def _object_keys(stream, max_bytes: int = 64 * 1024 * 1024) -> List[str]:
    """Field paths of a top-level JSON object, as flatten_keys names them,
    streamed so that a large array inside it is never loaded."""
    order: List[str] = []
    children: Dict[str, List[str]] = {}
    for prefix, event, value in ijson.parse(stream):
        if event == "map_key":
            if prefix == "":
                order.append(value)
            elif prefix in order and "." not in prefix:
                children.setdefault(prefix, []).append(f"{prefix}.{value}")
        elif event == "end_map" and prefix == "":
            break
        if stream.tell() > max_bytes:
            break
    return [path for key in order for path in children.get(key, [key])]


def detect_fields_from_stream(stream: io.IOBase, ext: str, max_bytes: int = 256 * 1024) -> List[str]:
    """
    Robustly detects fields/columns from a file stream.
    Supports CSV, TSV, JSON, JSONL.
    """
    ext = ext.lower().lstrip(".")

    # Records are read whole, however long or pretty-printed: the first element
    # of a top-level array, the top-level object, or the first JSONL line.
    if ext == "json":
        head = stream.read(64)
        stream.seek(0)
        start = head.lstrip(b"\xef\xbb\xbf \t\r\n")[:1]
        try:
            if start == b"[":
                first = next(ijson.items(stream, "item"), None)
                if isinstance(first, dict):
                    return flatten_keys(first)
            elif start == b"{":
                return _object_keys(stream)
        except Exception:
            pass
        stream.seek(0)
    elif ext in ("jsonl", "ndjson"):
        for line in iter(lambda: stream.readline(64 * 1024 * 1024), b""):
            if line.strip():
                try:
                    first = json.loads(line)
                except ValueError:
                    break
                if isinstance(first, dict):
                    return flatten_keys(first)
                break
        stream.seek(0)

    # Read a sample chunk for analysis
    chunk_bytes = stream.read(max_bytes)
    if not chunk_bytes:
        return []
    
    # Try decoding
    try:
        text = chunk_bytes.decode("utf-8", errors="replace").strip()
    except Exception:
        return []

    if ext in ("csv", "tsv"):
        sep = "\t" if ext == "tsv" else ","
        try:
            # Use io.StringIO to make it compatible with csv.DictReader
            reader = csv.DictReader(io.StringIO(text), delimiter=sep)
            cols = reader.fieldnames or []
            return [c.strip() for c in cols if c.strip()]
        except Exception:
            return []

    if ext in ("json", "jsonl", "ndjson"):
        # 1. Try parsing as a full JSON first (if it's a valid small JSON)
        try:
            data = json.loads(text)
            if isinstance(data, list) and len(data) > 0:
                return flatten_keys(data[0])
            elif isinstance(data, dict):
                return flatten_keys(data)
        except json.JSONDecodeError:
            pass

        # 2. If it's not a full JSON, it might be JSONL or a truncated JSON
        # Let's try to find the first complete object {}
        # Simple heuristic: find first '{' and corresponding '}' or end of first line
        try:
            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # If it's a pretty-printed JSON, the first line might just be '[' or '{'
                # We try to accumulate lines until we get a valid object
                if line in ("[", "{"):
                    continue
                
                try:
                    # Try to parse line (JSONL case)
                    obj = json.loads(line.rstrip(","))
                    if isinstance(obj, dict):
                        return flatten_keys(obj)
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        # 3. Last resort: regex for top-level keys if it looks like a dict
        # This is for truncated large JSONs starting with {
        if text.startswith("{"):
            keys = re.findall(r'"([^"]+)"\s*:', text[:10000])
            if keys:
                # Deduplicate and return
                seen = set()
                return [k for k in keys if not (k in seen or seen.add(k))]

    return []
