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
from typing import Iterable, List, Generator, Optional, Dict

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


def get_output_path(original_path: str, new_ext: str, prefix: str = "anon_") -> str:
    """Constructs the output file path in the 'output' directory."""
    os.makedirs("output", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    return os.path.join("output", f"{prefix}{base_name}{new_ext}")

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from image bytes using OCR."""
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception:
        return ""


class FileProcessor(ABC):
    DEFAULT_BATCH_SIZE = 200

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: Optional[Dict] = None, min_word_length: int = 3):
        self.file_path = file_path
        self.orchestrator = orchestrator
        self.ner_data_generation = ner_data_generation
        self.anonymization_config = anonymization_config or {}
        self.min_word_length = min_word_length
        self.db_executor = ThreadPoolExecutor(max_workers=1)
        self.ner_output_file: Optional[str] = None
        if self.ner_data_generation:
            self.ner_output_file = self._get_ner_output_path()
            os.makedirs(os.path.dirname(self.ner_output_file), exist_ok=True)
            self.ner_file_handle = open(self.ner_output_file, "w", encoding="utf-8")

    def _get_ner_output_path(self) -> str:
        return get_output_path(self.file_path, ".jsonl", prefix="ner_data_anon_")

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
                output_path = self.ner_output_file or ""
                all_texts = self._extract_all_texts()
                self._run_ner_pipeline(all_texts)
            else:
                output_path = get_output_path(self.file_path, self._get_output_extension())
                self._process_anonymization(output_path)
        finally:
            self._cleanup_optimization()
        return output_path

    def _process_anonymization(self, output_path: str):
        with open(output_path, "w", encoding="utf-8") as outfile:
            text_iterator = self._extract_texts()
            for text_batch in self._batch_iterator(text_iterator, self.DEFAULT_BATCH_SIZE):
                anonymized_batch = self._process_batch_smart(text_batch)
                outfile.write("".join(anonymized_batch))

    @abstractmethod
    def _extract_texts(self) -> Iterable[str]:
        raise NotImplementedError

    def _extract_all_texts(self) -> List[str]:
        return list(self._extract_texts())

    @abstractmethod
    def _get_output_extension(self) -> str:
        raise NotImplementedError

    def _should_anonymize(self, text: str, path: str = "") -> bool:
        if not isinstance(text, str) or len(text.strip()) < self.min_word_length:
            return False
            
        text_lower = text.lower().strip()
        if text_lower.isnumeric() or text_lower in TECHNICAL_STOPLIST:
            return False

        if path and self.anonymization_config.get('fields_to_exclude'):
            if any(path.lstrip('.').startswith(p) for p in self.anonymization_config['fields_to_exclude']):
                return False
        
        fields_to_anonymize = self.anonymization_config.get('fields_to_anonymize')
        if path and fields_to_anonymize:
            return path.lstrip('.') in fields_to_anonymize

        if not fields_to_anonymize:
            return True
            
        return False

    def _process_batch_smart(self, text_list: List[str], forced_entity_type: Optional[str] = None) -> List[str]:
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
            if not self._should_anonymize(s): continue
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
                    texts_to_process = [str(val) for val in chunk[col] if self._should_anonymize(str(val), col)]
                    if not texts_to_process: continue
                    
                    anonymized_texts = self._process_batch_smart(texts_to_process)
                    translation_map = dict(zip(texts_to_process, anonymized_texts))
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
                        if self._should_anonymize(str(val), col):
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
                        if self._should_anonymize(cell.value, path):
                            yield cell.value
    
    def _process_anonymization(self, output_path: str):
        wb = openpyxl.load_workbook(self.file_path)
        
        all_texts = list(set(self._extract_texts()))
        if not all_texts:
            wb.save(output_path)
            return
            
        anonymized_texts = self._process_batch_smart(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

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
                if self._should_anonymize(element.text, path):
                    yield element.text
            if element.tail and element.tail.strip():
                 if self._should_anonymize(element.tail, path + "/tail()"):
                    yield element.tail
            
            for key, value in element.attrib.items():
                attr_path = f"{path}[@{key}]"
                if self._should_anonymize(value, attr_path):
                    yield value
            element.clear()

    def _process_anonymization(self, output_path: str):
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        tree = etree.parse(self.file_path, parser)
        
        all_texts = list(set(self._extract_texts()))
        if not all_texts:
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            return

        anonymized_texts = self._process_batch_smart(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

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
        return ".json"

    def _walk_and_collect_strings(self, obj, path_prefix: str = "", out_dict: Optional[Dict] = None) -> Dict:
        if out_dict is None: 
            out_dict = defaultdict(list)
        current_path = path_prefix.lstrip('.')

        if isinstance(obj, dict):
            for k, v in obj.items():
                self._walk_and_collect_strings(v, f"{current_path}.{k}", out_dict)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_and_collect_strings(item, current_path, out_dict)
        elif isinstance(obj, str):
            if self._should_anonymize(obj, current_path):
                fields_to_anonymize = self.anonymization_config.get("fields_to_anonymize", {})
                field_config = fields_to_anonymize.get(current_path, {})
                entity_type = field_config.get("entity_type")
                group = entity_type if entity_type else "auto"
                out_dict[group].append(obj)
        return out_dict

    def _walk_and_reconstruct(self, obj, translation_map: Dict, path_prefix: str = ""):
        current_path = path_prefix.lstrip('.')
        if isinstance(obj, dict):
            return {k: self._walk_and_reconstruct(v, translation_map, f"{current_path}.{k}") for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._walk_and_reconstruct(item, translation_map, current_path) for item in obj]
        elif isinstance(obj, str):
            if self._should_anonymize(obj, current_path) and obj in translation_map:
                return translation_map[obj]
        return obj

    def _extract_all_texts(self) -> List[str]:
        with open(self.file_path, "rb") as f:
            data = orjson.loads(f.read())
        strings_by_type = self._walk_and_collect_strings(data)
        all_strings = []
        for string_list in strings_by_type.values():
            all_strings.extend(string_list)
        return all_strings

    def _process_anonymization(self, output_path: str):
        with open(self.file_path, "rb") as f:
            data = orjson.loads(f.read())

        strings_by_type = self._walk_and_collect_strings(data)
        translation_map = {}

        for entity_type, string_list in strings_by_type.items():
            unique_strings = sorted(list(set(string_list)))
            if not unique_strings: continue

            forced_type = entity_type if entity_type != "auto" else None
            anonymized_strings = self._process_batch_smart(unique_strings, forced_entity_type=forced_type)
            translation_map.update(dict(zip(unique_strings, anonymized_strings)))
        
        reconstructed_data = self._walk_and_reconstruct(data, translation_map)
        with open(output_path, "wb") as f:
            f.write(orjson.dumps(reconstructed_data, option=orjson.OPT_INDENT_2))

    def _extract_texts(self) -> Iterable[str]:
        yield from ()


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