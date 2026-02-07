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

import numpy as np
import openpyxl
import pandas as pd
import pytesseract
from docx import Document
from lxml import etree
from PIL import Image
import pymupdf as fitz

from .engine import AnonymizationOrchestrator


def get_output_path(original_path, new_ext):
    """Constructs the output file path in the 'output' directory."""
    os.makedirs("output", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    return os.path.join("output", f"anon_{base_name}{new_ext}")


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from image bytes using OCR."""
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception:
        return ""


class FileProcessor(ABC):
    """Abstract base class for file processors."""

    def __init__(self, file_path: str, orchestrator: AnonymizationOrchestrator):
        self.file_path = file_path
        self.orchestrator = orchestrator

    @abstractmethod
    def process(self) -> str:
        """
        Processes the file, anonymizes its content, and returns the output path.
        """
        raise NotImplementedError

    def _get_output_path(self, new_ext: str) -> str:
        """Gets the standardized output path for the processed file."""
        return get_output_path(self.file_path, new_ext)


class TextFileProcessor(FileProcessor):
    """Processor for plain text files (.txt)."""

    def process(self) -> str:
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        anonymized_content = self.orchestrator.anonymize_text(content)
        output_path = self._get_output_path(".txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(anonymized_content)
        return output_path


class PdfFileProcessor(FileProcessor):
    """Processor for PDF files, including OCR for images."""

    def process(self) -> str:
        parts: list[str] = []
        with fitz.open(self.file_path) as doc:
            for page in doc:
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

        for para in doc.paragraphs:
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
    """Processor for CSV files, processed in batches."""

    def process(self) -> str:
        df = pd.read_csv(self.file_path, dtype=str)
        all_values = [str(val) if val is not None else "" for val in df.values.flatten().tolist()]
        
        anonymized_values = self.orchestrator.anonymize_texts(all_values)
        
        anonymized_array = np.array(anonymized_values).reshape(df.shape)
        anonymized_df = pd.DataFrame(anonymized_array, columns=df.columns, index=df.index)
        
        output_path = self._get_output_path(".csv")
        anonymized_df.to_csv(output_path, index=False, encoding="utf-8")
        return output_path


class XlsxFileProcessor(FileProcessor):
    """Processor for XLSX files, handling text and images."""

    def process(self) -> str:
        wb = openpyxl.load_workbook(self.file_path)
        all_texts = []
        cell_map = {}

        for sheet_idx, sheet in enumerate(wb.worksheets):
            # Collect cell text
            for row_idx, row in enumerate(sheet.iter_rows()):
                for col_idx, cell in enumerate(row):
                    if cell.value and isinstance(cell.value, str):
                        all_texts.append(cell.value)
                        cell_map[(sheet_idx, row_idx, col_idx)] = len(all_texts) - 1

        # Anonymize all texts at once
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

        # Reconstruct the workbook
        for sheet_idx, sheet in enumerate(wb.worksheets):
            for row_idx, row in enumerate(sheet.iter_rows()):
                for col_idx, cell in enumerate(row):
                    if (sheet_idx, row_idx, col_idx) in cell_map:
                        original_text = all_texts[cell_map[(sheet_idx, row_idx, col_idx)]]
                        cell.value = translation_map[original_text]

            # Clear old images and handle OCR text as before
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
        parser = etree.XMLParser(recover=True, strip_cdata=False)
        tree = etree.parse(self.file_path, parser)
        all_texts = []

        # Collect all text content
        for element in tree.iter():
            if element.text and element.text.strip():
                all_texts.append(element.text)
            if element.tail and element.tail.strip():
                all_texts.append(element.tail)

        # Anonymize in a single batch
        anonymized_texts = self.orchestrator.anonymize_texts(all_texts)
        translation_map = dict(zip(all_texts, anonymized_texts))

        # Reconstruct the XML
        for element in tree.iter():
            if element.text and element.text.strip() in translation_map:
                element.text = translation_map[element.text]
            if element.tail and element.tail.strip() in translation_map:
                element.tail = translation_map[element.tail]
        
        output_path = self._get_output_path(".xml")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path


class JsonFileProcessor(FileProcessor):
    """Processor for JSON files."""

    def process(self) -> str:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_strings = []
        def collect_strings(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    collect_strings(v)
            elif isinstance(obj, list):
                for item in obj:
                    collect_strings(item)
            elif isinstance(obj, str):
                all_strings.append(obj)

        collect_strings(data)
        anonymized_strings = self.orchestrator.anonymize_texts(all_strings)
        translation_map = dict(zip(all_strings, anonymized_strings))

        def recursive_reconstruct(obj):
            if isinstance(obj, dict):
                return {k: recursive_reconstruct(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursive_reconstruct(item) for item in obj]
            elif isinstance(obj, str) and obj in translation_map:
                return translation_map[obj]
            return obj

        anonymized_data = recursive_reconstruct(data)
        output_path = self._get_output_path(".json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(anonymized_data, f, indent=4, ensure_ascii=False)
        return output_path


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
        raise ValueError(f"Unsupported file format: {ext}")
        
    return processor_class(file_path, orchestrator)
