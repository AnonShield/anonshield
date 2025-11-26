# Anonymization Flow: A Deep Dive

This document describes in detail the processing flow for each file type supported by the anonymization tool. The architecture is based on the **Template Method** design pattern, where a base class (`FileProcessor`) defines the algorithm's skeleton, and specialized subclasses implement the specific extraction and reconstruction details for each format.

## Architecture and Core Components

The system is composed of three main layers that work together.

```mermaid
graph TD
    A[Input: File] --> B{1. File Processing Layer (processors.py)};
    B -- Extracts Texts --> C{2. Orchestration Layer (engine.py)};
    C -- Detects & Anonymizes PII --> D[3. Analysis & Storage Layer (Presidio & DB)];
    C -- Returns Anonymized Text --> B;
    B -- Reconstructs & Saves File --> E[Output: Anonymized File];

    subgraph "1. File Processors"
        B;
        direction LR;
        P_JSON(JsonFileProcessor);
        P_XML(XmlFileProcessor);
        P_CSV(CsvFileProcessor);
        P_PDF(PdfFileProcessor);
        P_DOCX(DocxFileProcessor);
        P_TXT(TextFileProcessor);
    end

    subgraph "2. Orchestrator and Strategies"
        C;
        direction LR;
        S_Presidio(Presidio Strategy);
        S_Balanced(Balanced Strategy);
        S_Fast(Fast Strategy);
        S_Forced(Forced Strategy);
    end
    
    subgraph "3. Analysis and Persistence"
        D;
        direction LR;
        M_Spacy[spaCy Models];
        M_Trf[Transformer Model];
        M_Regex[Custom Regex];
        DB[(Database)];
    end
```

1.  **`FileProcessor` (Base Class):** Orchestrates the main flow. Its responsibility is to open the file, call the extraction method, manage batch processing, and call the reconstruction/saving method.
2.  **`AnonymizationOrchestrator`:** The brain of the anonymization. It doesn't know about files, only about text. It receives batches of text, decides which anonymization strategy to use (`presidio`, `fast`, `balanced`), and invokes the Presidio engines for detection and substitution.
3.  **`CustomSlugAnonymizer`:** A custom Presidio operator. When the Presidio `AnonymizerEngine` finds PII, it calls this operator, which generates a secure "slug" (e.g., `[PERSON_a1b2c3]`) using an HMAC-SHA256 hash of the original text. This ensures that "John Doe" is always replaced by the same slug, maintaining referential consistency. The full hash is stored in a SQLite database to allow for future de-anonymization.

---

## The Heart of the Process: Decision and Anonymization Logic

### A. The Gatekeeper: `_should_anonymize()`

This method in the `FileProcessor` class acts as a gatekeeper, deciding if a piece of text is worth sending for the costly PII analysis. For structured files (JSON, XML), it also receives the data's "path" (e.g., `asset.tags[0].value`).

The decision flow is as follows:
1.  **Exclusion Check (`fields_to_exclude`):** If the path is on the exclusion list, the process stops. **This is the highest priority rule.**
2.  **Forced Anonymization Check (`force_anonymize`):** If the path is mapped here, it's flagged for anonymization with a specific entity type, bypassing text filters.
3.  **Text Filters:** The text is inspected (length, numeric content, stop-words). If it fails, the process stops.
4.  **Mode Logic (Explicit vs. Implicit):** In explicit mode (if `fields_to_anonymize` exists), a text only proceeds if its path is explicitly listed. In implicit mode, any text that passes the filters continues.

### B. The Orchestrator and Its Strategies

Once `_should_anonymize` gives the green light, the `AnonymizationOrchestrator` takes over, using one of three main strategies:

#### `presidio` Strategy (The Comprehensive One)
- **How it works:** Uses the Presidio `AnalyzerEngine` to its full potential. It invokes **all** available recognizers: the **Transformer model + spaCy** pipeline, the **custom Regex** list, and **dozens of Presidio's built-in recognizers** (for passports, driver's licenses, etc.). The results from all these sources are then aggregated by a sophisticated logic to resolve conflicts and determine the best entity.
- **Pro:** Highest accuracy and broadest detection capability.
- **Con:** Slower due to the extensive analysis and complex aggregation.

