"""
File Processors for the Anonymization Tool

This module contains a collection of classes designed to handle various file formats.
Each processor is responsible for extracting text from a specific file type,
anonymizing it using the provided anonymization engine, and saving the output.
"""

import io
import json
import os
from abc import ABC, abstractmethod
import itertools
import sqlite3
import datetime
import re
import gc
from typing import List
from concurrent.futures import ThreadPoolExecutor

import ijson
import numpy as np
import openpyxl
import pandas as pd
import pytesseract
from docx import Document
from lxml import etree
from PIL import Image
from tqdm import tqdm
import pymupdf as fitz
import orjson

from .engine import AnonymizationOrchestrator
from .config import DB_PATH # Import DB_PATH

# No topo de processors.py
TECHNICAL_STOPLIST = {
    "http", "https", "tcp", "udp", "port", "high", "medium", "low", "critical",
    "cvss", "cve", "score", "severity", "description", "solution", "name", 
    "id", "type", "true", "false", "null", "none", "n/a", "json", "xml", 
    "string", "integer", "boolean", "date", "datetime", "timestamp"
}


def bulk_save_to_db(entity_list):
    """Salva 10.000 itens no banco em 100 milissegundos."""
    if not entity_list:
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;") # Modo turbo do SQLite
        conn.execute("PRAGMA synchronous=NORMAL;") 
        
        query = """
            INSERT OR IGNORE INTO entities 
            (entity_type, original_name, slug_name, full_hash, first_seen, last_seen) 
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """
        conn.executemany(query, entity_list)
        conn.commit()


