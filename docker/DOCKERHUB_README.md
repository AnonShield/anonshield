# AnonLFI 3.0: Professional PII Pseudonymization Framework for CSIRTs

**Enterprise-grade pseudonymization framework designed for Cybersecurity Incident Response Teams (CSIRTs).** Resolves the conflict between data confidentiality (GDPR/LGPD compliance) and analytical utility using HMAC-SHA256 reversible pseudonyms. Features OCR pipeline, 24-language support, and Small Language Model (SLM) integration for context-aware anonymization.

## Container Architecture

| Tag | Base Image | Target Use Case | Size | Features |
|-----|------------|-----------------|------|----------|
| `latest` | `python:3.12-slim` | **CPU processing** - Works on any x86_64 machine | ~1.5GB | Full feature set, universal compatibility |
| `gpu` | `nvidia/cuda:12.8.0` | **GPU acceleration** - NVIDIA hardware only | ~6GB+ | GPU acceleration, CUDA 12.8 support |

## Hardware Requirements

### CPU Version (`latest` tag)
- **Any x86_64 processor**
- **4GB RAM minimum** (8GB+ recommended for large files)
- No GPU required

### GPU Version (`gpu` tag) 
- **NVIDIA GPU with Compute Capability ≥ 6.1** (Pascal architecture+)
- **8GB VRAM minimum** (16GB+ recommended for optimal performance)
- **8GB+ System RAM** (container + models require substantial memory)
- **NVIDIA Driver ≥ 525.60.11** (for CUDA 12.8 support)
- **NVIDIA Container Toolkit** (installation guide below)

**⚠️ GPU Compatibility:** Tested and verified only on RTX 5060 Ti (16GB VRAM) with Driver 590.48.01 on Ubuntu 24.04. Other modern NVIDIA GPUs should work but compatibility is not guaranteed.

## Quick Start

### CPU Mode (Universal)
```bash
# Basic anonymization
docker run --rm \
  -e ANON_SECRET_KEY="your-secure-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/document.txt

# Process entire directory
docker run --rm \
  -e ANON_SECRET_KEY="your-secure-key" \
  -v $(pwd)/documents:/data \
  kapelinsky/anon /data/
```

### GPU Mode (NVIDIA Only)
```bash
# GPU acceleration for transformer models
# ⚠️ CRITICAL: --gpus all flag is MANDATORY
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="your-secure-key" \
  -v $(pwd):/data \
  kapelinsky/anon:gpu /data/document.txt

# For systems with Docker runtime issues:
docker run --rm --runtime=nvidia --gpus all \
  -e ANON_SECRET_KEY="your-secure-key" \
  -v $(pwd):/data \
  kapelinsky/anon:gpu /data/document.txt

# RECOMMENDED: With model persistence (avoids redownloading 2-4GB every time)
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="your-secure-key" \
  -v $(pwd):/data \
  -v anon-models:/app/models \
  kapelinsky/anon:gpu /data/document.txt
```

Output files are saved to `/data/output/` by default.

## GPU Setup (NVIDIA Container Toolkit)

**Ubuntu/Debian Installation:**
```bash
# Add NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install and configure
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

**Troubleshooting GPU Issues:**
- **Error: "libnvidia-ml.so.1 not found"** → Install proprietary NVIDIA drivers (`sudo apt install nvidia-driver-xxx`)
- **Error: "--gpus all not supported"** → Use `--runtime=nvidia --gpus all` explicitly
- **Driver compatibility** → Run `nvidia-smi` and verify CUDA Version ≥ 12.8

## SLM Integration (Fully Automatic)

**AnonLFI automatically manages Ollama - no manual setup required!**

### Automatic LLM Management Features
- ✅ **Zero Configuration**: Just add `--slm-detector` flag
- ✅ **Auto-Start**: Automatically starts Ollama Docker container if not running
- ✅ **Auto-Download**: Downloads required models (llama3) on first use
- ✅ **Docker Integration**: Requires Docker socket access for container management
- ✅ **Model Persistence**: Downloaded models persist in Docker volumes
- ✅ **GPU Support**: Automatically uses GPU if available for Ollama

### SLM Usage Examples
```bash
# Auto-managed SLM detection (CPU mode)
docker run --rm \
  -e ANON_SECRET_KEY="your-key" \
  -v $(pwd):/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  kapelinsky/anon /data/report.txt --slm-detector

# Auto-managed SLM detection (GPU mode - fastest)
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="your-key" \
  -v $(pwd):/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  kapelinsky/anon:gpu /data/report.txt --slm-detector

# SLM entity analysis (generates detailed reports)
docker run --rm \
  -e ANON_SECRET_KEY="your-key" \
  -v $(pwd):/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  kapelinsky/anon /data/document.txt --slm-map-entities

# Full SLM anonymization (end-to-end AI processing)
docker run --rm \
  -e ANON_SECRET_KEY="your-key" \
  -v $(pwd):/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  kapelinsky/anon /data/complex.txt --anonymization-strategy slm
