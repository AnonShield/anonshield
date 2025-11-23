"""
File Processors for the Anonymization Tool

This module uses a Template Method Pattern. The `FileProcessor` base class defines
the main workflow for processing files, and subclasses implement the specific
details for extracting text from different file formats (e.g., PDF, DOCX, JSON).
"""

import gc
import io
import os
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, List, Generator, Optional, Dict, Tuple, Union, Optional

import numpy as np  # type: ignore
import openpyxl  # type: ignore
import orjson  # type: ignore
import pandas as pd  # type: ignore
import pytesseract  # type: ignore
from docx import Document  # type: ignore
from lxml import etree  # type: ignore
from PIL import Image  # type: ignore
from tqdm import tqdm  # type: ignore
import pymupdf as fitz  # type: ignore

from .config import bulk_save_to_db, TECHNICAL_STOPLIST
from .engine import AnonymizationOrchestrator


def get_output_path(original_path: str, new_ext: str, prefix: str = "anon_", output_dir: str = "output") -> str:
    """Constructs the output file path in the specified output directory."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    return os.path.join(output_dir, f"{prefix}{base_name}{new_ext}")

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from image bytes using OCR."""
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception:
        return ""


class FileProcessor(ABC):
    DEFAULT_BATCH_SIZE = 200

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: Optional[Dict] = None, min_word_length: int = 3, skip_numeric: bool = False, output_dir: str = "output", overwrite: bool = False):
        self.file_path = file_path
        self.orchestrator = orchestrator
        self.ner_data_generation = ner_data_generation
        self.anonymization_config = anonymization_config or {}
        self.min_word_length = min_word_length
        self.skip_numeric = skip_numeric
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.db_executor = ThreadPoolExecutor(max_workers=1)
        self.ner_output_file: Optional[str] = None
        if self.ner_data_generation:
            self.ner_output_file = self._get_ner_output_path()
            os.makedirs(os.path.dirname(self.ner_output_file), exist_ok=True)
            self.ner_file_handle = open(self.ner_output_file, "w", encoding="utf-8")

    def _get_ner_output_path(self) -> str:
        return get_output_path(self.file_path, ".jsonl", prefix="ner_data_anon_", output_dir=self.output_dir)

    def _setup_optimization(self):
        gc.disable()

    def _cleanup_optimization(self):
        gc.collect()
        gc.enable()
        self.db_executor.shutdown(wait=True)
        if hasattr(self, 'ner_file_handle') and self.ner_file_handle:
            self.ner_file_handle.close()

    def _batch_iterator(self, iterator: Iterable[str], size: int) -> Generator[List[str], None, None]:
        batch = []
        for item in iterator:
            batch.append(item)
            if len(batch) >= size:
                yield batch
                batch = []
        if batch:
            yield batch

    def process(self) -> str:
        self._setup_optimization()
        output_path: str = ""
        try:
            if self.ner_data_generation:
                output_path = self.ner_output_file or self._get_ner_output_path()
                if os.path.exists(output_path) and not self.overwrite:
                    print(f"[!] Output file '{output_path}' already exists. Use --overwrite to replace it.", file=sys.stderr)
                    return output_path
                all_texts = self._extract_all_texts()
                self._run_ner_pipeline(all_texts)
            else:
                output_path = get_output_path(self.file_path, self._get_output_extension(), output_dir=self.output_dir)
                if os.path.exists(output_path) and not self.overwrite:
                    print(f"[!] Output file '{output_path}' already exists. Use --overwrite to replace it.", file=sys.stderr)
                    return output_path
                self._process_anonymization(output_path)
        finally:
            self._cleanup_optimization()
        return output_path

    def _process_anonymization(self, output_path: str):
        with open(output_path, "w", encoding="utf-8") as outfile:
            text_iterator = self._extract_texts()
            for text_batch in self._batch_iterator(text_iterator, self.DEFAULT_BATCH_SIZE):
                should_anonymize, forced_type = self._should_anonymize(text_batch[0])
                if should_anonymize:
                    anonymized_batch = self._process_batch_smart(text_batch, forced_entity_type=forced_type)
                    outfile.write("".join(anonymized_batch))
                else:
                    outfile.write("".join(text_batch))


    @abstractmethod
    def _extract_texts(self) -> Iterable[str]:
        raise NotImplementedError

    def _extract_all_texts(self) -> List[str]:
        return list(self._extract_texts())

    @abstractmethod
    def _get_output_extension(self) -> str:
        raise NotImplementedError

    def _should_anonymize(self, text: str, path: str = "") -> Tuple[bool, Optional[Union[str, List[str]]]]:
        if not isinstance(text, str) or len(text.strip()) < self.min_word_length:
            return False, None

        stripped_text = text.strip()
        if self.skip_numeric and stripped_text.isnumeric():
            return False, None
            
        text_lower = stripped_text.lower()
        if text_lower in TECHNICAL_STOPLIST:
            return False, None

        current_path = path.lstrip('.')
        
        # Rule 1: Exclusion takes highest precedence.
        exclude_rules = self.anonymization_config.get('fields_to_exclude', [])
        for rule in exclude_rules:
            # If the rule is "output", match "output" or "output.something", but not "output_something"
            if current_path == rule or current_path.startswith(f"{rule}."):
                return False, None

        # Rule 2: Forced anonymization with a specific entity type.
        force_anonymize_rules = self.anonymization_config.get('force_anonymize', None)
        if force_anonymize_rules and current_path in force_anonymize_rules:
            entity_type = force_anonymize_rules[current_path].get("entity_type")
            return True, entity_type

        # Rule 3: Standard anonymization (auto-detection).
        fields_to_anonymize = self.anonymization_config.get('fields_to_anonymize', None)
        if fields_to_anonymize is not None and current_path in fields_to_anonymize:
            return True, None

        # Rule 4: Default behavior. If either 'force_anonymize' or 'fields_to_anonymize'
        # are defined in the config, then we are in "explicit" mode, and any field not
        # matching a rule by this point should be ignored.
        if force_anonymize_rules is not None or fields_to_anonymize is not None:
            return False, None
        
        # If no anonymization rule keys are in the config, default to anonymizing everything.
        return True, None

    def _process_batch_smart(self, text_list: List[str], forced_entity_type: Optional[Union[str, List[str]]] = None) -> List[str]:
        if not text_list:
            return []
        
        entity_collector: List = []
        anonymized_values = self.orchestrator.anonymize_texts(
            text_list,
            operator_params={"entity_collector": entity_collector},
            forced_entity_type=forced_entity_type
        )

        if entity_collector:
            self.db_executor.submit(bulk_save_to_db, list(entity_collector))

        if len(anonymized_values) != len(text_list):
            print(f"[!] Warning: Mismatch in batch processing for {self.file_path}. Skipping update for this batch.", file=sys.stderr)
            return text_list

        return anonymized_values

    def _run_ner_pipeline(self, text_list: List[str]):
        if not text_list: return

        MAX_CHUNK_SIZE = 1500 
        DELIMITER = " . ||| . "
        
        text_chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0
        
        for s in text_list:
            should, _ = self._should_anonymize(s)
            if not should: continue
            s = s.strip()
            if not s: continue

            if current_len + len(s) + len(DELIMITER) > MAX_CHUNK_SIZE and current_chunk:
                text_chunks.append(DELIMITER.join(current_chunk))
                current_chunk, current_len = [], 0
            
            current_chunk.append(s)
            current_len += len(s) + len(DELIMITER)
        
        if current_chunk:
            text_chunks.append(DELIMITER.join(current_chunk))

        if not text_chunks: return
        
        desc = f"Detecting Entities for {os.path.basename(self.file_path)}"
        for chunk in tqdm(text_chunks, desc=desc, leave=False):
            ner_records = self.orchestrator.detect_entities([chunk])
            for record in ner_records:
                self.ner_file_handle.write(orjson.dumps(record).decode('utf-8') + "\n")


class TextFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".txt"

    def _extract_texts(self) -> Iterable[str]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                yield line


class ImageFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".txt"

    def _extract_texts(self) -> Iterable[str]:
        with open(self.file_path, "rb") as f:
            image_bytes = f.read()
        extracted_text = extract_text_from_image(image_bytes)
        if extracted_text:
            yield extracted_text


class DocxFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".txt"

    def _extract_texts(self) -> Iterable[str]:
        doc = Document(self.file_path)
        for para in doc.paragraphs:
            para_content_parts = []
            for run in para.runs:
                if run._r.xpath(".//w:drawing"):
                    for r_id in run._r.xpath(".//@r:embed"):
                        try:
                            image_part = doc.part.related_parts[r_id]
                            ocr_text = extract_text_from_image(image_part.blob)
                            if ocr_text: para_content_parts.append(ocr_text)
                        except (KeyError, AttributeError):
                            continue
                else:
                    para_content_parts.append(run.text)
            full_para_text = "".join(para_content_parts)
            if full_para_text.strip():
                yield full_para_text + "\n"


class PdfFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".txt"

    def _extract_texts(self) -> Iterable[str]:
        with fitz.open(self.file_path) as doc:
            for page in doc:
                content_items = []
                text_blocks = page.get_text("dict").get("blocks", [])
                for block in text_blocks:
                    if block["type"] == 0:
                        block_text = "".join(span["text"] for line in block.get("lines", []) for span in line.get("spans", []) if "text" in span)
                        if block_text.strip():
                            content_items.append({"bbox": block["bbox"], "content": block_text})

                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        bbox = page.get_image_bbox(img)
                        content_items.append({"bbox": bbox, "content": extract_text_from_image(base_image["image"])})

                content_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
                
                for item in content_items:
                    if item['content']:
                        yield item['content'] + "\n"


class CsvFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".csv"
    
    def _process_anonymization(self, output_path: str):
        chunk_size = 50
        header_written = False
        
        try:
            with open(self.file_path, "rb") as f:
                total_rows = sum(1 for _ in f) -1
        except (IOError, FileNotFoundError):
            total_rows = 0
        
        if total_rows <= 0: return

        with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='skip', engine='c', lineterminator='\n') as reader:
            progress_bar = tqdm(total=total_rows, desc=f"Processing CSV {os.path.basename(self.file_path)}", unit="rows", leave=False)
            for chunk in reader:
                anonymized_chunk = chunk.copy()
                for col in chunk.columns:
                    texts_by_type: Dict[Union[str, Tuple[str, ...]], List[str]] = defaultdict(list)
                    
                    for val in chunk[col].dropna():
                        val_str = str(val)
                        should_anon, forced_type = self._should_anonymize(val_str, col)
                        if should_anon:
                            if isinstance(forced_type, list):
                                group_key = tuple(forced_type)
                            else:
                                group_key = forced_type if forced_type is not None else "auto"
                            texts_by_type[group_key].append(val_str)
                    
                    if not texts_by_type:
                        continue

                    translation_map = {}
                    for group_key, texts in texts_by_type.items():
                        unique_texts = list(set(texts))
                        
                        current_forced_type = group_key if group_key != "auto" else None
                        if isinstance(current_forced_type, tuple):
                            current_forced_type = list(current_forced_type)

                        anonymized_texts = self._process_batch_smart(unique_texts, forced_entity_type=current_forced_type)
                        translation_map.update(dict(zip(unique_texts, anonymized_texts)))

                    if translation_map:
                        anonymized_chunk[col] = anonymized_chunk[col].replace(translation_map)

                anonymized_chunk.to_csv(output_path, mode='a', index=False, header=not header_written)
                header_written = True
                progress_bar.update(len(chunk))
            progress_bar.close()

    def _extract_texts(self) -> Iterable[str]:
        with pd.read_csv(self.file_path, dtype=str, chunksize=50, on_bad_lines='skip', engine='c') as reader:
            for chunk in reader:
                for col in chunk.columns:
                    for val in chunk[col]:
                        should_anon, _ = self._should_anonymize(str(val), col)
                        if should_anon:
                            yield str(val)


class XlsxFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".xlsx"

    def _extract_texts(self) -> Iterable[str]:
        wb = openpyxl.load_workbook(self.file_path, read_only=True)
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        path = f"{sheet.title}.{cell.column_letter}"
                        should_anon, _ = self._should_anonymize(cell.value, path)
                        if should_anon:
                            yield cell.value
    
    def _process_anonymization(self, output_path: str):
        wb = openpyxl.load_workbook(self.file_path)
        
        all_texts_map: Dict[Union[str, Tuple[str, ...]], List[str]] = defaultdict(list)
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        path = f"{sheet.title}.{cell.column_letter}"
                        should_anon, forced_type = self._should_anonymize(cell.value, path)
                        if should_anon:
                            if isinstance(forced_type, list):
                                group_key = tuple(forced_type)
                            else:
                                group_key = forced_type if forced_type is not None else "auto"
                            all_texts_map[group_key].append(cell.value)
        
        translation_map = {}
        for group_key, texts in all_texts_map.items():
            forced_type = group_key if group_key != "auto" else None
            if isinstance(forced_type, tuple):
                forced_type = list(forced_type)
            
            unique_texts = list(set(texts))
            anonymized_texts = self._process_batch_smart(unique_texts, forced_entity_type=forced_type)
            translation_map.update(dict(zip(unique_texts, anonymized_texts)))

        if not translation_map:
            wb.save(output_path)
            return

        # Reconstruct workbook
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value in translation_map:
                        cell.value = translation_map[cell.value]
        
        wb.save(output_path)


class XmlFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".xml"

    def _get_xpath(self, elem) -> str:
        return "/".join(e.tag for e in elem.iterancestors()) + "/" + elem.tag

    def _extract_texts(self) -> Iterable[str]:
        for _, element in etree.iterparse(self.file_path, events=('end',), recover=True, strip_cdata=False):
            path = self._get_xpath(element)
            if element.text and element.text.strip():
                should_anon, _ = self._should_anonymize(element.text, path)
                if should_anon:
                    yield element.text
            if element.tail and element.tail.strip():
                should_anon, _ = self._should_anonymize(element.tail, path + "/tail()")
                if should_anon:
                    yield element.tail
            
            for key, value in element.attrib.items():
                attr_path = f"{path}[@{key}]"
                should_anon, _ = self._should_anonymize(value, attr_path)
                if should_anon:
                    yield value
            element.clear()

    def _process_anonymization(self, output_path: str):
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        tree = etree.parse(self.file_path, parser)
        
        text_groups: Dict[Union[str, Tuple[str, ...]], List[str]] = defaultdict(list)
        for element in tree.iter():
            path = self._get_xpath(element)
            if element.text and element.text.strip():
                should_anon, forced_type = self._should_anonymize(element.text, path)
                if should_anon:
                    group_key = tuple(forced_type) if isinstance(forced_type, list) else (forced_type if forced_type is not None else "auto")
                    text_groups[group_key].append(element.text)

            if element.tail and element.tail.strip():
                should_anon, forced_type = self._should_anonymize(element.tail, path + "/tail()")
                if should_anon:
                    group_key = tuple(forced_type) if isinstance(forced_type, list) else (forced_type if forced_type is not None else "auto")
                    text_groups[group_key].append(element.tail)
            
            for key, value in element.attrib.items():
                attr_path = f"{path}[@{key}]"
                should_anon, forced_type = self._should_anonymize(value, attr_path)
                if should_anon:
                    group_key = tuple(forced_type) if isinstance(forced_type, list) else (forced_type if forced_type is not None else "auto")
                    text_groups[group_key].append(value)

        translation_map = {}
        for group_key, texts in text_groups.items():
            forced_type = group_key if group_key != "auto" else None
            if isinstance(forced_type, tuple):
                forced_type = list(forced_type)

            unique_texts = list(set(texts))
            anonymized_texts = self._process_batch_smart(unique_texts, forced_entity_type=forced_type)
            translation_map.update(dict(zip(unique_texts, anonymized_texts)))

        if not translation_map:
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            return

        for element in tree.iter():
            if element.text in translation_map:
                element.text = translation_map[element.text]
            if element.tail in translation_map:
                element.tail = translation_map[element.tail]
            
            for key, value in element.attrib.items():
                if value in translation_map:
                    element.set(key, translation_map[value])

        tree.write(output_path, encoding="utf-8", xml_declaration=True)


class JsonFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".json" if not self.file_path.endswith(".jsonl") else ".jsonl"

    def _process_json_recursive(self, obj, path_prefix: str = ""):
        current_path = path_prefix.lstrip('.')
        
        if isinstance(obj, dict):
            return {k: self._process_json_recursive(v, f"{current_path}.{k}") for k, v in obj.items()}
        
        elif isinstance(obj, list):
            # Maintain the same path for list items to match config like "asset.tags.category"
            return [self._process_json_recursive(item, current_path) for item in obj]
        
        elif isinstance(obj, str):
            should_anon, forced_type = self._should_anonymize(obj, current_path)
            if should_anon:
                # Process this value immediately with the context of this specific path
                return self._anonymize_single_value(obj, forced_type)
            return obj
            
        return obj

    def _anonymize_single_value(self, text: str, forced_type: Optional[Union[str, List[str]]]) -> str:
        # Wrapper to call the orchestrator for a single value
        entity_collector: List = [] # Create a new collector for each call if needed for DB persistence
        result = self.orchestrator.anonymize_text(
            text, 
            operator_params={"entity_collector": entity_collector}, 
            forced_entity_type=forced_type
        )
        if entity_collector:
            self.db_executor.submit(bulk_save_to_db, list(entity_collector))
        return result

    def _process_anonymization(self, output_path: str):
        is_jsonl = self.file_path.endswith(".jsonl")
        
        with open(output_path, "wb") as out_f:
            with open(self.file_path, "rb") as in_f:
                if is_jsonl:
                    for line in in_f:
                        if not line.strip(): continue
                        try:
                            data = orjson.loads(line)
                            processed_data = self._process_json_recursive(data)
                            out_f.write(orjson.dumps(processed_data) + b'\n')
                        except orjson.JSONDecodeError:
                            print(f"[!] Warning: Skipping invalid JSON line in {self.file_path}", file=sys.stderr)
                            out_f.write(line) # Write invalid lines as is
                else:
                    try:
                        data = orjson.loads(in_f.read())
                        processed_data = self._process_json_recursive(data)
                        out_f.write(orjson.dumps(processed_data, option=orjson.OPT_INDENT_2))
                    except orjson.JSONDecodeError:
                         print(f"[!] Invalid JSON in {self.file_path}", file=sys.stderr)

    def _extract_texts(self) -> Iterable[str]:
        # This method is used for NER data generation and for pre-calculating the total number of items
        if self.file_path.endswith(".jsonl"):
             with open(self.file_path, "rb") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        data = orjson.loads(line)
                        yield from self._yield_strings(data)
                    except orjson.JSONDecodeError:
                        continue # Skip invalid JSON lines during extraction
        else:
             with open(self.file_path, "rb") as f:
                data = orjson.loads(f.read())
                yield from self._yield_strings(data)

    def _yield_strings(self, obj, path=""):
        path = path.lstrip(".")
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._yield_strings(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for item in obj:
                yield from self._yield_strings(item, path)
        elif isinstance(obj, str):
             should, _ = self._should_anonymize(obj, path)
             if should: yield obj


def get_processor(file_path: str, orchestrator: AnonymizationOrchestrator, **kwargs) -> Optional[FileProcessor]:
    ext = os.path.splitext(file_path)[1].lower()
    
    processor_map = {
        ".txt": TextFileProcessor, ".log": TextFileProcessor,
        ".pdf": PdfFileProcessor,
        ".docx": DocxFileProcessor,
        ".csv": CsvFileProcessor,
        ".xlsx": XlsxFileProcessor,
        ".xml": XmlFileProcessor,
        ".json": JsonFileProcessor, ".jsonl": JsonFileProcessor,
        ".jpeg": ImageFileProcessor, ".jpg": ImageFileProcessor, ".png": ImageFileProcessor,
        ".gif": ImageFileProcessor, ".bmp": ImageFileProcessor, ".tiff": ImageFileProcessor,
        ".tif": ImageFileProcessor, ".webp": ImageFileProcessor, ".jp2": ImageFileProcessor,
        ".pnm": ImageFileProcessor,
    }
    
    processor_class = processor_map.get(ext)
    if not processor_class:
        return None
        
    return processor_class(file_path, orchestrator, **kwargs)  # type: ignore