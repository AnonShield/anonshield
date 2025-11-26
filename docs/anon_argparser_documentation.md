## anon.py Argument Documentation

This document outlines the command-line arguments for `anon.py`, providing a high-level description for each, its purpose, and how it influences the script's behavior.

### Positional Argument

#### `file_path`
*   **Description**: Specifies the absolute or relative path to the input data. This can be either a single file (e.g., text, JSON, CSV, XLSX, XML) or a directory containing multiple files. The script will automatically detect the file type and apply the appropriate processing logic. If a directory is provided, `anon.py` will recursively process all supported files within it. This argument is optional if `--list-entities` or `--list-languages` is used.
*   **Default**: None (required unless listing entities or languages)

### Mode Selection

#### `--generate-ner-data`
*   **Description**: When this flag is enabled, the script operates in NER (Named Entity Recognition) data generation mode instead of performing anonymization. In this mode, the output files will contain annotations of detected entities, formatted for training or evaluation of NER models, rather than redacted content. This is useful for building custom datasets for domain-specific NER tasks.
*   **Type**: Boolean flag
*   **Default**: `False` (anonymization is the default mode)

### General Options

#### `--list-entities`
*   **Description**: This flag instructs the script to print a comprehensive list of all supported entity types (e.g., PERSON, ORGANIZATION, LOCATION, DATE) that `anon.py` can detect and process. After displaying the list, the script will exit. This is useful for understanding the capabilities of the entity recognition engine and for configuring arguments like `--preserve-entities`.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--list-languages`
*   **Description**: This flag causes the script to display a list of all human languages it supports for processing, along with their respective two-letter ISO 639-1 codes (e.g., `en: English`, `pt: Portuguese`). The script will then exit. This helps users identify the correct `--lang` code for their input data.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--lang`
*   **Description**: Sets the primary language of the input document(s). This is crucial for selecting the correct underlying spaCy and Transformer models for accurate language-specific entity recognition. Using the wrong language may lead to poor detection performance. The value should be a two-letter ISO 639-1 language code.
*   **Type**: String
*   **Default**: `en` (English)

#### `--output-dir`
*   **Description**: Specifies the directory where all processed output files will be saved. If the directory does not exist, `anon.py` will attempt to create it. Processed files retain their original filenames but are saved within this specified output location.
*   **Type**: String
*   **Default**: `output`

#### `--overwrite`
*   **Description**: When this flag is present, the script is permitted to overwrite existing files in the `--output-dir` that have the same name as the generated output files. If this flag is not set and an output file with the same name already exists, the script will typically append a timestamp or a numerical suffix to avoid data loss, or in some cases, skip processing to prevent accidental overwrites.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--no-report`
*   **Description**: Disables the generation of a performance report. By default, `anon.py` creates a summary report in the `logs` directory after processing, detailing metrics such as processing time and the number of entities handled. This flag can be used to suppress report generation, for instance, in automated workflows where such reports are not needed.
*   **Type**: Boolean flag
*   **Default**: `False`

### Anonymization Options

#### `--preserve-entities`
*   **Description**: Allows the user to specify a comma-separated list of entity types that should *not* be anonymized. For example, `--preserve-entities PERSON,DATE` would ensure that all detected `PERSON` and `DATE` entities remain in the output, while other sensitive entities are redacted. Entity names should match those listed by `--list-entities`. Case-insensitivity is typically handled by the script.
*   **Type**: String
*   **Default**: `""` (no entities preserved by default)

#### `--allow-list`
*   **Description**: Provides a comma-separated list of specific terms or phrases that should explicitly *not* be anonymized, even if they are detected as sensitive entities. This is useful for ensuring that legitimate business names, project codes, or other non-sensitive terms that might be mistakenly identified by the NER models are retained in the output. The terms are matched in a case-insensitive manner.
*   **Type**: String
*   **Default**: `""` (no terms allowed by default)

#### `--slug-length`
*   **Description**: Defines the desired length of the anonymized "slug" or replacement string generated for each redacted entity. The slug is a consistent, non-identifying substitute for sensitive information. A longer slug might offer more robust anonymization by making reverse engineering harder, while a shorter one might be preferred for brevity. The length must be an integer between 1 and 64 characters.
*   **Type**: Integer
*   **Range**: 1-64
*   **Default**: `None` (the system determines an appropriate default length)

#### `--anonymization-config`
*   **Description**: Specifies the file path to a JSON configuration file that defines advanced, fine-grained anonymization rules, especially for structured data formats like JSON, CSV, or XML. This configuration can dictate which specific fields to include/exclude, specify custom anonymization strategies for certain data types, or define complex redaction patterns beyond standard entity detection.
*   **Type**: String (path to JSON file)
*   **Default**: `None`

### Performance & Filtering Options

#### `--preserve-row-context`
*   **Description**: Specifically for structured files like CSV or XLSX, enabling this flag ensures that all values within each row are processed individually for anonymization, even if a value appears identical in multiple rows. This approach guarantees that the context of each data point within its row is fully considered, potentially leading to more accurate anonymization but at the cost of increased processing time and resource usage due to redundant processing of identical values. If disabled, unique values might be processed once and then mapped, which is faster but could lose subtle contextual nuances.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--json-stream-threshold-mb`
*   **Description**: Sets a size threshold (in megabytes) for JSON files. Any JSON file exceeding this size will be processed using a streaming approach, where data is read and processed in chunks rather than loading the entire file into memory. This prevents Out-of-Memory (OOM) errors when dealing with very large JSON datasets. For smaller files, in-memory processing might be faster.
*   **Type**: Integer
*   **Default**: `ProcessingLimits.JSON_STREAM_THRESHOLD_MB` (e.g., 500 MB)