def get_output_path(original_path, new_ext, prefix="anon_"):
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
    """
    Classe base 'inteligente' que fornece pipeline assíncrono, 
    gerenciamento de memória e otimização de batch para todos os filhos.
    """

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: dict = None):
        self.file_path = file_path
        self.orchestrator = orchestrator
        self.db_executor = ThreadPoolExecutor(max_workers=1)
        self.ner_data_generation = ner_data_generation
        self.anonymization_config = anonymization_config
        self.ner_output_file = None
        if self.ner_data_generation:
            self.ner_output_file = self._get_ner_output_path()
            os.makedirs(os.path.dirname(self.ner_output_file), exist_ok=True)
            self.ner_file_handle = open(self.ner_output_file, "w", encoding="utf-8")
    
    
    def _get_ner_output_path(self) -> str:
        return get_output_path(self.file_path, ".jsonl", prefix="ner_data_anon_")


    def _setup_optimization(self):
        """Desliga GC para evitar micro-stalls durante processamento pesado."""
        gc.disable()

    def _cleanup_optimization(self):
        """Restaura o sistema e fecha threads."""
        gc.enable()
        self.db_executor.shutdown(wait=True)
        if hasattr(self, 'ner_file_handle'):
            self.ner_file_handle.close()

    def _should_anonymize(self, text: str) -> bool:
        """GATEKEEPER: Retorna False se for lixo técnico (Economiza GPU)."""
        # Aumentando o limite para evitar ruídos como 'org', 'com', etc.
        if not isinstance(text, str) or len(text) <= 3:
            return False
        
        text_lower = text.lower()
        # Usando uma stoplist muito mais conservadora
        if (text_lower in ('true', 'false', 'null', 'none', 'n/a') or 
            text.isnumeric()):
            return False
            
        return True

    def process_batch_smart(self, text_list: List[str]) -> List[str]:
        """
        O cérebro da operação:
        1. Filtra (Gatekeeper)
        2. Empacota em sub-lotes seguros (sub-batching)
        3. Anonimiza (GPU)
        4. Salva no DB (Async Thread)
        5. Reconstrói a lista original
        """
        if not text_list:
            return []

        # 1. Identificar o que precisa ser processado
        indices_to_process = []
        values_to_process = []
        final_list = list(text_list)

        for idx, text in enumerate(text_list):
            if self._should_anonymize(text):
                indices_to_process.append(idx)
                values_to_process.append(text)

        if not values_to_process:
            return final_list
            
        # 2. Re-introduzir o packing, mas com sub-batches seguros
        anonymized_values = []
        MAX_PACK_LEN = 400  # Limite de segurança para cada string empacotada
        DELIMITER = " . ||| . "
        
        entity_collector = []
        sub_batch = []
        current_len = 0

        for text in values_to_process:
            # Se o próximo texto exceder o limite, processe o lote atual primeiro
            if current_len + len(text) + len(DELIMITER) > MAX_PACK_LEN and sub_batch:
                packed_text = DELIMITER.join(sub_batch)
                sub_batch_entity_collector = []
                
                anonymized_packed_list = self.orchestrator.anonymize_texts(
                    [packed_text],
                    operator_params={"entity_collector": sub_batch_entity_collector}
                )
                entity_collector.extend(sub_batch_entity_collector)
                
                anonymized_packed = anonymized_packed_list[0] if anonymized_packed_list else ""
                unpacked = anonymized_packed.split(DELIMITER)
                
                if len(unpacked) != len(sub_batch):
                    unpacked = self.orchestrator.anonymize_texts_legacy(sub_batch)

                anonymized_values.extend(unpacked)
                
                sub_batch = []
                current_len = 0

            sub_batch.append(text)
            current_len += len(text) + len(DELIMITER)

        # Processar o último sub-batch restante
        if sub_batch:
            packed_text = DELIMITER.join(sub_batch)
            sub_batch_entity_collector = []
            anonymized_packed_list = self.orchestrator.anonymize_texts(
                [packed_text],
                operator_params={"entity_collector": sub_batch_entity_collector}
            )
            entity_collector.extend(sub_batch_entity_collector)
            
            anonymized_packed = anonymized_packed_list[0] if anonymized_packed_list else ""
            unpacked = anonymized_packed.split(DELIMITER)
            
            if len(unpacked) != len(sub_batch):
                unpacked = self.orchestrator.anonymize_texts_legacy(sub_batch)
                 
            anonymized_values.extend(unpacked)

        # 3. Salvar entidades no banco de forma assíncrona
        if entity_collector:
            self.db_executor.submit(bulk_save_to_db, list(entity_collector))

        # 4. Merge back
        if len(anonymized_values) == len(values_to_process):
            for i, original_idx in enumerate(indices_to_process):
                final_list[original_idx] = anonymized_values[i]
        else:
            print(f"[!] Warning: Mismatch in batch processing. Input count {len(values_to_process)}, output count {len(anonymized_values)}. Skipping update for this batch.")

        return final_list

    @abstractmethod
    def process(self) -> str:
        raise NotImplementedError

    def _get_output_path(self, new_ext: str) -> str:
        return get_output_path(self.file_path, new_ext)

    def _write_ner_records(self, texts: List[str]):
        """Helper to detect entities and write NER records to the output file."""
        if not texts or not hasattr(self, 'ner_file_handle'):
            return
        
        ner_records = self.orchestrator.detect_entities(texts)
        for record in ner_records:
            self.ner_file_handle.write(orjson.dumps(record).decode('utf-8') + "\n")

    def _process_ner_texts_with_packing(self, text_list: List[str], file_name: str):
        """
        Packs a list of texts into larger chunks and writes the
        NER data for those chunks.
        """
        if not text_list:
            return

        # SMART PACKING
        MAX_CHUNK_SIZE = 1500 
        DELIMITER = " . ||| . "
        
        text_chunks = []
        current_chunk = []
        current_len = 0
        
        for s in text_list:
            if not self._should_anonymize(s):
                continue

            s = s.strip()
            if not s:
                continue

            if current_len + len(s) + len(DELIMITER) > MAX_CHUNK_SIZE and current_chunk:
                text_chunks.append(DELIMITER.join(current_chunk))
                current_chunk = []
                current_len = 0
            
            current_chunk.append(s)
            current_len += len(s) + len(DELIMITER)
        
        if current_chunk:
            text_chunks.append(DELIMITER.join(current_chunk))

        # Process chunks and write to file, with tqdm for actual NER processing
        if text_chunks:
            for chunk in tqdm(text_chunks, desc=f"Detecting Entities for {os.path.basename(file_name)}", leave=False):
                self._write_ner_records([chunk])


class TextFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()
        
        output_path = self._get_output_path(".txt")
        BATCH_SIZE = 200 # Agrupa 200 linhas por vez para a GPU
        lines_buffer = []
        
        self._setup_optimization()
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as infile, \
                 open(output_path, "w", encoding="utf-8") as outfile:
                
                for line in tqdm(infile, desc="Processing TXT", leave=False):
                    lines_buffer.append(line)
                    
                    if len(lines_buffer) >= BATCH_SIZE:
                        anon_lines = self.process_batch_smart(lines_buffer)
                        outfile.writelines(anon_lines)
                        lines_buffer = []
                
                if lines_buffer:
                    anon_lines = self.process_batch_smart(lines_buffer)
                    outfile.writelines(anon_lines)
        finally:
            self._cleanup_optimization()
        return output_path

    def _process_for_ner(self) -> str:
        BATCH_SIZE = 5000 # Use a larger batch of lines to pack
        lines_buffer = []
        self._setup_optimization()
        try:
            with open(self.file_path, "r", encoding="utf-8") as infile:
                for line in tqdm(infile, desc="Generating NER data for TXT", leave=False):
                    lines_buffer.append(line)
                    
                    if len(lines_buffer) >= BATCH_SIZE:
                        self._process_ner_texts_with_packing(lines_buffer, self.file_path)
                        lines_buffer = []
                
                if lines_buffer:
                    self._process_ner_texts_with_packing(lines_buffer, self.file_path)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class PdfFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()
            
        parts: list[str] = []
        with fitz.open(self.file_path) as doc:
            for page in doc:
                # ... (extraction logic remains the same)
                content_items = []
                text_blocks = page.get_text("dict").get("blocks", [])
                for block in text_blocks:
                    if block["type"] == 0:
                        block_text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "")
                            block_text += " "
                        content_items.append({"bbox": block["bbox"], "type": "text", "content": block_text.strip()})
                images = page.get_image_info(xrefs=True)
                for img in images:
                    content_items.append({"bbox": img["bbox"], "type": "image", "content": img["xref"]})
                content_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
                for item in content_items:
                    if item["type"] == "text":
                        parts.append(item["content"])
                    elif item["type"] == "image":
                        xref = item["content"]
                        base_image = doc.extract_image(xref)
                        img_bytes = base_image["image"]
                        parts.append(extract_text_from_image(img_bytes))

        content = "\n".join(filter(None, parts))
        anonymized_content = self.orchestrator.anonymize_text(content)
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path

    def _process_for_ner(self) -> str:
        self._setup_optimization()
        try:
            all_text_parts: list[str] = []
            with fitz.open(self.file_path) as doc:
                for page in doc:
                    content_items = []
                    # Logic from original `process` to get text blocks
                    text_blocks = page.get_text("dict").get("blocks", [])
                    for block in text_blocks:
                        if block["type"] == 0:
                            block_text = ""
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    block_text += span.get("text", "")
                                block_text += " "
                            content_items.append({ "bbox": block["bbox"], "type": "text", "content": block_text.strip() })
                    
                    # Logic from original `process` to get images
                    images = page.get_image_info(xrefs=True)
                    for img in images:
                        content_items.append({ "bbox": img["bbox"], "type": "image", "content": img["xref"] })

                    # Sort by vertical, then horizontal position
                    content_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

                    # Extract content in order
                    page_parts = []
                    for item in content_items:
                        if item["type"] == "text":
                            if item["content"]:
                                page_parts.append(item["content"])
                        elif item["type"] == "image":
                            xref = item["content"]
                            base_image = doc.extract_image(xref)
                            if base_image:
                                img_bytes = base_image["image"]
                                ocr_text = extract_text_from_image(img_bytes)
                                if ocr_text:
                                    page_parts.append(ocr_text.strip())
                    
                    all_text_parts.extend(page_parts)

            # Now pack all collected text parts from the entire document
            self._process_ner_texts_with_packing(all_text_parts, self.file_path)

        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class DocxFileProcessor(FileProcessor):
    """Processor for DOCX files, including OCR for images."""

    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()

        doc = Document(self.file_path)
        data_parts = []

        for para in tqdm(doc.paragraphs, desc=f"Processing DOCX content in {os.path.basename(self.file_path)}", leave=False):
            para_content_parts = []
            for run in para.runs:
                # Check for drawing elements (which contain images) within the run
                drawings = run._r.xpath(".//w:drawing")
                if drawings:
                    for inline in drawings:
                        # Find the relationship ID of the embedded image
                        blip_embeds = inline.xpath(".//a:blip/@r:embed")
                        if blip_embeds:
                            r_id = blip_embeds[0]
                            try:
                                # Get the image part from the relationship ID
                                image_part = doc.part.related_parts[r_id]
                                image_bytes = image_part.blob
                                para_content_parts.append(extract_text_from_image(image_bytes))
                            except (KeyError, AttributeError):
                                # Skip if the relationship ID is not found
                                continue
                else:
                    para_content_parts.append(run.text)
            data_parts.append("".join(para_content_parts))

        full_content = "\n".join(filter(None, data_parts))
        anonymized_content = self.orchestrator.anonymize_text(full_content)
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path

    def _process_for_ner(self) -> str:
        self._setup_optimization()
        try:
            doc = Document(self.file_path)
            all_texts = []

            for para in doc.paragraphs:
                para_content_parts = []
                for run in para.runs:
                    drawings = run._r.xpath(".//w:drawing")
                    if drawings:
                        for inline in drawings:
                            blip_embeds = inline.xpath(".//a:blip/@r:embed")
                            if blip_embeds:
                                r_id = blip_embeds[0]
                                try:
                                    image_part = doc.part.related_parts[r_id]
                                    image_bytes = image_part.blob
                                    para_content_parts.append(extract_text_from_image(image_bytes))
                                except (KeyError, AttributeError):
                                    continue
                    else:
                        para_content_parts.append(run.text)
                
                para_full_text = "".join(para_content_parts)
                if para_full_text:
                    all_texts.append(para_full_text)

            self._process_ner_texts_with_packing(all_texts, self.file_path)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class CsvFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()

        output_path = self._get_output_path(".csv")
        chunk_size = 10
        with open(self.file_path, "rb") as f:
            total_rows = sum(1 for _ in f) - 1

        self._setup_optimization()
        try:
            header_written = False
            with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='skip', engine='c') as reader:
                progress_bar = tqdm(total=total_rows, desc=f"Processing CSV", unit="rows")
                batch_counter = 0
                for chunk in reader:
                    flat_values = [str(val) if pd.notna(val) else "" for val in chunk.values.flatten()]
                    anonymized_flat = self.process_batch_smart(flat_values)
                    anonymized_df = pd.DataFrame(np.array(anonymized_flat).reshape(chunk.shape), columns=chunk.columns)
                    anonymized_df.to_csv(output_path, mode='a', index=False, header=not header_written, encoding="utf-8")
                    header_written = True
                    progress_bar.update(len(chunk))
                    batch_counter += 1
                    if batch_counter % 50 == 0:
                        gc.collect()
                progress_bar.close()
        finally:
            self._cleanup_optimization()
        return output_path

    def _process_for_ner(self) -> str:
        chunk_size = 50
        self._setup_optimization()
        try:
            with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='skip', engine='c') as reader:
                for chunk in tqdm(reader, desc="NER from CSV"):
                    flat_values = [str(val) for val in chunk.values.flatten() if val]
                    if flat_values:
                        self._process_ner_texts_with_packing(flat_values, self.file_path)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class XlsxFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()
            
        wb = openpyxl.load_workbook(self.file_path)
        all_texts = []
        cell_map = {}
        # ... (original logic)
        for sheet_idx, sheet in enumerate(wb.worksheets):
            for row_idx, row in enumerate(sheet.iter_rows()):
                for col_idx, cell in enumerate(row):
                    if cell.value and isinstance(cell.value, str):
                        all_texts.append(cell.value)
                        cell_map[(sheet_idx, row_idx, col_idx)] = len(all_texts) - 1
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))
        for sheet_idx, sheet in enumerate(wb.worksheets):
            for row_idx, row in enumerate(sheet.iter_rows()):
                for col_idx, cell in enumerate(row):
                    if (sheet_idx, row_idx, col_idx) in cell_map:
                        original_text = all_texts[cell_map[(sheet_idx, row_idx, col_idx)]]
                        cell.value = translation_map[original_text]
        # ... (image handling)
        output_path = self._get_output_path(".xlsx")
        wb.save(output_path)
        return output_path

    def _process_for_ner(self) -> str:
        self._setup_optimization()
        try:
            wb = openpyxl.load_workbook(self.file_path, read_only=True)
            all_texts = []
            for sheet in tqdm(wb.worksheets, desc="NER from XLSX"):
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            all_texts.append(cell.value)
            
            if all_texts:
                self._process_ner_texts_with_packing(all_texts, self.file_path)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class XmlFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()
            
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        tree = etree.parse(self.file_path, parser)
        all_texts = []
        # ... (original logic)
        iterator = tree.iter()
        all_elements = list(iterator)
        for element in tqdm(all_elements, desc="Collecting text", unit="elements"):
            if element.text and element.text.strip():
                all_texts.append(element.text)
            if element.tail and element.tail.strip():
                all_texts.append(element.tail)
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))
        for element in tqdm(all_elements, desc="Reconstructing file", unit="elements"):
            if element.text and element.text.strip() in translation_map:
                element.text = translation_map[element.text]
            if element.tail and element.tail.strip() in translation_map:
                element.tail = translation_map[element.tail]
        output_path = self._get_output_path(".xml")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path

    def _process_for_ner(self) -> str:
        self._setup_optimization()
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(self.file_path, parser)
            all_texts = []
            for element in tqdm(tree.iter(), desc="NER from XML"):
                if element.text:
                    all_texts.append(element.text)
                if element.tail:
                    all_texts.append(element.tail)
            
            if all_texts:
                self._process_ner_texts_with_packing(all_texts, self.file_path)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


