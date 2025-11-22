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


def get_output_path(original_path, new_ext):
    """Constructs the output file path in the 'output' directory."""
    os.makedirs("output", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    
    # CORREÇÃO: Usar apenas uma chave {} para interpolar as variáveis.
    # Antes estava f"anon_{{base_name}}{{new_ext}}" (Errado - Texto literal)
    return os.path.join("output", f"anon_{base_name}{new_ext}")

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

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator):
        self.file_path = file_path
        self.orchestrator = orchestrator
        # Thread dedicada para I/O de Banco de Dados (Não bloqueia GPU)
        self.db_executor = ThreadPoolExecutor(max_workers=1)
        self.uuid_pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

    def _setup_optimization(self):
        """Desliga GC para evitar micro-stalls durante processamento pesado."""
        gc.disable()

    def _cleanup_optimization(self):
        """Restaura o sistema e fecha threads."""
        gc.enable()
        self.db_executor.shutdown(wait=True)

    def _should_anonymize(self, text: str) -> bool:
        """GATEKEEPER: Retorna False se for lixo técnico (Economiza GPU)."""
        # Aumentando o limite para evitar ruídos como 'org', 'com', etc.
        if not isinstance(text, str) or len(text) <= 3:
            return False
        
        text_lower = text.lower()
        # Usando uma stoplist muito mais conservadora
        if (text_lower in ('true', 'false', 'null', 'none', 'n/a') or 
            text.isnumeric() or 
            self.uuid_pattern.match(text)):
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
        MAX_PACK_LEN = 250_000  # Limite de segurança para cada string empacotada
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


class TextFileProcessor(FileProcessor):
    def process(self) -> str:
        output_path = self._get_output_path(".txt")
        
        BATCH_SIZE = 200 # Agrupa 200 linhas por vez para a GPU
        lines_buffer = []
        
        self._setup_optimization()
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as infile, \
                 open(output_path, "w", encoding="utf-8") as outfile:
                
                for line in tqdm(infile, desc="Processing TXT"):
                    lines_buffer.append(line)
                    
                    if len(lines_buffer) >= BATCH_SIZE:
                        # Processa 200 linhas de uma vez
                        anon_lines = self.process_batch_smart(lines_buffer)
                        outfile.writelines(anon_lines)
                        lines_buffer = []
                
                # Processa o resto
                if lines_buffer:
                    anon_lines = self.process_batch_smart(lines_buffer)
                    outfile.writelines(anon_lines)
                    
        finally:
            self._cleanup_optimization()
            
        return output_path


class PdfFileProcessor(FileProcessor):
    """Processor for PDF files, including OCR for images."""

    def process(self) -> str:
        parts: list[str] = []
        with fitz.open(self.file_path) as doc:
            for page in tqdm(doc, desc=f"Extracting text from {{os.path.basename(self.file_path)}}"):
                content_items = []
                text_blocks = page.get_text("dict").get("blocks", [])
                for block in text_blocks:
                    if block["type"] == 0:
                        block_text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "")
                            block_text += " "
                        content_items.append(
                            {
                                "bbox": block["bbox"],
                                "type": "text",
                                "content": block_text.strip(),
                            }
                        )
                images = page.get_image_info(xrefs=True)
                for img in images:
                    content_items.append(
                        {"bbox": img["bbox"], "type": "image", "content": img["xref"]}
                    )

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


class DocxFileProcessor(FileProcessor):
    """Processor for DOCX files, including OCR for images."""

    def process(self) -> str:
        doc = Document(self.file_path)
        data_parts = []

        for para in tqdm(doc.paragraphs, desc=f"Processing {{os.path.basename(self.file_path)}}"):
            para_content_parts = []
            for run in para.runs:
                drawings = run._r.xpath(".//w:drawing")
                if drawings:
                    for inline in drawings:
                        blip_embeds = inline.xpath(".//a:blip/@r:embed")
                        if blip_embeds:
                            for rel in doc.part.rels.values():
                                if "image" in rel.target_ref and rel.rId in blip_embeds[0]:
                                    img_bytes = rel.target_part.blob
                                    para_content_parts.append(
                                        extract_text_from_image(img_bytes)
                                    )
                else:
                    para_content_parts.append(run.text)

            data_parts.append("".join(para_content_parts))

        full_content = "\n".join(filter(None, data_parts))
        anonymized_content = self.orchestrator.anonymize_text(full_content)
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path


