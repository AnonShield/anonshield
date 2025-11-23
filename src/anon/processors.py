"""
File Processors for the Anonymization Tool

This module uses a Template Method Pattern. The `FileProcessor` base class defines
the main workflow for processing files, and subclasses implement the specific
details for extracting text from different file formats (e.g., PDF, DOCX, JSON).
"""
import copy
import gc
import io
import os
import sys
import ijson
import shutil
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterable, List, Generator, Optional, Dict, Tuple, Union

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
    """Constructs a secure output file path, preventing path traversal."""
    
    # 1. Resolve and validate the output directory path
    real_project_dir = os.path.realpath(os.getcwd())
    real_output_dir = os.path.realpath(output_dir)
    
    # Ensure the resolved output directory is inside the project directory
    if not real_output_dir.startswith(real_project_dir):
        raise ValueError(f"Path traversal attempt detected: Output directory '{output_dir}' is outside the project boundary.")

    os.makedirs(real_output_dir, exist_ok=True)
    
    # 2. Sanitize filename from original_path to prevent it from being used for traversal
    base_name = os.path.basename(original_path)
    if not base_name or base_name in ('.', '..'):
        raise ValueError(f"Invalid original path provided: '{original_path}'")

    safe_filename = f"{prefix}{os.path.splitext(base_name)[0]}{new_ext}"
    
    # 3. Construct the final candidate path and perform the final check
    candidate_path = os.path.join(real_output_dir, safe_filename)
    real_candidate_path = os.path.realpath(candidate_path)

    # Final check to ensure the candidate path is within the resolved output directory.
    # This is a defense-in-depth measure.
    if not real_candidate_path.startswith(real_output_dir + os.sep) and real_candidate_path != real_output_dir:
         raise ValueError(f"Path traversal attempt detected for final path of file: '{original_path}'")
        
    return candidate_path

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from image bytes using OCR."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            return pytesseract.image_to_string(img)
    except Exception as e:
        logging.exception(f"Error during OCR extraction: {e}")
        return ""