```

**How Auto-Management Works:**
1. **Detection**: System checks if Ollama is running on localhost:11434
2. **Auto-Start**: If not found, starts `ollama/ollama:latest` container with GPU support
3. **Model Download**: Downloads `llama3` model automatically (5-10 minutes first time)
4. **Ready**: SLM features become available immediately
5. **Persistence**: Models and container persist for subsequent runs

**Docker Socket Requirement:** SLM auto-management requires Docker socket access (`-v /var/run/docker.sock:/var/run/docker.sock`) to manage the Ollama container.

## Core Features

### File Format Support
**Preserves original structure for:**
- `.json`, `.jsonl` - JSON structure preserved
- `.xml` - XML hierarchy maintained
- `.csv`, `.xlsx` - Tabular data formatting
- `.pdf`, `.docx` - Document layout preserved
- `.txt` - Plain text processing

**OCR Image Processing:**
- Extracts text from images in PDF/DOCX files
- Supports standalone images: `.png`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`
- Uses Tesseract OCR with multilingual support

### Entity Detection (25+ Types)
**Personal Information:**
- `PERSON` - Names, `EMAIL_ADDRESS` - Emails, `PHONE_NUMBER` - Phone numbers
- `CREDIT_CARD` - Card numbers, `LOCATION` - Geographic locations

**Cybersecurity Indicators:**
- `IP_ADDRESS` - IPv4/IPv6 addresses, `URL` - Web addresses, `HOSTNAME` - Domain names
- `HASH` - MD5/SHA1/SHA256/SHA512, `MAC_ADDRESS` - Network MAC addresses
- `CVE_ID` - Vulnerability identifiers, `CPE_STRING` - Platform enumeration
- `UUID` - Unique identifiers, `CERT_SERIAL` - Certificate serials

**Technical Patterns:**
- `AUTH_TOKEN` - API keys/session tokens, `PGP_BLOCK` - PGP signatures
- `FILE_PATH` - System paths, `PASSWORD`/`USERNAME` - Contextual credentials

### Advanced Processing
**Anonymization Strategies:**
- `presidio` (default) - Full Microsoft Presidio pipeline with all recognizers
- `filtered` - Filtered scope Presidio pipeline (focused entity types)
- `hybrid` - Hybrid approach with custom replacement logic
- `standalone` - Zero Presidio dependencies, regex-based (fastest)
- `slm` - End-to-end LLM-based anonymization (experimental)

**Language Support (24 languages):**
English, Portuguese, Spanish, French, German, Italian, Chinese, Japanese, Korean, Russian, Polish, Dutch, Swedish, Norwegian, Danish, Finnish, Greek, Croatian, Lithuanian, Slovenian, Macedonian, Romanian, Ukrainian, Catalan

**Security & Consistency:**
- **HMAC-SHA256** pseudonym generation with secret key
- **Reversible anonymization** - same entity = same pseudonym
- **Controlled de-anonymization** with secret key protection
- **Configurable slug length** (1-64 characters)

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANON_SECRET_KEY` | **YES** | HMAC-SHA256 secret key for pseudonym generation | - |
| `ANON_LAZY_LOADING` | No | Download models on first use (automatic) | `1` |
| `ANON_PRELOAD` | No | Pre-download specific models on startup | - |
| `OLLAMA_BASE_URL` | No | Ollama service URL (for manual Ollama) | `http://ollama:11434` |

## Model Persistence (CRITICAL for Production)

**⚠️ WITHOUT PERSISTENT VOLUMES, MODELS REDOWNLOAD EVERY TIME (2-4GB each run)**

### Essential Volumes
| Mount Path | Purpose | Size Impact | Required |
|------------|---------|-------------|----------|
| `/app/models` | **AI Model Cache** - spaCy + Transformer models | 2-4GB | ✅ **CRITICAL** |
| `/app/db` | **Entity Database** - Anonymization mappings | <100MB | ✅ **For de-anonymization** |
| `/app/output` | **Results** - Anonymized files | Variable | ✅ **Recommended** |
| `/var/run/docker.sock` | **Docker Socket** - SLM container management | - | Only for SLM |

### Model Download Process
**First Run (without volumes):**
1. Downloads spaCy model (400MB+)
2. Downloads transformer model (1-2GB)
3. Caches in `/app/models`
4. **Total: 5-10 minutes download time**

**Subsequent Runs (with persistent volumes):**
1. Uses cached models instantly
2. **Total: 0 seconds download time**

## Complete Usage Examples

### File Processing
```bash
# Single file with language selection
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/incident.pdf --lang pt

# Directory processing with custom output
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd)/input:/data \
  -v $(pwd)/anonymized:/output \
  kapelinsky/anon /data/ --output-dir /output

# Preserve specific entity types
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/logs.json --preserve-entities "HOSTNAME,IP_ADDRESS"
```