class CsvFileProcessor(FileProcessor):
    def process(self) -> str:
        output_path = self._get_output_path(".csv")
        
        # Otimização 1: Batch mais seguro
        chunk_size = 10
        
        # Otimização 2: Contar linhas rápido (sem carregar CSV)
        with open(self.file_path, "rb") as f:
            total_rows = sum(1 for _ in f) - 1

        self._setup_optimization() # Desliga GC
        
        try:
            header_written = False
            # Engine 'c' do pandas é mais rápida, on_bad_lines ignora erros
            with pd.read_csv(self.file_path, dtype=str, chunksize=chunk_size, on_bad_lines='skip', engine='c') as reader:
                
                progress_bar = tqdm(total=total_rows, desc=f"Processing CSV", unit="rows")
                batch_counter = 0

                for chunk in reader:
                    # Achata o chunk para uma lista única de strings
                    flat_values = [str(val) if pd.notna(val) else "" for val in chunk.values.flatten()]
                    
                    # A Mágica acontece aqui: chama o método inteligente da classe pai
                    anonymized_flat = self.process_batch_smart(flat_values)
                    
                    # Reconstrói o DataFrame
                    anonymized_df = pd.DataFrame(
                        np.array(anonymized_flat).reshape(chunk.shape), 
                        columns=chunk.columns
                    )
                    
                    anonymized_df.to_csv(output_path, mode='a', index=False, header=not header_written, encoding="utf-8")
                    header_written = True
                    
                    progress_bar.update(len(chunk))
                    
                    # Gerenciamento manual de GC a cada 50 chunks (100k linhas)
                    batch_counter += 1
                    if batch_counter % 50 == 0:
                        gc.collect()
                        
                progress_bar.close()
        finally:
            self._cleanup_optimization() # Restaura sistema

        return output_path


class XlsxFileProcessor(FileProcessor):
    """Processor for XLSX files, handling text and images."""

    def process(self) -> str:
        wb = openpyxl.load_workbook(self.file_path)
        all_texts = []
        cell_map = {}

        # The nature of XLSX makes streaming reads/writes difficult with openpyxl.
        # We'll show progress on a sheet/row basis for the collection part.
        print("Collecting text from XLSX file (progress based on rows)...")
        total_rows = sum(sheet.max_row for sheet in wb.worksheets)
        
        with tqdm(total=total_rows, desc="Collecting text", unit="rows") as progress_bar:
            for sheet_idx, sheet in enumerate(wb.worksheets):
                for row_idx, row in enumerate(sheet.iter_rows()):
                    for col_idx, cell in enumerate(row):
                        if cell.value and isinstance(cell.value, str):
                            all_texts.append(cell.value)
                            cell_map[(sheet_idx, row_idx, col_idx)] = len(all_texts) - 1
                    progress_bar.update(1)

        print("Anonymizing collected texts...")
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

        print("Reconstructing anonymized XLSX file...")
        with tqdm(total=total_rows, desc="Reconstructing file", unit="rows") as progress_bar:
            for sheet_idx, sheet in enumerate(wb.worksheets):
                for row_idx, row in enumerate(sheet.iter_rows()):
                    for col_idx, cell in enumerate(row):
                        if (sheet_idx, row_idx, col_idx) in cell_map:
                            original_text = all_texts[cell_map[(sheet_idx, row_idx, col_idx)]]
                            cell.value = translation_map[original_text]
                    progress_bar.update(1)

                if hasattr(sheet, '_images') and sheet._images:
                    ocr_texts = []
                    for image in list(sheet._images):
                        img_bytes = image._data()
                        ocr_text = extract_text_from_image(img_bytes)
                        if ocr_text.strip():
                            ocr_texts.append(ocr_text)
                    
                    if ocr_texts:
                        anonymized_ocr_texts = self.orchestrator.anonymize_texts(ocr_texts)
                        for anonymized_text in anonymized_ocr_texts:
                            sheet.append(["Anonymized image text:", anonymized_text])
                    
                    sheet._images.clear()

        output_path = self._get_output_path(".xlsx")
        wb.save(output_path)
        return output_path