class FileProcessor(ABC):
    DEFAULT_BATCH_SIZE = 200

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: Optional[Dict] = None, min_word_length: int = 3, skip_numeric: bool = False, output_dir: str = "output", overwrite: bool = False, disable_gc: bool = False):
        self.file_path = file_path
        self.orchestrator = orchestrator
        self.ner_data_generation = ner_data_generation
        self.anonymization_config = copy.deepcopy(anonymization_config) if anonymization_config is not None else {}
        self.min_word_length = min_word_length
        self.skip_numeric = skip_numeric
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.disable_gc = disable_gc
        self.ner_output_file: Optional[str] = None
        self.ner_file_handle = None # Initialize to None

    def _get_ner_output_path(self) -> str:
        return get_output_path(self.file_path, ".jsonl", prefix="ner_data_anon_", output_dir=self.output_dir)

    def _setup_optimization(self):
        if self.disable_gc:
            gc.disable()

    def _cleanup_optimization(self):
        if self.disable_gc:
            gc.collect()
            gc.enable()
        if hasattr(self, 'ner_file_handle') and self.ner_file_handle:
            self.ner_file_handle.close()

    def _batch_iterator(self, iterator: Iterable, size: int) -> Generator[List, None, None]:
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
                    logging.warning(f"Output file '{output_path}' already exists. Use --overwrite to replace it.")
                    return output_path
                
                # Open the file handle here, within the try block
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                self.ner_file_handle = open(output_path, "w", encoding="utf-8")
                
                all_texts = self._extract_all_texts()
                self._run_ner_pipeline(all_texts)
            else:
                output_path = get_output_path(self.file_path, self._get_output_extension(), output_dir=self.output_dir)
                if os.path.exists(output_path) and not self.overwrite:
                    logging.warning(f"Output file '{output_path}' already exists. Use --overwrite to replace it.")
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
        """
        Determines if a given text should be anonymized based on a rich configuration.

        The logic follows a clear priority:
        1. Explicit exclusion (`fields_to_exclude`) always prevents anonymization.
        2. Forced anonymization (`force_anonymize`) always triggers anonymization, bypassing text-based filters
           like `min_word_length`.
        3. Text-based filtering (stop-words, numeric-only, `min_word_length`) is applied.
        4. In "explicit mode" (when `force_anonymize` or `fields_to_anonymize` is set), only fields explicitly
           listed for anonymization are processed.
        5. In "implicit mode" (default), any text that passes all the above checks is anonymized.
        """
        current_path = path.lstrip('.')

        # --- Configuration-based logic ---
        if self.anonymization_config:
            # 1. Highest priority: explicit exclusion
            if any(current_path == rule or current_path.startswith(f"{rule}.")
                   for rule in self.anonymization_config.get('fields_to_exclude', [])):
                return False, None

            # 2. Second highest priority: forced anonymization (bypasses text filters)
            force_config = self.anonymization_config.get('force_anonymize', {})
            if current_path in force_config:
                return True, force_config[current_path].get("entity_type")

        # --- Text-based filtering for auto-detection ---
        if not isinstance(text, str) or len(text.strip()) < self.min_word_length:
            return False, None
        
        stripped_text = text.strip()
        if self.skip_numeric and stripped_text.isnumeric():
            return False, None
        
        if stripped_text.lower() in TECHNICAL_STOPLIST:
            return False, None

        # --- Mode-based logic (explicit vs. implicit) ---
        if self.anonymization_config:
            is_explicit_mode = 'force_anonymize' in self.anonymization_config or \
                               'fields_to_anonymize' in self.anonymization_config
            
            if is_explicit_mode:
                # In explicit mode, only auto-anonymize if it's in the allow-list.
                if any(current_path == rule or current_path.startswith(f"{rule}.")
                       for rule in self.anonymization_config.get('fields_to_anonymize', [])):
                    return True, None
                else:
                    return False, None

        # Default to anonymizing if it passed all checks in implicit mode.
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
            bulk_save_to_db(list(entity_collector))

        if len(anonymized_values) != len(text_list):
            logging.critical(f"PII leakage detected in {self.file_path}: batch size mismatch. "
                             f"Input length: {len(text_list)}, Output length: {len(anonymized_values)}")
            raise RuntimeError("Anonymization failed to prevent data leak. Halting execution.")

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
            for page_num, page in enumerate(doc):
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
                
                # Explicitly clean up PyMuPDF page objects to prevent memory leaks
                page.clean_contents()
                del page # Ensure the page object is released

                # Periodically force garbage collection for long-running processes
                if page_num % 50 == 0:
                    gc.collect()