#### `fast` Strategy (The Quick One)
- **How it works:** Completely bypasses the `AnalyzerEngine`. It runs a direct, manual pipeline:
    1. Passes the text through the **spaCy + Transformer** pipeline (as configured by Presidio's `TransformersNlpEngine`).
    2. In parallel, passes the text through the **custom Regex** list.
    3. Uses a simpler merge logic (`_merge_overlapping_entities`) to combine the results from both sources.
    4. Reconstructs the text manually without the `AnonymizerEngine`'s full pipeline.
- **Pro:** Significantly faster by eliminating the overhead of the `AnalyzerEngine` and its multiple internal recognizers.
- **Con:** Less robust in resolving entity conflicts and does not benefit from the full range of Presidio's additional recognizers.

#### `balanced` Strategy (NEW! Optimal Balance)
- **How it works:** This strategy offers a smart middle ground. It *uses* the Presidio `AnalyzerEngine` (thus benefiting from its more robust result aggregation logic than `fast` mode), but it invokes it selectively. Instead of using all recognizers, it instructs the engine to use **only** the main **spaCy + Transformer** pipeline and the **custom Regex** list, effectively disabling Presidio's other built-in recognizers.
- **Pro:** Offers an ideal balance, being faster than `presidio` (by ignoring many internal recognizers) and more robust than `fast` (by using Presidio's superior aggregation logic).
- **Con:** May not detect very specific entities that only the full `presidio` strategy would cover.

### C. How Text Reaches the Transformer: The Tokenization Process

The Transformer model processes a numerical representation of text, created through a crucial step called **tokenization**.

Imagine the text: `"My name is John and I live in São Paulo."`

1.  **Breaking into Tokens:** The text is broken into "sub-words" (e.g., "São Paulo" -> `['ĠS', 'ão', 'ĠPaulo']`), allowing the model to handle unknown words.
2.  **Addition of Special Tokens:** Tokens like `<s>` (start) and `</s>` (end) are added.
3.  **Conversion to IDs:** Each token is mapped to an integer from the model's vocabulary.
4.  **Creation of the Attention Mask:** A list of `1`s and `0`s tells the model which tokens are real and should be considered.

The resulting numerical structure (`input_ids` and `attention_mask`) is what is effectively passed to the Transformer's neural network.

---

## Detailed Flow by File Type

The general flow of **Collect -> Batch Anonymize -> Reconstruct** applies to all. The difference lies in how each processor implements the collection and reconstruction.

### 1. `TextFileProcessor` and `ImageFileProcessor`
- **Logic:** Simple and direct. Extracts all text (either from lines in a `.txt` file or via OCR from an image) and saves it to a new, anonymized `.txt` file.

### 2. `DocxFileProcessor` and `PdfFileProcessor`
- **Logic:** Complex extraction with simple reconstruction.
- **Challenge:** Extracting text in the correct order, especially from embedded images (DOCX) and complex layouts (PDF).
- **Solution:** The `PdfFileProcessor` excels with its **spatial sorting**. It extracts the text and coordinates of each block and image, then re-sorts them from top-to-bottom and left-to-right to simulate human reading before sending for anonymization. The result is a single `.txt`.

### 3. `CsvFileProcessor` and `XlsxFileProcessor`
- **Logic:** Preservation of tabular structure via a translation map.
- **Flow:**
    1.  **Collection and Deduplication:** Collects all **unique** text values from the file that need anonymization.
    2.  **Map Creation:** The unique values are anonymized, creating a dictionary that maps the original to the anonymized version: `{"John Doe": "[PERSON_...]"}`.
    3.  **Map Application:** Iterates over the file again, replacing all occurrences of the original values with their anonymized counterparts from the map.
    4.  A new CSV/XLSX file is saved, keeping the structure intact.

### 4. `XmlFileProcessor` and `JsonFileProcessor`
- **Logic:** Preservation of hierarchy through data tree analysis and reconstruction.
- **Flow:**
    1.  **Parsing and Path-Aware Collection:** The file is parsed into a tree. The processor traverses the tree and collects all texts that need anonymization, storing not just the text, but also its **path** (`.`-notation for JSON, XPath for XML).
    2.  **Grouping and Translation Map:** The texts are grouped (by path or forced entity type) and sent to create a translation map.
    3.  **Object Reconstruction:** The code traverses the original tree a second time, using the map to replace the values in their exact locations.
    4.  The new, anonymized object/tree is saved, perfectly preserving the original structure.
- **Optimization (XML):** To handle many small fields, the `XmlFileProcessor` collects *all* relevant texts from the entire document into a single list and sends it as a single batch for anonymization.
- **Optimization (JSON):** Uses a **Hybrid Mode** for large files (>100MB), processing them in streaming mode (`ijson` for arrays, line-by-line for `.jsonl`) to avoid excessive memory consumption.

---

## Special Operation Modes and Optimizations

### NER Data Generation Mode (`--generate-ner-data`)
- **Goal:** Instead of anonymizing, generates data to train NLP models.
- **Optimization:** To efficiently analyze thousands of small texts, the `_run_ner_pipeline` method **joins them into a single giant string**, using the ` . ||| . ` delimiter as "glue". This single string is processed all at once by the model, maximizing performance. This concatenation technique is used **exclusively** in this mode.