class XmlFileProcessor(FileProcessor):
    """Processor for XML files."""

    def process(self) -> str:
        # XML processing is also difficult to stream for writing with standard libraries.
        # We read all text, anonymize, then reconstruct. Progress is shown for the iteration phases.
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        tree = etree.parse(self.file_path, parser)
        all_texts = []

        print("Collecting text from XML file...")
        iterator = tree.iter()
        all_elements = list(iterator)
        
        for element in tqdm(all_elements, desc="Collecting text", unit="elements"):
            if element.text and element.text.strip():
                all_texts.append(element.text)
            if element.tail and element.tail.strip():
                all_texts.append(element.tail)

        print("Anonymizing collected texts...")
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

        print("Reconstructing anonymized XML file...")
        for element in tqdm(all_elements, desc="Reconstructing file", unit="elements"):
            if element.text and element.text.strip() in translation_map:
                element.text = translation_map[element.text]
            if element.tail and element.tail.strip() in translation_map:
                element.tail = translation_map[element.tail]
        
        output_path = self._get_output_path(".xml")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path


import gc
import threading
from concurrent.futures import ThreadPoolExecutor
import itertools
import re
import ijson
from tqdm import tqdm
import os


class JsonFileProcessor(FileProcessor):
    # ... (Mantenha o UUID_PATTERN e _collect_strings_recursive iguais) ...
    UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator):
        super().__init__(file_path, orchestrator)
        # Cria um pool de 1 thread apenas para escrita no banco (evita lock do SQLite)
        self.db_executor = ThreadPoolExecutor(max_workers=1)

    def _collect_strings_recursive(self, obj):
        """
        Helper to recursively collect all strings from a JSON object,
        with aggressive filtering to skip non-sensitive data.
        """
        strings = []
        if isinstance(obj, dict):
            for v in obj.values():
                strings.extend(self._collect_strings_recursive(v))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(self._collect_strings_recursive(item))
        elif isinstance(obj, str):
            # GATEKEEPER LOGIC
            if (len(obj) > 3 and
                obj.lower() not in ('true', 'false') and
                not self.UUID_PATTERN.match(obj) and
                any(c.isalpha() for c in obj)):
                strings.append(obj)
        return strings

    def _reconstruct_recursive(self, obj, translation_map):
        """Helper to recursively reconstruct the object with anonymized strings."""
        if isinstance(obj, dict):
            return {k: self._reconstruct_recursive(v, translation_map) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._reconstruct_recursive(item, translation_map) for item in obj]
        elif isinstance(obj, str) and obj in translation_map:
            return translation_map[obj]
        return obj

    def process(self) -> str:
        output_path = self._get_output_path(".json")
        temp_output_path = output_path + ".tmp"
        
        BATCH_SIZE = 50 # Mantenha 50 ou teste 100 na 3060
        file_size = os.path.getsize(self.file_path)
        
        # OTIMIZAÇÃO DE MEMÓRIA: Desliga o GC automático
        gc.disable()
        batch_counter = 0
        
        print(f"[*] Starting optimized JSON processing (Batch Size: {BATCH_SIZE}) | Async DB: ON")

        try:
            with open(self.file_path, "rb") as f_in, open(temp_output_path, "w", encoding="utf-8") as f_out:
                f_out.write("[\n")
                
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Anonymizing {os.path.basename(self.file_path)}") as pbar:
                    
                    class FileWrapper:
                        def __init__(self, file, pbar):
                            self.file = file
                            self.pbar = pbar
                        def read(self, size=-1):
                            data = self.file.read(size)
                            self.pbar.update(len(data))
                            return data

                    wrapped_file = FileWrapper(f_in, pbar)
                    objects = ijson.items(wrapped_file, 'item', use_float=True)
                    
                    is_first_batch = True
                    while True:
                        batch_of_objects = list(itertools.islice(objects, BATCH_SIZE))
                        if not batch_of_objects:
                            break
                        
                        # Processa o lote
                        self._process_and_write_batch(batch_of_objects, f_out, is_first_batch)
                        is_first_batch = False
                        
                        # OTIMIZAÇÃO: Coleta lixo manualmente a cada 100 lotes para não travar a CPU
                        batch_counter += 1
                        if batch_counter % 100 == 0:
                            gc.collect()

                f_out.write("\n]")
        
        finally:
            # Garante que o GC volte e que as threads terminem
            gc.enable()
            self.db_executor.shutdown(wait=True)
        
        os.replace(temp_output_path, output_path)
        print(f"[*] Optimized processing complete. Output at: {output_path}")
        return output_path

    def _process_and_write_batch(self, batch_of_objects, outfile, is_first_batch_in_file):
        if not batch_of_objects:
            return

        all_strings_for_batch = []
        object_string_maps = [] 

        for item in batch_of_objects:
            strings_in_item = self._collect_strings_recursive(item)
            all_strings_for_batch.extend(strings_in_item)
            object_string_maps.append(strings_in_item)
        
        if not all_strings_for_batch:
            # Se não tem nada pra anonimizar, só escreve rápido
            for i, item in enumerate(batch_of_objects):
                if not (is_first_batch_in_file and i == 0):
                    outfile.write(",\n")
                outfile.write(orjson.dumps(item).decode('utf-8'))
            return

        DELIMITER = " . ||| . "
        packed_text = DELIMITER.join(all_strings_for_batch)

        entity_collector_for_batch = []
        
        # GPU Trabalha aqui (Bloqueante, não tem jeito)
        anonymized_packed_list = self.orchestrator.anonymize_texts(
            [packed_text],
            operator_params={"entity_collector": entity_collector_for_batch}
        )
        anonymized_packed = anonymized_packed_list[0] if anonymized_packed_list else ""
        
        # OTIMIZAÇÃO: Envia para o banco em Thread separada (Não bloqueia a GPU para o próximo lote)
        if entity_collector_for_batch:
            # Copia a lista para evitar condição de corrida se o coletor for reusado (embora aqui seja novo)
            data_to_save = list(entity_collector_for_batch) 
            self.db_executor.submit(bulk_save_to_db, data_to_save)

        anonymized_strings_flat = anonymized_packed.split(DELIMITER)
        
        # Fallback de segurança (se o split falhar por causa do modelo)
        if len(anonymized_strings_flat) != len(all_strings_for_batch):
             # Se falhar o packing, roda lento (fallback)
            anonymized_strings_flat = self.orchestrator.anonymize_texts_legacy(
                all_strings_for_batch,
                operator_params={"entity_collector": []} # Já salvamos antes, ignora DB aqui
            )

        current_pos = 0
        for i, item in enumerate(batch_of_objects):
            strings_in_item = object_string_maps[i]
            num_strings = len(strings_in_item)
            
            anonymized_strings_for_item = anonymized_strings_flat[current_pos : current_pos + num_strings]
            
            anonymized_item = item
            if strings_in_item:
                translation_map = dict(zip(strings_in_item, anonymized_strings_for_item))
                anonymized_item = self._reconstruct_recursive(item, translation_map)
            
            current_pos += num_strings

            if not (is_first_batch_in_file and i == 0):
                outfile.write(",\n")
            
            # Remove formatação bonita (INDENT_2) para ganhar velocidade de escrita e espaço em disco
            # Se precisar ler depois, use um formatador (jq). Máquinas preferem JSON minificado.
            outfile.write(orjson.dumps(anonymized_item).decode('utf-8'))