class CsvFileProcessor(FileProcessor):
    def _get_output_extension(self) -> str:
        return ".csv"
    
    def _process_anonymization(self, output_path: str):
        chunk_size = 1000 # Increased chunk size
        header_written = False
        
        try:
            # Efficiently get total_rows for tqdm
            with open(self.file_path, "rb") as f:
                total_rows = sum(1 for _ in f) -1 # Subtract 1 for header
        except (IOError, FileNotFoundError):
            total_rows = 0
        
        if total_rows <= 0:
            if not header_written: # Ensure empty file still gets a header if input had one
                try:
                    df_header = pd.read_csv(self.file_path, nrows=0)
                    df_header.to_csv(output_path, mode='a', index=False, header=True)
                except Exception:
                    pass # Ignore if file doesn't exist or is truly empty
            return

        # Use engine='python' for better handling of different CSV formats, though slower
        # Explicitly setting dtype=str to prevent type inference issues, and low_memory=False for large files
        with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='warn', encoding='utf-8', low_memory=False) as reader:
            progress_bar = tqdm(total=total_rows, desc=f"Processing CSV {os.path.basename(self.file_path)}", unit="rows", leave=False)
            for chunk in reader:
                anonymized_chunk = chunk.copy()
                
                texts_to_anonymize_map: Dict[Union[str, Tuple[str, ...]], Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
                
                # Collect all unique strings per column and forced_type group
                for col in chunk.columns:
                    for val in chunk[col].dropna().unique(): # Process unique values per column for efficiency
                        val_str = str(val)
                        should_anon, forced_type = self._should_anonymize(val_str, col)
                        if should_anon:
                            group_key = tuple(forced_type) if isinstance(forced_type, list) else (forced_type if forced_type is not None else "auto")
                            texts_to_anonymize_map[group_key][col].append(val_str)

                translation_map: Dict[str, str] = {}
                for group_key, cols_data in texts_to_anonymize_map.items():
                    current_forced_type = group_key if group_key != "auto" else None
                    if isinstance(current_forced_type, tuple):
                        current_forced_type = list(current_forced_type)
                    
                    # Flatten the unique texts for batch processing
                    unique_texts_for_group = list(set(val for sublist in cols_data.values() for val in sublist))
                    
                    if unique_texts_for_group:
                        anonymized_texts = self._process_batch_smart(unique_texts_for_group, forced_entity_type=current_forced_type)
                        translation_map.update(dict(zip(unique_texts_for_group, anonymized_texts)))

                # Apply translations using a vectorized approach if possible, or apply per column
                if translation_map:
                    for col in chunk.columns:
                        # Using map is generally faster than replace with a dict for Pandas Series
                        anonymized_chunk[col] = anonymized_chunk[col].map(lambda x: translation_map.get(x, x)).fillna(anonymized_chunk[col])


                anonymized_chunk.to_csv(output_path, mode='a', index=False, header=not header_written, encoding='utf-8')
                header_written = True
                progress_bar.update(len(chunk))
            progress_bar.close()

    def _extract_texts(self) -> Iterable[str]:
        chunk_size = 1000 # Increased chunk size
        with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='warn', encoding='utf-8', low_memory=False) as reader:
            for chunk in reader:
                batch_values = []
                for col in chunk.columns:
                    for val in chunk[col].dropna():
                        val_str = str(val)
                        should_anon, _ = self._should_anonymize(val_str, col)
                        if should_anon:
                            batch_values.append(val_str)
                if batch_values:
                    yield "\n".join(batch_values) + "\n" # Yield batch of values separated by newline


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
        try:
            tree = etree.parse(self.file_path, parser)
            if parser.error_log:
                for error in parser.error_log:
                    logging.warning(f"XML parsing error in {self.file_path} on line {error.line}: {error.message}")
        except etree.XMLSyntaxError as e:
            logging.error(f"Fatal XML syntax error in {self.file_path}: {e}", exc_info=True)
            with open(output_path, "w") as f:
                f.write(f"<!-- Could not parse XML file {os.path.basename(self.file_path)} due to syntax errors. -->")
            return

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
    """
    Optimized JSON/JSONL processor that uses a hybrid approach.
    - For .jsonl files, it streams line by line.
    - For .json files, it uses a fast in-memory approach for small files and a
      memory-efficient streaming approach for large files that are root-level arrays.
    """
    JSON_STREAM_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB
    JSON_CHUNK_SIZE = 1000 # Number of objects to process per batch in array streaming mode

    def _get_output_extension(self) -> str:
        return ".json" if not self.file_path.endswith(".jsonl") else ".jsonl"

    def _is_json_array(self) -> bool:
        """Detects if the root of the JSON file is an array."""
        try:
            with open(self.file_path, 'rb') as f:
                for chunk in f:
                    stripped_chunk = chunk.lstrip()
                    if stripped_chunk:
                        return stripped_chunk.startswith(b'[')
            return False
        except (IOError, OSError):
            return False

    def _process_anonymization(self, output_path: str):
        """Dispatcher for JSON processing based on file type, structure, and size."""
        if self.file_path.endswith(".jsonl"):
            self._process_anonymization_jsonl(output_path)
            return

        file_size = os.path.getsize(self.file_path)
        is_large_file = file_size >= self.JSON_STREAM_THRESHOLD_BYTES

        if is_large_file:
            if self._is_json_array():
                logging.info("Large JSON array detected (%.1f MB). Switching to memory-efficient array streaming mode.", file_size / 1024 / 1024)
                self._process_json_array_streaming(output_path, self.JSON_CHUNK_SIZE)
            else:
                raise ValueError(f"Streaming for large single JSON objects ({file_size / 1024 / 1024:.1f} MB) is not supported due to memory safety. Only large arrays are streamable.")
        else:
            self._process_anonymization_in_memory(output_path)

    def _process_json_array_streaming(self, output_path: str, chunk_size: int):
        """Processes a file containing a root-level JSON array in streamed chunks."""
        with open(self.file_path, 'rb') as in_f, open(output_path, 'wb') as out_f:
            out_f.write(b'[\n')
            is_first_chunk = True
            
            try:
                objects_iterator = ijson.items(in_f, 'item', use_float=True)
                
                for obj_batch in self._batch_iterator(objects_iterator, chunk_size):
                    batch_text_groups = defaultdict(list)
                    
                    for obj in obj_batch:
                        obj_text_groups = self._collect_strings_from_object(obj)
                        for group_key, strings in obj_text_groups.items():
                            batch_text_groups[group_key].extend(strings)
                    
                    path_aware_map = self._build_path_aware_translation_map(batch_text_groups)
                    
                    for obj in obj_batch:
                        if not is_first_chunk:
                            out_f.write(b',\n')
                        
                        reconstructed_obj = self._reconstruct_object(obj, path_aware_map)
                        out_f.write(orjson.dumps(reconstructed_obj, option=orjson.OPT_INDENT_2))
                        is_first_chunk = False
            
            except (ijson.JSONError, MemoryError) as e:
                logging.error(f"Error streaming JSON file {self.file_path}: {e}", exc_info=True)
                out_f.truncate()
                out_f.write(b'{"error": "Failed to parse source JSON file"}')

            out_f.write(b'\n]')

    def _process_anonymization_in_memory(self, output_path: str):
        """Fast in-memory processing for files smaller than the threshold."""
        with open(self.file_path, "rb") as f:
            try:
                data = orjson.loads(f.read())
            except orjson.JSONDecodeError:
                logging.error(f"Invalid JSON in {self.file_path}. Aborting.")
                with open(output_path, "wb") as out_f:
                    out_f.write(b"{}")
                return

        text_groups = self._collect_strings_from_object(data)
        path_aware_map = self._build_path_aware_translation_map(text_groups)
        
        if not path_aware_map:
            shutil.copyfile(self.file_path, output_path)
            return

        reconstructed_data = self._reconstruct_object(data, path_aware_map)
        with open(output_path, "wb") as f:
            f.write(orjson.dumps(reconstructed_data, option=orjson.OPT_INDENT_2))
    
    def _collect_strings_from_object(self, obj, path_prefix: str = "") -> Dict[str, List[str]]:
        text_groups = defaultdict(list)
        
        def _walk(sub_obj, current_path):
            if isinstance(sub_obj, dict):
                for k, v in sub_obj.items():
                    _walk(v, f"{current_path}.{k}")
            elif isinstance(sub_obj, list):
                for item in sub_obj:
                    _walk(item, current_path)
            elif isinstance(sub_obj, str):
                should_anon, forced_type = self._should_anonymize(sub_obj, current_path)
                if should_anon:
                    group_key = "auto"
                    if isinstance(forced_type, str):
                        group_key = forced_type
                    elif isinstance(forced_type, list):
                        group_key = tuple(sorted(forced_type))
                    
                    text_groups[group_key].append(sub_obj)

        _walk(obj, path_prefix.lstrip('.'))
        return text_groups
    
    def _reconstruct_object(self, obj, path_aware_map: Dict, path_prefix: str = ""):
        current_path = path_prefix.lstrip('.')
        if isinstance(obj, dict):
            return {k: self._reconstruct_object(v, path_aware_map, f"{current_path}.{k}") for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._reconstruct_object(item, path_aware_map, current_path) for item in obj]
        elif isinstance(obj, str):
            should_anon, group_key_or_list = self._should_anonymize(obj, current_path)
            if not should_anon:
                return obj

            final_group_key: Union[str, tuple] = "auto"
            if isinstance(group_key_or_list, str):
                final_group_key = group_key_or_list
            elif isinstance(group_key_or_list, list):
                final_group_key = tuple(sorted(group_key_or_list))

            if final_group_key in path_aware_map and obj in path_aware_map[final_group_key]:
                return path_aware_map[final_group_key][obj]
        return obj

    def _build_path_aware_translation_map(self, text_groups: Dict) -> Dict[Union[str, tuple], Dict[str, str]]:
        path_aware_map: Dict[Union[str, tuple], Dict[str, str]] = defaultdict(dict)
        if not text_groups:
            return path_aware_map

        total_unique_strings = sum(len(set(v)) for v in text_groups.values())
        if not total_unique_strings:
            return path_aware_map
            
        progress = tqdm(total=total_unique_strings, desc="Anonymizing collected strings", unit="str", leave=False)

        for group_key, string_list in text_groups.items():
            unique_strings = sorted(list(set(string_list)))
            if not unique_strings: continue

            forced_type: Optional[Union[str, List[str]]] = group_key if group_key != "auto" else None
            if isinstance(forced_type, tuple): 
                forced_type = list(forced_type)

            anonymized_strings = self._process_batch_smart(unique_strings, forced_entity_type=forced_type)
            path_aware_map[group_key].update(dict(zip(unique_strings, anonymized_strings)))
            progress.update(len(unique_strings))
        
        progress.close()
        return path_aware_map

    def _process_anonymization_jsonl(self, output_path: str):
        """Processes .jsonl files line by line for maximum memory efficiency."""
        with open(output_path, "wb") as out_f:
            with open(self.file_path, "rb") as in_f:
                for line in in_f:
                    if not line.strip(): continue
                    try:
                        data = orjson.loads(line)
                        text_groups = self._collect_strings_from_object(data)
                        path_aware_map = self._build_path_aware_translation_map(text_groups)
                        processed_data = self._reconstruct_object(data, path_aware_map)
                        out_f.write(orjson.dumps(processed_data) + b'\n')
                    except orjson.JSONDecodeError:
                        logging.warning(f"Skipping invalid JSON line in {self.file_path}")
                        out_f.write(line)
    
    def _extract_texts(self) -> Iterable[str]:
        if self.file_path.endswith(".jsonl"):
             with open(self.file_path, "rb") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        data = orjson.loads(line)
                        yield from self._yield_strings_from_obj(data)
                    except orjson.JSONDecodeError:
                        continue
        else:
            try:
                with open(self.file_path, 'rb') as f:
                    for obj in ijson.items(f, 'item', use_float=True, multiple_values=self._is_json_array()):
                        yield from self._yield_strings_from_obj(obj)
            except Exception as e:
                 logging.warning("Failed to stream JSON, falling back to in-memory loading. Error: %s", e)
                 with open(self.file_path, "rb") as f:
                    data = orjson.loads(f.read())
                    yield from self._yield_strings_from_obj(data)


    def _yield_strings_from_obj(self, obj, path=""):
        path = path.lstrip(".")
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._yield_strings_from_obj(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for item in obj:
                yield from self._yield_strings_from_obj(item, path)
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
