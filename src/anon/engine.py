# src/anon/engine.py

import hashlib
import hmac
import re
import sys
from typing import Dict, Iterable, List

import pandas as pd
import spacy
import torch
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.batch_analyzer_engine import BatchAnalyzerEngine
from presidio_analyzer.nlp_engine import NerModelConfiguration, TransformersNlpEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from .config import (
    DB_PATH,
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
)


SUPPORTED_LANGUAGES = {
    "ca": "Catalan", "zh": "Chinese", "hr": "Croatian", "da": "Danish",
    "nl": "Dutch", "en": "English", "fi": "Finnish", "fr": "French",
    "de": "German", "el": "Greek", "it": "Italian", "ja": "Japanese",
    "ko": "Korean", "lt": "Lithuanian", "mk": "Macedonian", "nb": "Norwegian Bokmål",
    "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "sl": "Slovenian", "es": "Spanish", "sv": "Swedish", "uk": "Ukrainian"
}


class CustomSlugAnonymizer(Operator):
    """
    Operador customizado do Presidio que substitui o texto por um slug com HMAC.
    """
    def operate(self, text: str, params: dict | None = None) -> str:
        # 1. Limpa o texto (remove espaços extras)
        clean_text = " ".join(text.split()).strip()
        
        # 2. Gera HMAC seguro (usando a chave secreta)
        full_hash = hmac.new(
            SECRET_KEY.encode(), 
            clean_text.encode(), 
            hashlib.sha256
        ).hexdigest()

        entity_type = params.get("entity_type", "UNKNOWN") if params else "UNKNOWN"
        slug_length = params.get("slug_length", None) if params else None
        
        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash

        if params and "entity_collector" in params:
            params["entity_collector"].append((entity_type, clean_text, display_hash, full_hash))

        return f"[{entity_type}_{display_hash}]"

    def validate(self, params: dict | None = None) -> None: pass
    def operator_name(self) -> str: return "custom_slug"
    def operator_type(self) -> OperatorType: return OperatorType.Anonymize


