# src/anon/engine.py

import hashlib
import hmac
import re
from typing import List

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
    """Carrega reconhecedores Regex otimizados para entidades de infraestrutura/cybersecurity/PII."""
    
    # --- 1. URL & REDE ---
    url_pattern = Pattern(
      name="URL Pattern", 
      regex=r"(?:https?://|ftp://|www\.)[^\s]+(?:\.(?:com|net|org|edu|gov|mil|int|br|app|dev|io|co|uk|de|fr|es|it|ru|cn|jp|kr|au|ca|mx|ar|cl|pe|co\.uk|com\.br|org\.br|gov\.br|edu\.br|net\.br|vercel\.app|herokuapp\.com|github\.io|gitlab\.io|netlify\.app|firebase\.app|appspot\.com|cloudfront\.net|amazonaws\.com|azure\.com|digitalocean\.com)|localhost|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?::[0-9]{1,5})?(?:/[^\s]*)?",
      score=0.7
    )

    ip_pattern = Pattern(
        name="IP Address Pattern", 
        regex=r"(?<![\.\d])(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?!\.[\d])", 
        score=0.85
    )
    
    ipv6_pattern = Pattern(
      name="IPv6 Address Pattern", 
      regex=r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", 
      score=0.6
    )
    serial_pattern = Pattern(
        name="Certificate Serial",
        regex=r"\b[0-9a-fA-F]{16,40}\b",  # Mudado de {40} para {16,40}
        score=0.75
    )
    
    # OID (Object Identifier) - Garantindo que pegue a estrutura hierárquica
    oid_pattern = Pattern(
        name="OID Pattern",
        regex=r"\b[0-2](?:\.\d+){3,}\b", 
        score=0.95
    )
    port_pattern = Pattern(
        name="Port/Protocol",
        regex=r"\b\d{1,5}/(?:tcp|udp|sctp)\b",
        score=0.85
    )
    hostname_patterns = [
        Pattern(name="FQDN Pattern", regex=r"\b(?!Not-A\.Brand)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b", score=0.6),
        Pattern(name="Certificate CN Pattern", regex=r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]|[a-f0-9]{8,16})\b", score=0.7),
        Pattern(name="Standalone Hex Hostname Pattern", regex=r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)", score=0.6),
    ]

    # --- 2. CRIPTOGRAFIA & SEGURANÇA ---
    hash_patterns = [
        Pattern(name="SHA256 Hash", regex=r"\b[0-9a-fA-F]{64}\b", score=0.8),
        Pattern(name="MD5 Colon-Separated Hash", regex=r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b", score=0.85)
    ]

    # CVE ID (Novo)
    cve_pattern = Pattern(
        name="CVE ID Pattern",
        regex=r"\bCVE-\d{4}-\d{4,}\b", 
        score=0.95
    )

    # CPE String
    cpe_pattern = Pattern(
        name="CPE String",
        regex=r"\bcpe:(?:/|2\.3:)[aho](?::[A-Za-z0-9\._\-~%*]+){2,}\b",
        score=0.9
    )

    # Tokens de Sessão (Auth Tokens)
    auth_token_patterns = [
        Pattern(name="Cookie/Session Assignment", regex=r"(?<=[=])[a-zA-Z0-9\-_]{32,128}\b", score=0.9),
        Pattern(name="Generic Auth Token", regex=r"\b[a-zA-Z0-9]{32,128}\b", score=0.5)
    ]

    # --- 3. CREDENCIAIS & SEGREDOS (Novo) ---
    password_pattern = Pattern(
        name="Contextual Password",
        regex=r"(?<=password=|passwd=|pwd=|secret=|api_key=|apikey=|access_key=|client_secret=)[^\s,;\"']+\b",
        score=0.95
    )

    username_pattern = Pattern(
        name="Contextual Username",
        regex=r"(?<=user=|username=|uid=|login=|user_id=)[a-zA-Z0-9_.-]+\b",
        score=0.8
    )

    # --- 4. DADOS PESSOAIS (PII) ---
    email_pattern = Pattern(name="Email Pattern", regex=r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", score=1.0)
    
    phone_pattern = Pattern(
        name="Phone Number Pattern",
        regex=r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{2,3}\)?[-. ]?\d{4,5}[-. ]?\d{4}\b",
        score=0.6
    )

    # CPF (Simplificado)
    cpf_pattern = Pattern(name="CPF Pattern", regex=r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", score=0.85)

    cc_pattern = Pattern(name="Credit Card Pattern", regex=r"\b(?:\d{4}[- ]?){3}\d{4}\b", score=0.7)

    # --- 5. IDENTIFICADORES DIVERSOS ---
    uuid_pattern = Pattern(name="UUID Pattern", regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", score=0.8)
    cert_body_pattern = Pattern(name="Certificate Body", regex=r"\bMII[a-zA-Z0-9+/=\n]{100,}\b", score=0.8)
    mac_pattern = Pattern(name="MAC Address", regex=r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", score=0.8)
    path_pattern = Pattern(name="User Home Path", regex=r"(?:/home/|/Users/|C:\\Users\\)([^/\\]+)", score=0.6)
    # Captura blocos de Assinatura ou Chave Pública PGP
    pgp_pattern = Pattern(
        name="PGP Block",
        # Pega desde o BEGIN até o END, incluindo quebras de linha (DOTALL)
        regex=r"-----BEGIN PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----.+?-----END PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----",
        score=0.95
    )
    recognizers = []
    for lang in langs:
        # Infra
        recognizers.append(PatternRecognizer(supported_entity="URL", patterns=[url_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="HOSTNAME", patterns=hostname_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="MAC_ADDRESS", patterns=[mac_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="FILE_PATH", patterns=[path_pattern], supported_language=lang))
        
        # Segurança
        recognizers.append(PatternRecognizer(supported_entity="HASH", patterns=hash_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="AUTH_TOKEN", patterns=auth_token_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CVE_ID", patterns=[cve_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CPE_STRING", patterns=[cpe_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_SERIAL", patterns=[serial_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_BODY", patterns=[cert_body_pattern], supported_language=lang))
        
        # Credenciais & PII
        recognizers.append(PatternRecognizer(supported_entity="PASSWORD", patterns=[password_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="USERNAME", patterns=[username_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[email_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern, cpf_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CREDIT_CARD", patterns=[cc_pattern], supported_language=lang))
        
        # Diversos
        recognizers.append(PatternRecognizer(supported_entity="UUID", patterns=[uuid_pattern], supported_language=lang))

    return recognizers

class AnonymizationOrchestrator:
    """
    Orquestrador de Anonimização Seguro e Otimizado.
    Combina modelos Transformer (via SpaCy) com Regex de alta performance.
    """

    def __init__(self, lang: str, allow_list: List[str], entities_to_preserve: List[str], slug_length: int | None = None, strategy: str = "presidio"):
        self.lang = lang
        self.allow_list = set(allow_list) 
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.strategy = strategy
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

    def anonymize_text(self, text: str, operator_params: dict = None, forced_entity_type: str = None) -> str:
        if not isinstance(text, str) or not text.strip():
            return text
        return self.anonymize_texts([text], operator_params=operator_params, forced_entity_type=forced_entity_type)[0]

    def anonymize_texts(self, texts: List[str], operator_params: dict = None, forced_entity_type: str = None) -> List[str]:
        """
        Anonymizes a list of texts.
        If a `forced_entity_type` is provided, it bypasses detection and applies
        the specified type directly. Otherwise, it uses the configured strategy.
        """
        if forced_entity_type:
            return self._anonymize_texts_forced_type(texts, forced_entity_type, operator_params)
        
        if self.strategy == "fast":
            return self._anonymize_texts_fast_path(texts, operator_params)
        return self._anonymize_texts_presidio(texts, operator_params)

    def _anonymize_texts_forced_type(self, texts: List[str], entity_type: str, operator_params: dict = None) -> List[str]:
        """Anonymizes texts using a predefined entity type, bypassing analysis."""
        anonymized_list = []
        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")

        for text in texts:
            if not isinstance(text, str) or not text.strip():
                anonymized_list.append(text)
                continue

            clean_text = " ".join(text.split()).strip()
            
            # Use cache if available
            cache_key = f"forced_{entity_type}_{clean_text}"
            if cache_key in self.cache:
                anonymized_list.append(self.cache[cache_key])
                continue

            full_hash = hmac.new(
                SECRET_KEY.encode(),
                clean_text.encode(),
                hashlib.sha256
            ).hexdigest()

            display_hash = full_hash[:self.slug_length] if self.slug_length is not None else full_hash

            if entity_collector is not None:
                entity_collector.append((entity_type, clean_text, display_hash, full_hash))
            
            anonymized_text = f"[{entity_type}_{display_hash}]"
            self.cache[cache_key] = anonymized_text
            anonymized_list.append(anonymized_text)

        return anonymized_list


    def _anonymize_texts_fast_path(self, texts: List[str], operator_params: dict = None) -> List[str]:
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

                # if normalized_label not in entities_to_anonymize or ent.text in self.allow_list:
                #    continue

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

    def _anonymize_texts_presidio(self, texts: List[str], operator_params: dict = None) -> List[str]:
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
        operator_params["slug_length"] = self.slug_length

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

    def detect_entities(self, texts: List[str]) -> List[dict]:
        """
        Detects entities in a list of texts and returns them in a format
        suitable for NER training data.
        """
        if not texts:
            return []

        # 1. Prepare list, skipping cache for fresh analysis
        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        
        unique_texts_to_process = sorted(list(set(t for t in original_texts if t)))

        if not unique_texts_to_process:
            return []

        # 2. Setup NLP model
        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang]

        # 3. Process in batches (GPU)
        docs = nlp_model.pipe(unique_texts_to_process, batch_size=500)
        
        results = []

        for doc in docs:
            original_doc_text = doc.text
            detected_entities = []

            # A. Detect with Transformer model
            for ent in doc.ents:
                normalized_label = ENTITY_MAPPING.get(ent.label_, ent.label_)
                detected_entities.append({
                    "start": ent.start_char, "end": ent.end_char,
                    "label": normalized_label, "score": 1.0
                })

            # B. Detect with compiled Regex
            for pat in self.compiled_patterns:
                for match in pat["regex"].finditer(original_doc_text):
                    detected_entities.append({
                        "start": match.start(), "end": match.end(),
                        "label": pat["label"], "score": pat["score"]
                    })

            # C. Resolve overlaps
            detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))
            
            merged_entities = []
            last_end = -1
            for ent in detected_entities:
                if ent["start"] >= last_end:
                    # Filter out preserved entities and allowed terms
                    if ent["label"] in self.entities_to_preserve:
                        continue
                    if original_doc_text[ent['start']:ent['end']] in self.allow_list:
                        continue
                    
                    merged_entities.append(ent)
                    last_end = ent["end"]

            # D. Format for NER training if entities were found
            if merged_entities:
                labels = [[ent['start'], ent['end'], ent['label']] for ent in merged_entities]
                results.append({"text": original_doc_text, "label": labels})
        
        return results
