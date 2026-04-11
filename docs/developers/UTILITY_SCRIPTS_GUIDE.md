# Utility Scripts Guide

This document provides an overview of the utility scripts located in the `scripts/` directory. These scripts support core tasks such as de-anonymization and database management.

## Table of Contents
- [Database & Core Function Scripts](#database--core-function-scripts)
  - [`deanonymize.py`](#deanonymizepy)
  - [`export_and_clear_db.py`](#export_and_clear_dbpy)
- [Experimental Scripts](#experimental-scripts)
  - [`slm_regex_generator.py`](#slm_regex_generatorpy)

---

## Database & Core Function Scripts

These scripts interact directly with the anonymization engine's database.

### `deanonymize.py`

- **Purpose:** Reverses the anonymization for a single entity slug. It queries the `entities.db` database to find the original text corresponding to a given slug. This script requires the `ANON_SECRET_KEY` environment variable to be set.
- **Arguments:**
  - `slug`: (Required) The anonymized slug to look up (e.g., `[PERSON_a1b2c3d4]`).
  - `--db-dir`: The directory where the `entities.db` file is located. Default: `db`.
- **Usage:**
  ```bash
  export ANON_SECRET_KEY='your-secret'
  uv run scripts/deanonymize.py "[PERSON_a1b2c3d4]"
  ```

### `export_and_clear_db.py`

- **Purpose:** Exports all records from the `entities.db` file into a CSV file. It includes an option to wipe the database after export.
- **Arguments:**
  - `--clear`: If present, deletes all records from the database after export.
- **Usage:**
  ```bash
  # Export only
  uv run scripts/export_and_clear_db.py

  # Export and clear
  uv run scripts/export_and_clear_db.py --clear
  ```

---

## Experimental Scripts

### `slm_regex_generator.py`

- **Purpose:** [Experimental] Automates regular expression creation. It takes an entity map file (generated via `--slm-map-entities`), groups entities by type, and uses an SLM to suggest regex patterns.
- **Arguments:**
  - `file_path`: (Required) Path to the entity map `.json` or `.jsonl` file.
  - `--output-file`: Path to save the output JSON report. Default: `slm_regex_report.json`.
- **Usage:**
  ```bash
  uv run scripts/slm_regex_generator.py output/my_entity_map.jsonl
  ```
