# AnonShield: Scalable On-Premise Pseudonymization

AnonShield is a pseudonymization framework designed for secure and compliant data sharing. It replaces Personally Identifiable Information (PII) and sensitive indicators with cryptographically secure, deterministic pseudonyms (HMAC-SHA256), preserving referential integrity across documents while ensuring GDPR/LGPD compliance.

## Key Features

- **Multi-Format Support**: Process JSON, CSV, XML, PDF, DOCX, XLSX, and plain text.
- **GPU-Accelerated NER**: Fast entity detection using state-of-the-art transformer models.
- **Scalable Architecture**: O(n) streaming processors for handling large files (tested up to 550 MB+).
- **Referential Integrity**: Uses HMAC-SHA256 to ensure the same entity always receives the same pseudonym across different files and runs.
- **Schema-Aware Configuration**: Fine-grained control over which fields to anonymize in structured files.
- **On-Premise**: Process sensitive data entirely locally without external API dependencies.

## Installation

### Local Setup (Linux)

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and Install**:
   ```bash
   git clone https://github.com/AnonShield/tool.git
   cd tool
   uv sync
   ```

3. **Set your Secret Key**:
   ```bash
   export ANON_SECRET_KEY=$(openssl rand -hex 32)
   ```

### Docker (Recommended)

Run AnonShield without installing Python dependencies:

```bash
chmod +x run.sh
export ANON_SECRET_KEY=$(openssl rand -hex 32)
./run.sh ./your_file.csv
```

## Quick Start

Anonymize a file using the default settings:

```bash
uv run anon.py path/to/your/file.txt
```

List all supported entity types:

```bash
uv run anon.py --list-entities
```

## Usage & Configuration

Detailed guides are available in the `docs/` directory:

- [CLI Reference](docs/users/CLI_REFERENCE.md)
- [Architecture Overview](docs/developers/ARCHITECTURE.md)
- [Anonymization Strategies](docs/developers/ANONYMIZATION_STRATEGIES.md)
- [SLM Integration Guide](docs/developers/SLM_INTEGRATION_GUIDE.md)

## Security

- **Deterministic**: Pseudonyms are derived from your `ANON_SECRET_KEY`. Keep this key safe to maintain (or regain) the ability to de-anonymize data.
- **Local-Only**: No data leaves your machine. All detection and processing happen strictly on-premise.

## License

This project is licensed under the **GNU General Public License v3.0**.