### Performance Optimization
```bash
# Fast processing with optimization
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/large_dataset/ --optimize

# Custom slug length for readability
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/report.txt --slug-length 8

# GPU with persistent storage
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  -v anon-models:/app/models \
  -v anon-db:/app/db \
  kapelinsky/anon:gpu /data/documents/
```

### Advanced Configuration
```bash
# Custom anonymization config for JSON/XML
docker run --rm \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  -v $(pwd)/config.json:/app/config.json \
  kapelinsky/anon /data/structured.json --anonymization-config /app/config.json

# Generate NER training data (no secret key needed)
docker run --rm \
  -v $(pwd):/data \
  kapelinsky/anon /data/corpus/ --generate-ner-data --output-dir /data/ner_output/

# Cybersecurity-focused model with hybrid strategy
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="production-key" \
  -v $(pwd):/data \
  kapelinsky/anon:gpu /data/threat_intel.json \
  --transformer-model attack-vector/SecureModernBERT-NER \
  --anonymization-strategy hybrid
```

## Resource Requirements

**Memory Usage:**
```
CPU Mode:  4-8GB RAM (base container + models)
GPU Mode:  8-16GB RAM + 4-8GB VRAM (container + CUDA libraries + models)
SLM Mode:  Additional 4-32GB depending on Ollama model size
```

**When to Use GPU:**
- ✅ Processing transformer-based NER models
- ✅ Large document batches
- ✅ High-volume processing pipelines
- ❌ Single small files
- ❌ Regex-only anonymization (no transformers)

## Common CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--lang LANG` | Document language (24 supported) | `--lang pt` |
| `--output-dir DIR` | Output directory path | `--output-dir /data/results` |
| `--preserve-entities TYPES` | Skip anonymizing specific types | `--preserve-entities "HOSTNAME,URL"` |
| `--allow-list TERMS` | Never anonymize specific terms | `--allow-list "CompanyName,ProductX"` |
| `--slug-length N` | Pseudonym length (1-64 chars) | `--slug-length 12` |
| `--anonymization-strategy S` | Processing strategy | `--anonymization-strategy filtered` |
| `--transformer-model MODEL` | NER model selection | `--transformer-model attack-vector/SecureModernBERT-NER` |
| `--optimize` | Enable all performance optimizations | `--optimize` |
| `--slm-detector` | Use SLM for enhanced entity detection | `--slm-detector` |
| `--slm-map-entities` | Generate entity analysis reports | `--slm-map-entities` |
| `--generate-ner-data` | Create NER training data | `--generate-ner-data` |
| `--list-entities` | Show all supported entity types | `--list-entities` |
| `--list-languages` | Show all supported languages | `--list-languages` |

Full documentation: `docker run --rm kapelinsky/anon --help`

## Production Deployment

### Recommended Production Setup
```bash
# STEP 1: Create persistent volumes (MANDATORY to avoid redownloads)
docker volume create anon-models     # Stores 2-4GB of AI models
docker volume create anon-db         # Stores anonymization mappings  
docker volume create anon-output     # Stores processed files

# STEP 2: Production deployment with persistent storage
docker run -d \
  --name anon-production \
  --gpus all \
  --restart unless-stopped \
  -e ANON_SECRET_KEY="$(cat /secure/anon.key)" \
  -v anon-models:/app/models \
  -v anon-db:/app/db \
  -v anon-output:/app/output \
  -v /data/input:/app/input:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  kapelinsky/anon:gpu \
  /app/input/ --optimize --slm-detector

# STEP 3: Monitor first run (downloads models, takes 5-10 minutes)
docker logs -f anon-production

# Subsequent runs will be instant (uses cached models)
```

**⚠️ Production Warning:** Without persistent volumes (`-v anon-models:/app/models`), the container will redownload 2-4GB of AI models on every restart, causing significant delays and bandwidth usage.

### Security Best Practices
- **Never hardcode** `ANON_SECRET_KEY` in commands
- **Use Docker secrets** or external key management
- **Mount input data read-only** (`-v /data:/app/input:ro`)
- **Regular backups** of `/app/db` volume for de-anonymization capability
- **Network isolation** in production environments

## Source Code & Support

- **GitHub Repository:** [github.com/AnonShield/AnonLFI3.0](https://github.com/AnonShield/AnonLFI3.0)
- **License:** Open source (see repository for details)
- **Docker Hub:** [hub.docker.com/r/kapelinsky/anon](https://hub.docker.com/r/kapelinsky/anon)

**Supported Entity Types:** 25+ including PERSON, ORGANIZATION, EMAIL_ADDRESS, IP_ADDRESS, CVE_ID, HASH, UUID, and more cybersecurity-focused patterns.

**Supported Languages:** English, Portuguese, Spanish, French, German, Italian, Chinese, Japanese, Korean, Russian, Polish, Dutch, Swedish, Norwegian, Danish, Finnish, Greek, Croatian, Lithuanian, Slovenian, Macedonian, Romanian, Ukrainian, Catalan.