#### `--optimize`
*   **Description**: This is a convenience flag that activates a set of pre-configured optimizations for faster processing. When `--optimize` is used, the script will automatically set the `anonymization-strategy` to `"fast"`, configure the `db-mode` to `"in-memory"`, enable the `use-cache` option, and set `min-word-length` to `3` (if it was previously 0). This is ideal for scenarios where speed is critical and a slight trade-off in exhaustive analysis is acceptable.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--use-cache`
*   **Description**: Enables an in-memory caching mechanism for anonymization results. When active, the script stores previously processed entities and their corresponding anonymized slugs in a cache. If the same entity is encountered again, its anonymized form is retrieved from the cache instead of reprocessing it, significantly speeding up performance for repetitive data, particularly in large datasets.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--max-cache-size`
*   **Description**: Defines the maximum number of items (unique entities and their anonymized forms) that the in-memory cache can store. Once this limit is reached, older or less frequently accessed items may be evicted to make space for new entries, following a Least Recently Used (LRU) or similar caching policy. A larger cache size can improve hit rates but consumes more memory.
*   **Type**: Integer
*   **Default**: `ProcessingLimits.MAX_CACHE_SIZE` (e.g., 100000)

#### `--min-word-length`
*   **Description**: Specifies the minimum character length a word must have to be considered for processing and potential anonymization. Words shorter than this length will be ignored by the entity detection and anonymization logic. This can help filter out very short, often non-PII terms, reducing processing overhead and false positives, especially when combined with `--optimize`.
*   **Type**: Integer
*   **Default**: `0` (no minimum length, all words processed)

#### `--technical-stoplist`
*   **Description**: Allows the user to provide a comma-separated list of custom technical terms or common words that should be explicitly ignored during the anonymization process. These words will be added to an internal "stoplist" alongside any predefined technical terms. This prevents the script from attempting to anonymize terms that are common in the input data but are not sensitive.
*   **Type**: String
*   **Default**: `""` (no custom stoplist terms)

#### `--skip-numeric`
*   **Description**: When enabled, strings that consist solely of numeric characters (e.g., "12345", "9876543210") will be exempt from anonymization. By default, numeric strings are treated like any other text and anonymized if they match an entity pattern (e.g., a phone number). This flag is useful if numeric identifiers in the data are not considered PII and should be preserved.
*   **Type**: Boolean flag
*   **Default**: `False` (numeric strings can be anonymized)

#### `--anonymization-strategy`
*   **Description**: Selects the overall approach or "strategy" for anonymizing content.
    *   `presidio`: Utilizes a comprehensive, model-based approach, leveraging the full power of the Presidio library for highly accurate and contextual entity detection. This is generally the most accurate but can be slower.
    *   `fast`: Employs an optimized, potentially rule-based or simplified model approach, prioritizing speed over exhaustive accuracy. This is suitable for large volumes of data where a balance between performance and reasonable anonymization is desired.
    *   `balanced`: Aims for a middle ground, combining elements of both `presidio` and `fast` strategies to offer a good blend of accuracy and performance.
*   **Type**: String (choice)
*   **Choices**: `presidio`, `fast`, `balanced`
*   **Default**: `presidio`