def load_custom_recognizers(langs: List[str]) -> List[PatternRecognizer]:
    """Carrega reconhecedores Regex otimizados para entidades de infraestrutura/cybersecurity."""
    
    # URL recognizer
    url_pattern = Pattern(
      name="URL Pattern", 
      regex=r"(?:https?://|ftp://|www\.)[^\s]+\.(?:com|net|org|edu|gov|mil|int|br|app|dev|io|co|uk|de|fr|es|it|ru|cn|jp|kr|au|ca|mx|ar|cl|pe|co\.uk|com\.br|org\.br|gov\.br|edu\.br|net\.br|vercel\.app|herokuapp\.com|github\.io|gitlab\.io|netlify\.app|firebase\.app|appspot\.com|cloudfront\.net|amazonaws\.com|azure\.com|digitalocean\.com)[^\s]*",
      score=0.7
    )

    # IP address recognizers (IPv4 and IPv6)
    ip_pattern = Pattern(
        name="IP Address Pattern", 
        regex=r"\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", 
        score=0.85
    )
    # IPv6 Otimizado (Detecta grupos de hex e dois pontos, sem validação estrita lenta)
    ipv6_pattern = Pattern(
        name="IPv6 Address Pattern", 
        regex=r"(?<![a-zA-Z0-9])(?:[A-Fa-f0-9]{1,4}:){2,}(?:[A-Fa-f0-9]{1,4}|:)(?![a-zA-Z0-9])", 
        score=0.6
    )

    hostname_patterns = [
        Pattern(
            name="FQDN Pattern",
            regex=r"\b([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
            score=0.6
        ),
        Pattern(
            name="Common Hostname Pattern",
            regex=r"\b(localhost)\b", 
            score=0.65
        ),
        Pattern(
            name="Certificate CN Pattern",
            regex=r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]|[a-f0-9]{8,16})\b",
            score=0.7
        ),
        Pattern(
            name="Standalone Hex Hostname Pattern",
            regex=r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)",
            score=0.6
        ),
    ]

    # Hashes (SHA256 e MD5 com dois-pontos)
    hash_patterns = [
        Pattern(name="SHA256 Hash", regex=r"\b[0-9a-fA-F]{64}\b", score=0.8),
        Pattern(
            name="MD5 Colon-Separated Hash",
            regex=r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b",
            score=0.85 
        )
    ]

    # UUIDs
    uuid_pattern = Pattern(
        name="UUID Pattern",
        regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        score=0.8
    )

    # Seriais de Certificado
    serial_pattern = Pattern(
        name="Certificate Serial (40-char Hex)",
        regex=r"\b[0-9a-fA-F]{40}\b",
        score=0.75
    )

    # Strings CPE
    cpe_pattern = Pattern(
        name="CPE String",
        regex=r"\bcpe:/[a-z]:[^:]+:[^:]+(:[^:]+){0,4}\b",
        score=0.7
    )
    
    # Corpos de Certificado (Base64)
    cert_body_pattern = Pattern(
        name="Certificate Body (Base64)",
        regex=r"\bMII[a-zA-Z0-9+/=\n]{100,}\b", 
        score=0.8
    )

    # MAC Address
    mac_pattern = Pattern(
        name="MAC Address",
        regex=r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
        score=0.8
    )

    # File Paths (Unix/Windows)
    path_pattern = Pattern(
        name="User Home Path",
        regex=r"(?:/home/|/Users/|C:\\Users\\)([^/\\]+)",
        score=0.6
    )

    recognizers = []
    for lang in langs:
        recognizers.append(PatternRecognizer(supported_entity="URL", patterns=[url_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="HOSTNAME", patterns=hostname_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="HASH", patterns=hash_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="UUID", patterns=[uuid_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_SERIAL", patterns=[serial_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CPE_STRING", patterns=[cpe_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_BODY", patterns=[cert_body_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="MAC_ADDRESS", patterns=[mac_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="FILE_PATH", patterns=[path_pattern], supported_language=lang))
        
    return recognizers

class AnonymizationOrchestrator:
    """
    Orquestrador de Anonimização Seguro e Otimizado.
    Combina modelos Transformer (via SpaCy) com Regex de alta performance.
    """

    def __init__(self, lang: str, allow_list: List[str], entities_to_preserve: List[str], slug_length: int | None = None):
        self.lang = lang
        self.allow_list = set(allow_list) 
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.total_entities_processed = 0
        self.entity_counts = {}
        self.cache = {}
        
        # Configura engines do Presidio
        self.analyzer_engine, self.anonymizer_engine = self._setup_engines()
        
        # Pré-compilação de Regex para performance (bypass do overhead do Presidio)
        self.compiled_patterns = []
        custom_recognizers = load_custom_recognizers([self.lang])
        
        for recognizer in custom_recognizers:
            # --- FIX: Presidio armazena como LISTA (supported_entities) ---
            entity_type = recognizer.supported_entities[0] 
            
            if entity_type in self.entities_to_preserve:
                continue
                
            for pattern in recognizer.patterns:
                try:
                    self.compiled_patterns.append({
                        "label": entity_type, # Usa a variável local corrigida
                        "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                        "score": pattern.score
                    })
                except re.error:
                    pass

    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Inicializa Engines mantendo o XLM-Roberta e configurações de segurança."""
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        supported_langs = set(["en", self.lang])

        trf_model_config = []
        for lang_code in supported_langs:
            spacy_model_name = lang_model_map.get(lang_code, f"{lang_code}_core_news_lg")
            trf_model_config.append(
                # Mantém o modelo XLM-Roberta definido no config.py
                {"lang_code": lang_code, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}
            )

        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=ENTITY_MAPPING, 
            aggregation_strategy="max", 
            labels_to_ignore=["O"]
        )
        
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=list(supported_langs))
        
        # Adiciona recognizers ao engine padrão também (para fallback)
        for recognizer in load_custom_recognizers(langs=core_analyzer.supported_languages):
            core_analyzer.registry.add_recognizer(recognizer)
        
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, operator_params: dict = None) -> str:
        if not isinstance(text, str) or not text.strip():
            return text
        return self.anonymize_texts([text], operator_params=operator_params)[0]

    def anonymize_texts(self, texts: List[str], operator_params: dict = None) -> List[str]:
        """
        Pipeline Otimizada: Usa SpaCy Pipe + Regex Compilado + HMAC Seguro.
        Evita o overhead do Presidio Analyzer wrapper, mas mantém a precisão.
        """
        if not texts:
            return []

        # 1. Prepara lista e verifica Cache
        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        final_anonymized_list = [""] * len(original_texts)
        
        texts_to_process_indices = {} 
        unique_texts_list = []

        for i, text in enumerate(original_texts):
            if not text: continue
            
            if text in self.cache:
                final_anonymized_list[i] = self.cache[text]
            else:
                if text not in texts_to_process_indices:
                    texts_to_process_indices[text] = []
                    unique_texts_list.append(text)
                texts_to_process_indices[text].append(i)

        if not unique_texts_list:
            return final_anonymized_list

        # 2. Configuração
        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")
        
        # Lista de entidades a anonimizar (respeitando a lista de preservação)
        entities_to_anonymize = set(self._get_entities_to_anonymize())

        # Acessa o modelo SpaCy correto do dicionário
        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang] 

        # 3. Processamento em Batch (GPU)
        docs = nlp_model.pipe(unique_texts_list, batch_size=500)

        for doc in docs:
            original_doc_text = doc.text
            detected_entities = []

            # A. Detecção via Modelo Transformer (IA)
            for ent in doc.ents:
                # Normaliza etiquetas (PER -> PERSON, LOC -> LOCATION)
                normalized_label = ENTITY_MAPPING.get(ent.label_, ent.label_)

                if normalized_label not in entities_to_anonymize or ent.text in self.allow_list:
                    continue

                detected_entities.append({
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "label": normalized_label,
                    "text": ent.text,
                    "score": 1.0 # IA tem prioridade máxima
                })

            # B. Detecção via Regex Compilado (Alta Velocidade)
            for pat in self.compiled_patterns:
                for match in pat["regex"].finditer(original_doc_text):
                    match_text = match.group()
                    if match_text not in self.allow_list:
                        detected_entities.append({
                            "start": match.start(),
                            "end": match.end(),
                            "label": pat["label"],
                            "text": match_text,
                            "score": pat["score"]
                        })

            # C. Resolução de Conflitos (Overlap)
            # Ordena por início, score descrescente e tamanho descrescente
            detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))
            
            merged_entities = []
            last_end = -1
            
            for ent in detected_entities:
                if ent["start"] >= last_end:
                    merged_entities.append(ent)
                    last_end = ent["end"]
                else:
                    continue

            # D. Reconstrução e Anonimização com HMAC
            new_text_parts = []
            current_idx = 0
            
            for ent in merged_entities:
                self.total_entities_processed += 1
                self.entity_counts[ent["label"]] = self.entity_counts.get(ent["label"], 0) + 1
                
                new_text_parts.append(original_doc_text[current_idx:ent["start"]])
                
                clean_text = " ".join(ent["text"].split()).strip()
                
                # CRÍTICO: Uso de HMAC seguro para anonimização determinística mas irreversível
                full_hash = hmac.new(
                    SECRET_KEY.encode(), 
                    clean_text.encode(), 
                    hashlib.sha256
                ).hexdigest()
                
                display_hash = full_hash[:self.slug_length] if self.slug_length else full_hash

                if entity_collector is not None:
                    entity_collector.append((ent["label"], clean_text, display_hash, full_hash))

                new_text_parts.append(f"[{ent['label']}_{display_hash}]")
                current_idx = ent["end"]
            
            new_text_parts.append(original_doc_text[current_idx:])
            anonymized_text = "".join(new_text_parts)

            # E. Cache e Distribuição
            self.cache[original_doc_text] = anonymized_text
            for idx in texts_to_process_indices[original_doc_text]:
                final_anonymized_list[idx] = anonymized_text

        return final_anonymized_list

    def anonymize_texts_legacy(self, texts: List[str], operator_params: dict = None) -> List[str]:
        """
        Método legado (mais lento) para fallback.
        Mantém compatibilidade mas usa a engine padrão do Presidio.
        """
        if not texts:
            return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        final_anonymized_list = [""] * len(original_texts)
        
        texts_to_process_map = {}
        for i, text in enumerate(original_texts):
            if text in self.cache:
                final_anonymized_list[i] = self.cache[text]
            else:
                if text not in texts_to_process_map:
                    texts_to_process_map[text] = []
                texts_to_process_map[text].append(i)

        if not texts_to_process_map:
            return final_anonymized_list
            
        unique_texts_to_process = list(texts_to_process_map.keys())
        entities_to_anonymize = self._get_entities_to_anonymize()
        
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            unique_texts_to_process,
            language=self.lang,
            entities=entities_to_anonymize,
            score_threshold=0.6,
        )

        if operator_params is None: operator_params = {}
        operator_params["total_entities_counter"] = self
        operator_params["entity_counts"] = self.entity_counts

        for text, analyzer_results in zip(unique_texts_to_process, analyzer_results_iterator):
            filtered_analyzer_results = [
                result for result in analyzer_results
                if text[result.start:result.end] not in self.allow_list
            ]
            anonymizer_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=filtered_analyzer_results,
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params)},
            )
            
            anonymized_text = anonymizer_result.text
            self.cache[text] = anonymized_text
            for index in texts_to_process_map[text]:
                final_anonymized_list[index] = anonymized_text
        
        return final_anonymized_list

    def _get_entities_to_anonymize(self) -> List[str]:
        """Retorna lista de entidades ativas (excluindo as preservadas)."""
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [
            ent for ent in all_entities 
            if not self.entities_to_preserve or ent not in self.entities_to_preserve
        ]