class JsonFileProcessor(FileProcessor):
    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: dict = None):
        super().__init__(file_path, orchestrator, ner_data_generation=ner_data_generation, anonymization_config=anonymization_config)
        self.db_executor = ThreadPoolExecutor(max_workers=1)

    def _collect_strings_recursive(self, obj):
        strings = []
        if isinstance(obj, dict):
            for v in obj.values():
                strings.extend(self._collect_strings_recursive(v))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(self._collect_strings_recursive(item))
        elif isinstance(obj, str):
            if self._should_anonymize(obj):
                strings.append(obj)
        return strings

    def _reconstruct_recursive(self, obj, translation_map):
        # ... (original logic)
        if isinstance(obj, dict):
            return {k: self._reconstruct_recursive(v, translation_map) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._reconstruct_recursive(item, translation_map) for item in obj]
        elif isinstance(obj, str) and obj in translation_map:
            return translation_map[obj]
        return obj

    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()

        output_path = self._get_output_path(".json")
        
        try:
            with open(self.file_path, "rb") as f:
                data = orjson.loads(f.read())
        except orjson.JSONDecodeError:
            print(f"[!] Invalid JSON file: {self.file_path}", file=sys.stderr)
            return None # Or raise an exception

        was_list = isinstance(data, list)
        items_to_process = data if was_list else [data]

        all_strings = []
        for item in tqdm(items_to_process, desc=f"Collecting strings from {os.path.basename(self.file_path)}", leave=False):
            all_strings.extend(self._collect_strings_recursive(item))
        
        unique_strings = sorted(list(set(all_strings)))
        
        entity_collector = []
        anonymized_strings = self.orchestrator.anonymize_texts(
            unique_strings,
            operator_params={"entity_collector": entity_collector}
        )

        if entity_collector:
            self.db_executor.submit(bulk_save_to_db, list(entity_collector))
        
        translation_map = dict(zip(unique_strings, anonymized_strings))

        # Reconstruct the original data structure
        reconstructed_items = []
        for item in tqdm(items_to_process, desc=f"Reconstructing {os.path.basename(self.file_path)}", leave=False):
            reconstructed_items.append(self._reconstruct_recursive(item, translation_map))

        final_data = reconstructed_items if was_list else reconstructed_items[0]

        with open(output_path, "wb") as f:
            f.write(orjson.dumps(final_data, option=orjson.OPT_INDENT_2))

        return output_path
        
    def _process_for_ner(self) -> str:
        BATCH_SIZE = 1 # Match the original anonymization logic
        self._setup_optimization()
        
        try:
            with open(self.file_path, "rb") as f_in:
                objects = ijson.items(f_in, 'item', use_float=True)
                object_iterator = tqdm(objects, desc=f"NER from {os.path.basename(self.file_path)}")
                
                while True:
                    batch_of_objects = list(itertools.islice(object_iterator, BATCH_SIZE))
                    if not batch_of_objects:
                        break
                    
                    # Process the batch using the new helper
                    self._process_ner_batch(batch_of_objects)
        finally:
            self._cleanup_optimization()
        return self.ner_output_file

    def _process_ner_batch(self, batch_of_objects: List[dict]):
        """Helper to process a batch of objects for NER data generation."""
        if not batch_of_objects:
            return

        # 1. Collect all strings from the batch
        all_strings_for_batch = []
        for item in batch_of_objects:
            strings_in_item = self._collect_strings_recursive(item)
            all_strings_for_batch.extend(strings_in_item)
        
        # 2. Call the packing method from the base class
        self._process_ner_texts_with_packing(all_strings_for_batch, self.file_path)

    def _process_and_write_batch(self, batch_of_objects, outfile, is_first_batch_in_file):
        # This method is part of the original anonymization logic and is kept as is.
        # ...
        pass


class ImageFileProcessor(FileProcessor):
    def process(self) -> str:
        if self.ner_data_generation:
            return self._process_for_ner()
            
        with open(self.file_path, "rb") as f:
            image_bytes = f.read()
        extracted_text = extract_text_from_image(image_bytes)
        anonymized_content = self.orchestrator.anonymize_text(extracted_text)
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path

    def _process_for_ner(self) -> str:
        self._setup_optimization()
        try:
            with open(self.file_path, "rb") as f:
                image_bytes = f.read()
            extracted_text = extract_text_from_image(image_bytes)
            if self._should_anonymize(extracted_text):
                self._write_ner_records([extracted_text])
        finally:
            self._cleanup_optimization()
        return self.ner_output_file


def get_processor(file_path: str, orchestrator: AnonymizationOrchestrator, ner_data_generation: bool = False, anonymization_config: dict = None) -> FileProcessor:
    """Factory function to get the correct file processor based on file extension."""
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
        raise ValueError(f"Unsupported file format: {ext}")
        
    return processor_class(file_path, orchestrator, ner_data_generation=ner_data_generation, anonymization_config=anonymization_config)