class ImageFileProcessor(FileProcessor):
    """Processor for image files (e.g., PNG, JPEG)."""

    def process(self) -> str:
        with open(self.file_path, "rb") as f:
            image_bytes = f.read()
        
        extracted_text = extract_text_from_image(image_bytes)
        anonymized_content = self.orchestrator.anonymize_text(extracted_text)
        
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path


def get_processor(file_path: str, orchestrator: AnonymizationOrchestrator) -> FileProcessor:
    """Factory function to get the correct file processor based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    
    processor_map = {
        ".txt": TextFileProcessor,
        ".pdf": PdfFileProcessor,
        ".docx": DocxFileProcessor,
        ".csv": CsvFileProcessor,
        ".xlsx": XlsxFileProcessor,
        ".xml": XmlFileProcessor,
        ".json": JsonFileProcessor,
        ".jpeg": ImageFileProcessor,
        ".jpg": ImageFileProcessor,
        ".png": ImageFileProcessor,
        ".gif": ImageFileProcessor,
        ".bmp": ImageFileProcessor,
        ".tiff": ImageFileProcessor,
        ".tif": ImageFileProcessor,
        ".webp": ImageFileProcessor,
        ".jp2": ImageFileProcessor,
        ".pnm": ImageFileProcessor,
    }
    
    processor_class = processor_map.get(ext)
    if not processor_class:
        raise ValueError(f"Unsupported file format: {{ext}}")
        
    return processor_class(file_path, orchestrator)