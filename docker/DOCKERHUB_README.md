# AnonShield: PII Pseudonymization for CSIRTs

AnonShield lets Computer Security Incident Response Teams share incident data without leaking personal data. It replaces PII and cybersecurity indicators (names, emails, IPs, CVEs, hashes, URLs, and more) with deterministic HMAC-SHA256 pseudonyms, so the same value always maps to the same pseudonym and your JSON, XML, and CSV files keep their structure. It is multilingual, ships with Tesseract OCR for scanned documents, and adds custom cybersecurity recognizers on top of standard NER. Everything runs on-premise, and the substitution is reversible as long as you keep the local mapping database.

[![Best Artifact at SBRC 2026](https://img.shields.io/badge/SBRC%202026-Best%20Artifact-gold)](https://doc-artefatos.github.io/sbrc2026/results.html)

> Selected **Best Artifact** at SBRC 2026 ([official results](https://doc-artefatos.github.io/sbrc2026/results.html)). Source code, documentation, and research artifact: [github.com/AnonShield/anonshield](https://github.com/AnonShield/anonshield).

![AnonShield pipeline](https://anonshield.org/pipeline.png)

> **Prefer a browser?** A hosted web app with the same engine runs at **[anonshield.org](https://anonshield.org)**: drag and drop a file, choose entity types and a strategy, and watch a live metrics dashboard. The Docker image documented below is the command-line tool.

![AnonShield web interface](https://anonshield.org/ui-app.png)

---

## Why AnonShield

* **Deterministic and reversible.** Identical values always map to the same pseudonym, so cross-references survive anonymization. With the mapping database you can de-anonymize later; without it, the output is irreversible.
* **Structure-preserving.** JSON, XML, and CSV stay valid and keep their schema. Only the sensitive values change.
* **Security-aware.** Beyond standard PII, it recognizes IPs, CVEs, hashes, URLs, hostnames, MAC addresses, certificates, and more (full list below).
* **Multilingual with OCR.** Handles many languages and reads scanned PDFs and images via Tesseract.
* **Fully on-premise.** No data leaves your machine. The only external network call is the one-time model download on first run.

---

## Quick Start

**The only prerequisite is Docker.** Install it for your OS: [Linux](https://docs.docker.com/engine/install/) | [macOS](https://docs.docker.com/desktop/setup/install/mac-install/) | [Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Everything else is included in your operating system. A small wrapper script handles `docker run`, volume mounts, and path mapping for you, so you never type a raw `docker run` command.

### Step 1: Download the wrapper script

**Linux / macOS** (open a terminal):
```bash
curl -fsSL https://raw.githubusercontent.com/AnonShield/anonshield/main/docker/run.sh -o run.sh
chmod +x run.sh
```

**Windows** (open **PowerShell**):
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/AnonShield/anonshield/main/docker/run.ps1 -OutFile run.ps1
```

> `curl` is built into Linux and macOS. `Invoke-WebRequest` is built into Windows 10/11. No extra installation needed.

### Step 2: Generate a secret key

The key drives pseudonym generation. Keep it stable across runs so the same input always yields the same pseudonym. To de-anonymize later you only need the `db/` database folder, not the key.

**Linux / macOS:**
```bash
export ANON_SECRET_KEY=$(openssl rand -hex 32)
```

To persist it across terminal sessions, append it to your shell profile:

```bash
# Linux (bash)
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc

# macOS (zsh)
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.zshrc
```

**Windows (PowerShell):**
```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:ANON_SECRET_KEY = [System.BitConverter]::ToString($bytes).Replace("-","").ToLower()
```

To persist it on Windows, go to **Settings > System > Environment Variables** and add a variable named `ANON_SECRET_KEY` with that value.

> **No de-anonymization needed?** Skip the key entirely with `--slug-length 0`. Entities are then replaced with their type only (for example `[IP_ADDRESS]`), and no secret key is required.

### Step 3: Anonymize

Pass any file or folder, using a relative or absolute path.

**Single file (CPU):**
```bash
# Linux / macOS
./run.sh ./YOUR_FILE.csv
```
```powershell
# Windows: Windows blocks script execution by default.
# Bypass it for the current session only, then run:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\run.ps1 .\YOUR_FILE.csv
```

**Single file (GPU):**
```bash
# Linux / macOS
./run.sh --gpu ./YOUR_FILE.csv
```
```powershell
# Windows
.\run.ps1 --gpu .\YOUR_FILE.csv
```

**Entire folder:**
```bash
# Linux / macOS
./run.sh ./your/folder/
```
```powershell
# Windows
.\run.ps1 .\your\folder\
```

By default the output is written to `./anon/output/`. For example, anonymizing `report.csv` produces `./anon/output/anon_report.csv`. The script creates an `./anon/` folder in your current directory to keep everything together:

```
./anon/
├── input/    (optional: put files here if you prefer)
├── output/   (anonymized files appear here)
├── db/       (entity mapping database; keep it to de-anonymize later)
└── models/   (NER model cached here on first run, about 1 GB, automatic)
```

> **First run:** the NER transformer model (about 1 GB) downloads automatically into `./anon/models/` and is reused on every subsequent run. This is the only network call AnonShield makes.

---

## Available Tags

Two tags are published. `latest` is the CPU image; `gpu` is the GPU image.

| Tag | Base | Use case | Approx. download |
|-----|------|----------|------------------|
| `latest` | `python:3.12-slim` | CPU image: works on any x86_64 machine | ~900 MB |
| `gpu` | `nvidia/cuda:12.8.0-runtime-ubuntu22.04` | GPU image: needs NVIDIA hardware and CUDA 12.8 | ~3 GB |

Both images include Tesseract OCR (English and Portuguese language data) and the spaCy NLP model. The wrapper script picks the right image automatically: plain `./run.sh` uses `latest`, and `./run.sh --gpu` uses `gpu`.

### Requirements

**CPU (`latest`):** any x86_64 machine with 4 GB or more of RAM.

**GPU (`gpu`):**
- NVIDIA GPU with driver 525 or newer (CUDA 12.8)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed and configured (see [GPU Setup](#gpu-setup-nvidia-container-toolkit) below)

---

## Common Options

| Flag | Description | Default |
|------|-------------|---------|
| `--lang <code>` | Document language (`en`, `pt`, `es`, ...) | `en` |
| `--output-dir <path>` | Local folder for anonymized files | `./anon/output/` |
| `--anonymization-strategy <s>` | Detection strategy (see [Anonymization Strategies](#anonymization-strategies)) | `filtered` |
| `--preserve-entities <types>` | Comma-separated entity types to skip (for example `LOCATION,IP_ADDRESS`) | none |
| `--allow-list <terms>` | Comma-separated terms to never anonymize | none |
| `--word-list <path>` | JSON file of known terms to always anonymize (internal names, acronyms, ...) | none |
| `--anonymization-config <path>` | JSON file with field-level rules for structured files | none |
| `--slug-length <n>` | Hash length in the pseudonym (0 to 64). `0` requires no secret key | `64` |
| `--transformer-model <id>` | NER model: `Davlan/xlm-roberta-base-ner-hrl` (default) or `attack-vector/SecureModernBERT-NER` | `Davlan/xlm-roberta-base-ner-hrl` |
| `--optimize` | Turn on all optimizations at once: `standalone` strategy, cache, `min-word-length=3`, in-memory DB | off |

Run `./run.sh --help` (Linux/macOS) or `.\run.ps1 --help` (Windows) for the complete flag list. Every option is explained with examples in the **[CLI reference on GitHub](https://github.com/AnonShield/anonshield/blob/main/docs/users/CLI_REFERENCE.md)**.

---

## Examples

> All examples use `./run.sh` (Linux/macOS). On **Windows** substitute `.\run.ps1` and use backslashes in paths.

**Portuguese document:**
```bash
./run.sh ./YOUR_FILE.pdf --lang pt
```

**Preserve hostnames and IPs (do not anonymize them):**
```bash
./run.sh ./YOUR_FILE.txt --preserve-entities "HOSTNAME,IP_ADDRESS"
```

**Always anonymize known internal terms:**
```bash
./run.sh ./YOUR_FILE.txt --word-list ./internal_terms.json
```

**Structured file with field-level config:**
```bash
./run.sh ./YOUR_FILE.json --anonymization-config ./anon_config.json
```

**GPU run with the cybersecurity-focused NER model:**
```bash
./run.sh --gpu ./YOUR_FILE.txt --transformer-model attack-vector/SecureModernBERT-NER
```

**Entire folder, output to a separate directory:**
```bash
./run.sh ./reports/ --output-dir ./results/
```

**Skip the secret key (irreversible, type-only labels):**
```bash
./run.sh ./YOUR_FILE.csv --slug-length 0
```

**List all supported entity types:**
```bash
./run.sh --list-entities
```

---

## Detected Entity Types

**Standard PII:** `PERSON`, `LOCATION`, `ORGANIZATION`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `USERNAME`, `PASSWORD`

**Cybersecurity (custom recognizers):** `IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`, `FILE_PATH`, `HASH`, `AUTH_TOKEN`, `CVE_ID`, `CPE_STRING`, `CERT_SERIAL`, `CERTIFICATE`, `CRYPTOGRAPHIC_KEY`, `UUID`, `PGP_BLOCK`, `PORT`, `OID`

When `--lang pt` is set, additional Brazilian recognizers are enabled (for example `BR_CPF`, `BR_CNPJ`, `BR_RG`, `BR_CEP`). Run `./run.sh --list-entities` (Linux/macOS) or `.\run.ps1 --list-entities` (Windows) for the full, up-to-date list.

---

## Anonymization Strategies

Choose with `--anonymization-strategy <name>`. The four production strategies are `filtered` (default), `hybrid`, `standalone`, and `presidio`. A `regex` strategy (pure pattern matching, no ML) and an experimental `slm` strategy are also available; see the [strategies guide](https://github.com/AnonShield/anonshield/blob/main/docs/developers/ANONYMIZATION_STRATEGIES.md).

| Strategy | What it does | Best for |
|----------|--------------|----------|
| `filtered` *(default)* | Presidio pipeline scoped to a curated recognizer set; handles overlapping entity merges correctly | Best accuracy; the safe default |
| `hybrid` | Presidio detection with custom text replacement | Same accuracy as `filtered`, different replacement path |
| `standalone` | Zero Presidio dependency, fastest on GPU | Maximum throughput |
| `presidio` | Full upstream Presidio pipeline | Comparison and baseline use |

**Recommendation:** keep `filtered` (the default) for the best accuracy at a small throughput cost. Switch to `standalone` on GPU when you need maximum throughput.

The numbers below come from the AnonShield benchmark suite. See [benchmark/BENCHMARK.md](https://github.com/AnonShield/anonshield/blob/main/benchmark/BENCHMARK.md) for the methodology and raw data.

**Throughput, GPU** (NVIDIA RTX 5060 Ti 16 GB, D2 operational dataset, 420 MB CSV / 551 MB JSON, 70,951 Tenable vulnerability records):

| Strategy | CSV (KB/s) | JSON (KB/s) | vs. slowest |
|----------|-----------|------------|-------------|
| `standalone` | **732** | **1,250** | **4.3x** faster |
| `hybrid` | 248 | 632 | 1.5x faster |
| `filtered` *(default)* | 240 | 627 | 1.4x faster |
| `presidio` | 171 | 575 | baseline |

**Throughput, CPU only** (AMD Ryzen 5 8600G, 6c/12t, D3 synthetic dataset, 247 MB CSV / 444 MB JSON, 70,951 CVE vulnerability records):

| Strategy | CSV (KB/s) | JSON (KB/s) | vs. slowest |
|----------|-----------|------------|-------------|
| `standalone` | **526** | **518** | CSV: **4x** faster |
| `hybrid` | 134 | 461 | similar |
| `filtered` *(default)* | 132 | 459 | similar |
| `presidio` | 130 | 439 | baseline |

**Throughput, CPU, heterogeneous formats** (Intel Xeon E5-2650, D1 OpenVAS dataset, 136 vulnerability reports in CSV, XML, and PDF, median KB/s on older server hardware):

| Strategy | CSV (KB/s) | XML (KB/s) | PDF (KB/s) | vs. slowest |
|----------|-----------|-----------|-----------|------------|
| `standalone` | **0.94** | **2.05** | **4.26** | about 15% faster |
| `hybrid` | 0.85 | 1.83 | 3.57 | similar |
| `presidio` | 0.85 | 1.85 | 3.56 | similar |
| `filtered` *(default)* | 0.81 | 1.82 | 3.83 | baseline |

> On GPU, `standalone` is about 4x faster than `presidio` on CSV. On the AMD Ryzen (CPU only, large dataset) the same roughly 4x CSV advantage holds; on heterogeneous OpenVAS reports (Intel Xeon) the gap narrows to about 15%.

**Accuracy** (67 annotated vulnerability records, GPU, `attack-vector/SecureModernBERT-NER` model, annotated by 3 security specialists):

| Strategy | Precision | Recall | F1 | Notes |
|----------|-----------|--------|----|-------|
| `filtered` *(default)* | 91.9% | 96.7% | **94.2%** | Best accuracy. Curated recognizer set; handles overlapping merges correctly. |
| `hybrid` | 91.9% | 96.7% | **94.2%** | Same accuracy as `filtered`. Uses manual replacement instead of Presidio's anonymizer. |
| `standalone` | 87.9% | 94.5% | 91.1% | Slightly lower precision. Fastest on GPU. |
| `presidio` | 71.6% | 96.7% | 82.3% | Many false positives. Rarely the best choice. |

---

## Word List (`--word-list`)

If your organization uses internal names, system names, acronyms, or codenames that a general NER model might miss, supply a JSON file listing them. Every term in the list is always anonymized, regardless of context.

**Format:** a JSON object where each key is the entity type label and the value is a list of terms. The key is used directly as the entity type, so any label is valid, including custom ones.

```json
{
  "ORGANIZATION": ["AcmeCorp", "CSIRT-BR", "ProjectPhoenix"],
  "PERSON":       ["Jane Doe", "Carlos Souza"],
  "HOSTNAME":     ["fw-edge.internal", "siem.corp.local"],
  "IP_ADDRESS":   ["10.0.0.1", "192.168.100.254"],
  "MY_SYSTEM":    ["SIEM-Alpha", "FW-CORE-01", "PROXY-DMZ"]
}
```

```bash
./run.sh ./incident_report.txt --word-list ./my_terms.json
```

---

## Field-Level Config (`--anonymization-config`)

For structured files (JSON, CSV, XML), a JSON config file controls exactly which fields are anonymized. Without it, the tool runs NER inference on every field, which is accurate but slow on large datasets. The config lets you:

- **`fields_to_exclude`**: fields that are never anonymized (for example severity scores, timestamps)
- **`fields_to_anonymize`**: explicit list of fields to run NER on; everything else is skipped
- **`force_anonymize`**: map a field directly to an entity type, bypassing NER entirely (useful for fields such as `Port` or `Hostname` that lack obvious syntactic patterns)

**Example, Tenable JSON scan (`config.json`):**
```json
{
  "fields_to_exclude": ["severity", "port", "protocol", "age_in_days"],
  "force_anonymize": {
    "asset.ipv4_addresses": { "entity_type": "IP_ADDRESS" },
    "asset.display_fqdn":   { "entity_type": "HOSTNAME" },
    "asset.display_mac_address": { "entity_type": "MAC_ADDRESS" },
    "scan.target":          { "entity_type": "HOSTNAME" }
  },
  "fields_to_anonymize": ["asset.name", "output"]
}
```

With this config, `severity`, `port`, and the other excluded fields are preserved; `asset.ipv4_addresses` is always pseudonymized as `IP_ADDRESS` regardless of its format; and only `asset.name` and `output` go through NER inference.

Save the config anywhere and pass its path:

```bash
./run.sh ./YOUR_FILE.json --anonymization-config ./anon_config.json
```

**Performance impact (GPU, NVIDIA RTX 5060 Ti, 70,951 vulnerability records):**

| Strategy | CSV without | CSV with | CSV gain | JSON without | JSON with | JSON gain |
|----------|------------|---------|---------|-------------|----------|----------|
| `standalone` | 732 KB/s | **34,341 KB/s** | **47x** | 1,250 KB/s | **31,272 KB/s** | **25x** |
| `filtered` | 240 KB/s | 32,115 KB/s | 134x | 627 KB/s | 29,937 KB/s | 48x |
| `hybrid` | 248 KB/s | 31,902 KB/s | 129x | 632 KB/s | 29,924 KB/s | 47x |
| `presidio` | 171 KB/s | 32,034 KB/s | 188x | 575 KB/s | 29,855 KB/s | 52x |

The config gain is largest for the Presidio-based strategies because they have a higher per-record baseline cost to eliminate. `standalone` stays the fastest even with config (34,341 KB/s vs. about 32,000 KB/s for the others). When you use only `force_anonymize` and `fields_to_exclude` (with no `fields_to_anonymize`), NER inference is bypassed entirely and the strategy choice no longer affects throughput.

---

## GPU Setup (NVIDIA Container Toolkit)

The GPU image needs the NVIDIA Container Toolkit on the host. Install and configure it once:

```bash
# Install the toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Verify the GPU is visible to Docker
docker run --rm --gpus all nvidia/cuda:12.8.0-runtime-ubuntu22.04 nvidia-smi
```

Once `nvidia-smi` works inside that test container, `./run.sh --gpu ...` will use your GPU automatically.

---

## Source Code and Documentation

| Resource | Link |
|----------|------|
| Repository | [github.com/AnonShield/anonshield](https://github.com/AnonShield/anonshield) |
| CLI reference | [docs/users/CLI_REFERENCE.md](https://github.com/AnonShield/anonshield/blob/main/docs/users/CLI_REFERENCE.md) |
| Architecture | [docs/developers/ARCHITECTURE.md](https://github.com/AnonShield/anonshield/blob/main/docs/developers/ARCHITECTURE.md) |
| Anonymization strategies | [docs/developers/ANONYMIZATION_STRATEGIES.md](https://github.com/AnonShield/anonshield/blob/main/docs/developers/ANONYMIZATION_STRATEGIES.md) |
| Benchmark suite | [benchmark/BENCHMARK.md](https://github.com/AnonShield/anonshield/blob/main/benchmark/BENCHMARK.md) |
| Issues | [github.com/AnonShield/anonshield/issues](https://github.com/AnonShield/anonshield/issues) |

---

## Support and Contact

We welcome feedback, questions, and contributions from the community.

* **Bugs and feature requests:** please [open an issue](https://github.com/AnonShield/anonshield/issues) on GitHub. This helps us track problems and keep the community informed.
* **Institutional inquiries and security reports:** for partnerships, institutional questions, or to report a security bug directly, reach our team at **[anonshield@unipampa.edu.br](mailto:anonshield@unipampa.edu.br)**.