#### `--regex-priority`
*   **Description**: When set, this flag ensures that custom regular expression (regex) recognizers take precedence over model-based entity detectors. If a custom regex matches a segment of text, that match will be used for anonymization, and the model-based detectors will not override it. This provides explicit control for specific patterns that require deterministic handling.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--db-mode`
*   **Description**: Determines how the internal database, used for tracking anonymized entities and their mappings, operates.
    *   `persistent`: The database is stored on disk within the `--db-dir`. This allows anonymization mappings to persist across multiple runs, ensuring consistency if the same input data is processed at different times, or if the anonymized IDs need to be stable.
    *   `in-memory`: The database resides entirely in RAM and is discarded once the script finishes execution. This offers faster performance by avoiding disk I/O but means that anonymization mappings are not saved. Ideal for single, self-contained processing tasks.
*   **Type**: String (choice)
*   **Choices**: `persistent`, `in-memory`
*   **Default**: `persistent`

#### `--db-dir`
*   **Description**: Specifies the directory where the persistent database file will be stored when `db-mode` is set to `persistent`. If `db-mode` is `in-memory`, this argument is ignored. The directory will be created if it does not exist.
*   **Type**: String
*   **Default**: `db`

#### `--disable-gc`
*   **Description**: Disables Python's automatic garbage collection mechanism during the processing phase. While garbage collection helps manage memory, it can introduce pauses that impact performance, especially for very large, single files. Disabling it may lead to a speed boost for specific high-memory tasks but requires careful consideration as it can also increase overall memory footprint and potentially lead to OOM errors if not enough memory is available.
*   **Type**: Boolean flag
*   **Default**: `False`

#### `--db-synchronous-mode`
*   **Description**: Controls the SQLite `synchronous` PRAGMA setting for the internal database. This setting dictates how much data is written to the physical disk before returning from a `COMMIT` operation, influencing durability and performance.
    *   `OFF`: Data is not necessarily written to disk before `COMMIT` returns, offering the highest performance but risking data loss upon system crash.
    *   `NORMAL`: `fsync` operations are deferred, providing a good balance between performance and durability for most applications.
    *   `FULL`: All content is safely written to disk before `COMMIT` returns, ensuring maximum data integrity but with lower performance.
    *   `EXTRA`: Similar to `FULL` but with additional integrity checks, further impacting performance.
    This option overrides any `synchronous` setting in the configuration file.
*   **Type**: String (choice)
*   **Choices**: `OFF`, `NORMAL`, `FULL`, `EXTRA`
*   **Default**: `None` (uses the default or configured value, often `NORMAL`)

#### `--log-level`
*   **Description**: Sets the verbosity level for the script's logging output. This controls which types of messages (e.g., debug, info, warning, error, critical) are displayed in the console or logs.
    *   `DEBUG`: Most verbose, shows detailed internal events for debugging.
    *   `INFO`: General information about the script's progress and significant events.
    *   `WARNING`: Indicates potential issues that don't prevent the script from running.
    *   `ERROR`: Signals errors that prevent certain operations from completing.
    *   `CRITICAL`: Most severe errors, often leading to program termination.
*   **Type**: String (choice)
*   **Choices**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
*   **Default**: `WARNING`

#### `--force-large-xml`
*   **Description**: This flag bypasses internal memory safety checks for XML files. XML files, especially malformed or extremely large ones, can consume significant memory when parsed entirely. Enabling this flag forces the script to attempt processing even if the file exceeds recommended memory limits. Users should exercise extreme caution, as this can lead to Out-of-Memory (OOM) errors, system instability, or crashes if the system lacks sufficient RAM to handle the XML document.
*   **Type**: Boolean flag
*   **Default**: `False`

### Chunking and Batching Options

These arguments are grouped to manage how large inputs are divided and processed to optimize memory usage and performance, especially for large files or directories.

#### `--batch-size`
*   **Description**: Defines the default number of text chunks or units of work that are processed together in a single batch. This applies generally to text processing operations where the input can be segmented. Adjusting this value can impact memory consumption and throughput; a larger batch size might utilize hardware more efficiently but require more RAM.
*   **Type**: Integer
*   **Default**: `DefaultSizes.BATCH_SIZE` (e.g., 1000)

#### `--csv-chunk-size`
*   **Description**: Specifically for CSV (Comma Separated Values) files, this argument controls the number of rows read into memory at once when using the pandas library for processing. For very large CSVs, processing in chunks (e.g., 10,000 or 100,000 rows at a time) is essential to prevent memory exhaustion, as the entire file does not need to be loaded simultaneously.
*   **Type**: Integer
*   **Default**: `DefaultSizes.CSV_CHUNK_SIZE` (e.g., 10000)

#### `--json-chunk-size`
*   **Description**: Used when streaming large JSON arrays. This argument specifies the number of JSON objects or elements that are processed as a single chunk from the input stream. This helps manage memory when `json-stream-threshold-mb` is exceeded, preventing the loading of the entire JSON structure into RAM.
*   **Type**: Integer
*   **Default**: `DefaultSizes.JSON_CHUNK_SIZE` (e.g., 1000)

#### `--ner-chunk-size`
*   **Description**: Sets the maximum character length for text segments used during NER (Named Entity Recognition) data generation. When generating NER data, input texts might be broken down into chunks of this size to fit within model context windows or to optimize processing. Longer texts are split, and each chunk is processed independently.
*   **Type**: Integer
*   **Default**: `DefaultSizes.NER_CHUNK_SIZE` (e.g., 2000)

#### `--nlp-batch-size`
*   **Description**: Specifies the batch size for spaCy's `nlp.pipe()` method, which is used for efficient processing of multiple documents or text segments. This defines how many documents spaCy's language model processes concurrently before yielding results. Optimizing this value can significantly affect the performance of the underlying NLP pipeline.
*   **Type**: Integer
*   **Default**: `DefaultSizes.NLP_BATCH_SIZE` (e.g., 1000)