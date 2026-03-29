# AnonShield — PII Pseudonymization for CSIRTs

Modular pseudonymization framework for Cybersecurity Incident Response Teams. Anonymizes PII and cybersecurity indicators using HMAC-SHA256, preserving structure in JSON, XML, CSV, and more. Supports 24 languages, OCR, and custom cybersecurity recognizers (IP, CVE, hash, URL, etc.).

> **Source code, documentation & research artifact:** [github.com/AnonShield/tool](https://github.com/AnonShield/tool)

---

## Available Tags

| Tag | Base | Use Case | Approx. Size |
|-----|------|----------|-------------|
| `latest` | `python:3.12-slim` | CPU — works on any x86_64 machine | ~2 GB |
| `gpu` | `nvidia/cuda:12.8.0` | GPU — requires NVIDIA hardware + CUDA 12.8 | ~6 GB |

---

## Requirements

**CPU (`latest`):** Any x86_64 machine with 4 GB+ RAM.

**GPU (`gpu`):**
- NVIDIA GPU, driver ≥ 525 (CUDA 12.8)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed and configured

---

## Quick Start

> **The only prerequisite is Docker.** Install it for your OS: [Linux](https://docs.docker.com/engine/install/) · [macOS](https://docs.docker.com/desktop/setup/install/mac-install/) · [Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Everything else is already included in your operating system.

### Step 1 — Download the wrapper script

**Linux / macOS** — open a terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/AnonShield/tool/main/docker/run.sh -o run.sh
chmod +x run.sh
```

**Windows** — open **PowerShell**:
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/AnonShield/tool/main/docker/run.ps1 -OutFile run.ps1
```

> `curl` is built into Linux and macOS. `Invoke-WebRequest` is built into Windows 10/11. No extra installation needed.

### Step 2 — Generate a secret key

The key is used to generate pseudonyms. To de-anonymize later, you only need the `db/` database folder — not the key itself.

**Linux / macOS:**
```bash
export ANON_SECRET_KEY=$(openssl rand -hex 32)
```

To keep it across terminal sessions:

**Linux:**
```bash
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc
```

**macOS:**
```bash
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.zshrc
```

Windows (PowerShell):
```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:ANON_SECRET_KEY = [System.BitConverter]::ToString($bytes).Replace("-","").ToLower()
```

To keep it across sessions, go to **Settings → System → Environment Variables**, add a new variable named `ANON_SECRET_KEY` with that value.

### Step 3 — Anonymize

Pass any file or folder — relative or absolute path:

**Single file (CPU):**
```bash
# Linux / macOS
./run.sh ./YOUR_FILE.csv
```
```powershell
# Windows
# Note: Windows blocks script execution by default. Bypass it for the current session only:
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

Output is written to `./anon/output/anon_YOUR_FILE.csv`. The script automatically creates an `./anon/` folder in your current directory:

```
./anon/
├── input/    ← optional: put files here if you prefer
├── output/   ← anonymized files appear here
├── db/       ← entity mapping database (keep this to de-anonymize later)
└── models/   ← NER model cached here on first run (~1 GB, automatic)
```

> **On first run:** the NER transformer model (~1 GB) is downloaded automatically to `./anon/models/` and reused on all subsequent runs.

> **Note:** If you don't need to de-anonymize later, use `--slug-length 0` — entities are replaced with their type only (e.g. `[IP_ADDRESS]`) and no secret key is required.

---

## Common Options

| Flag | Description | Default |
|------|-------------|---------|
| `--lang <code>` | Document language (`en`, `pt`, `es`, ...) | `en` |
| `--output-dir <path>` | Local path where anonymized files are saved | `./anon/output/` |
| `--preserve-entities <types>` | Comma-separated entity types to skip (e.g. `LOCATION,IP_ADDRESS`) | — |
| `--allow-list <terms>` | Comma-separated terms to never anonymize | — |
| `--slug-length <n>` | Hash length in the anonymized slug (0–64) | `64` |
| `--word-list <path>` | JSON file of known terms to always anonymize (internal names, acronyms, etc.) | — |
| `--anonymization-strategy <s>` | Detection strategy — see below | `filtered` |
| `--optimize` | Enable all performance optimizations | off |

For the complete reference with examples for every option, see the **[CLI_REFERENCE.md on GitHub](https://github.com/AnonShield/tool/blob/main/docs/users/CLI_REFERENCE.md)**

Run `./run.sh --help` (Linux/macOS) or `.\run.ps1 --help` (Windows) for the full options list.

---

## Anonymization Strategies

Choose with `--anonymization-strategy <name>`.

**Throughput — GPU** (NVIDIA RTX 5060 Ti 16 GB · D2 operational dataset · 420 MB CSV / 551 MB JSON, 70,951 Tenable vulnerability records):

| Strategy | CSV (KB/s) | JSON (KB/s) | vs. slowest |
|----------|-----------|------------|-------------|
| `standalone` | **732** | **1,250** | **4.3×** faster |
| `hybrid` | 248 | 632 | 1.5× faster |
| `filtered` *(default)* | 240 | 627 | 1.4× faster |
| `presidio` | 171 | 575 | baseline |

**Throughput — CPU, no GPU** (AMD Ryzen 5 8600G (6c/12t) · D3 synthetic dataset · 247 MB CSV / 444 MB JSON, 70,951 CVE vulnerability records):

Benchmark run without GPU to measure CPU-only performance on a large structured dataset.

| Strategy | CSV (KB/s) | JSON (KB/s) | vs. slowest |
|----------|-----------|------------|-------------|
| `standalone` | **526** | **518** | CSV: **4×** faster |
| `hybrid` | 134 | 461 | similar |
| `filtered` *(default)* | 132 | 459 | similar |
| `presidio` | 130 | 439 | baseline |

**Throughput — CPU, heterogeneous formats** (Intel Xeon E5-2650 · D1 OpenVAS dataset · 136 vulnerability reports, median KB/s):

Benchmark on a heterogeneous set of real OpenVAS scan reports in CSV, XML, and PDF format, measuring per-file median throughput on older server hardware.

| Strategy | CSV (KB/s) | XML (KB/s) | PDF (KB/s) | vs. slowest |
|----------|-----------|-----------|-----------|------------|
| `standalone` | **0.94** | **2.05** | **4.26** | **~15 %** faster |
| `hybrid` | 0.85 | 1.83 | 3.57 | similar |
| `presidio` | 0.85 | 1.85 | 3.56 | similar |
| `filtered` *(default)* | 0.81 | 1.82 | 3.83 | baseline |

> On GPU, `standalone` is **4× faster** than `presidio` on CSV. On the AMD Ryzen (CPU-only, large dataset), the same ~4× advantage holds for CSV; on heterogeneous OpenVAS reports (Intel Xeon), the gap shrinks to ~15 %.

**Accuracy** (67 annotated vulnerability records · GPU · `attack-vector/SecureModernBERT-NER` model · annotated by 3 security specialists):

| Strategy | Precision | Recall | F1 | Notes |
|----------|-----------|--------|----|-------|
| `filtered` *(default)* | 91.9 % | 96.7 % | **94.2 %** | Best accuracy. Curated recognizer set; handles overlapping entity merges correctly. |
| `hybrid` | 91.9 % | 96.7 % | **94.2 %** | Same accuracy as `filtered`. Uses manual text replacement instead of Presidio's anonymizer. |
| `standalone` | 87.9 % | 94.5 % | 91.1 % | Slightly lower precision. Fastest on GPU. |
| `presidio` | 71.6 % | 96.7 % | 82.3 % | Many false positives. Rarely the best choice. |

**Recommendation:** `filtered` (default) gives the best accuracy at a small throughput cost. Use `standalone` on GPU for maximum throughput.

---

## Word List (`--word-list`)

If your organization uses internal names, system names, acronyms, or codenames that a general NER model might not recognize, you can supply a JSON file listing them. Every term in the list is always anonymized, regardless of context.

**Format:** a JSON object where each key is the entity type label and the value is a list of terms. The key is used directly as the entity type — any label is valid, including custom ones.

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

## Anonymization Config (`--anonymization-config`)

For structured files (JSON, CSV, XML), you can pass a JSON config file to control exactly which fields get anonymized. Without it, the tool runs NER inference on every field — accurate but slow on large datasets. The config lets you:

- **`fields_to_exclude`** — fields that are never anonymized (e.g. severity scores, timestamps)
- **`fields_to_anonymize`** — explicit list of fields to run NER on; everything else is skipped
- **`force_anonymize`** — map a field directly to an entity type, bypassing NER entirely (useful for fields like `Port` or `Hostname` that don't have obvious syntactic patterns)

**Example — Tenable JSON scan (`config.json`):**
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

With this config: `severity`, `port`, etc. are preserved; `asset.ipv4_addresses` is always pseudonymized as `IP_ADDRESS` regardless of its format; only `asset.name` and `output` go through NER inference.

Save the config anywhere and pass its path:

```bash
./run.sh ./YOUR_FILE.json --anonymization-config ./anon_config.json
```

**Performance impact (GPU · NVIDIA RTX 5060 Ti · 70,951 vulnerability records):**

| Strategy | CSV without | CSV with | CSV gain | JSON without | JSON with | JSON gain |
|----------|------------|---------|---------|-------------|----------|----------|
| `standalone` | 732 KB/s | **34,341 KB/s** | **47×** | 1,250 KB/s | **31,272 KB/s** | **25×** |
| `filtered` | 240 KB/s | 32,115 KB/s | 134× | 627 KB/s | 29,937 KB/s | 48× |
| `hybrid` | 248 KB/s | 31,902 KB/s | 129× | 632 KB/s | 29,924 KB/s | 47× |
| `presidio` | 171 KB/s | 32,034 KB/s | 188× | 575 KB/s | 29,855 KB/s | 52× |

The config gain is larger for Presidio-based strategies because they have a higher per-record baseline cost to eliminate. `standalone` remains the fastest even with config (34,341 KB/s vs ~32,000 KB/s for others). When using only `force_anonymize` and `fields_to_exclude` — with no `fields_to_anonymize` — NER inference is completely bypassed and strategy choice no longer affects throughput.

---

## Examples

> All examples use `./run.sh` (Linux/macOS). On **Windows** substitute `.\run.ps1` and use backslashes for paths.

**Portuguese document:**
```bash
./run.sh ./YOUR_FILE.pdf --lang pt
```

**Preserve hostnames and IPs (don't anonymize them):**
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

**GPU with cybersecurity-focused NER model:**
```bash
./run.sh --gpu ./YOUR_FILE.txt --transformer-model attack-vector/SecureModernBERT-NER
```

**Entire folder, output to a separate directory:**
```bash
./run.sh ./reports/ --output-dir ./results/
```

**List all supported entity types:**
```bash
./run.sh --list-entities
```

---

## GPU Setup (NVIDIA Container Toolkit)

```bash
# Install toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

If you get `--gpus all not supported`, try adding `--runtime=nvidia`:
```bash
docker run --rm --runtime=nvidia --gpus all anonshield/anon:gpu /data/file.txt ...
```

---

## Detected Entity Types

**Standard PII:** `PERSON`, `LOCATION`, `ORGANIZATION`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `USERNAME`, `PASSWORD`

**Cybersecurity (custom recognizers):** `IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`, `FILE_PATH`, `HASH`, `AUTH_TOKEN`, `CVE_ID`, `CPE_STRING`, `CERT_SERIAL`, `CERTIFICATE`, `CRYPTOGRAPHIC_KEY`, `UUID`, `PGP_BLOCK`, `PORT`, `OID`

Run `./run.sh --list-entities` (Linux/macOS) or `.\run.ps1 --list-entities` (Windows) for the full list.

---

## Full CLI Reference

Every option explained in plain language with examples: **[CLI_REFERENCE.md on GitHub](https://github.com/AnonShield/tool/blob/main/docs/users/CLI_REFERENCE.md)**

---

## Source Code & Documentation

| Resource | Link |
|----------|------|
| Repository | [github.com/AnonShield/tool](https://github.com/AnonShield/tool) |
| CLI Reference | [docs/users/CLI_REFERENCE.md](https://github.com/AnonShield/tool/blob/main/docs/users/CLI_REFERENCE.md) |
| Architecture | [docs/developers/ARCHITECTURE.md](https://github.com/AnonShield/tool/blob/main/docs/developers/ARCHITECTURE.md) |
| Anonymization Strategies | [docs/developers/ANONYMIZATION_STRATEGIES.md](https://github.com/AnonShield/tool/blob/main/docs/developers/ANONYMIZATION_STRATEGIES.md) |
| Benchmark Suite | [benchmark/BENCHMARK.md](https://github.com/AnonShield/tool/blob/main/benchmark/BENCHMARK.md) |
| Experiments & Datasets | [paper_data/EXPERIMENTS.md](https://github.com/AnonShield/tool/blob/main/paper_data/EXPERIMENTS.md) |
| Issues | [github.com/AnonShield/tool/issues](https://github.com/AnonShield/tool/issues) |

---

## Support & Contact

We welcome feedback, questions, and contributions from the community.

* **Bugs & Feature Requests:** Please [open an issue](https://github.com/AnonShield/tool/issues) on our GitHub repository. This helps us track problems and keep the community informed.
* **Direct Contact & Inquiries:** For institutional questions, partnerships, or to report a security bug directly, reach out to our team at **[anonshield@unipampa.edu.br](mailto:anonshield@unipampa.edu.br)**.
