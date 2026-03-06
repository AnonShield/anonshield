# AnonLFI 3.0 — PII Pseudonymization for CSIRTs

Modular pseudonymization framework for Cybersecurity Incident Response Teams. Anonymizes PII and cybersecurity indicators using HMAC-SHA256, preserving structure in JSON, XML, CSV, and more. Supports 24 languages, OCR, and custom cybersecurity recognizers (IP, CVE, hash, URL, etc.).

**GitHub:** [github.com/AnonShield/tool](https://github.com/AnonShield/tool)

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

### Step 1 — Download the wrapper script

```bash
curl -fsSL https://github.com/AnonShield/tool/raw/main/docker/run-docker.sh -o run-docker.sh
chmod +x run-docker.sh
```

### Step 2 — Generate a secret key

The key is used to generate pseudonyms. You'll need it again to de-anonymize — keep it safe.

```bash
export ANON_SECRET_KEY=$(openssl rand -hex 32)
```

To keep it across terminal sessions:
```bash
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc
```

### Step 3 — Put your files in `./anon/input/`

The script creates an `./anon/` folder in your current directory to keep everything in one place:

```
./anon/
├── input/    ← put your files here
├── output/   ← anonymized files appear here
└── models/   ← NER model cached here on first run (~1 GB, automatic)
```

```bash
cp /path/to/YOUR_FILE.csv ./anon/input/
```

### Step 4 — Anonymize

**Single file (CPU):**
```bash
./run-docker.sh ./anon/input/YOUR_FILE.csv
```

**Single file (GPU):**
```bash
./run-docker.sh --gpu ./anon/input/YOUR_FILE.csv
```

**Entire input folder:**
```bash
./run-docker.sh ./anon/input/
```

Output is written to `./anon/output/anon_YOUR_FILE.csv`.

> **On first run:** the NER transformer model (~1 GB) is downloaded automatically to `./anon/models/` and reused on all subsequent runs.

---

## Common Options

| Flag | Description | Default |
|------|-------------|---------|
| `--lang <code>` | Document language (`en`, `pt`, `es`, ...) | `en` |
| `--output-dir <path>` | Local path where anonymized files are saved | `./output/` |
| `--preserve-entities <types>` | Comma-separated entity types to skip (e.g. `LOCATION,IP_ADDRESS`) | — |
| `--allow-list <terms>` | Comma-separated terms to never anonymize | — |
| `--slug-length <n>` | Hash length in the anonymized slug (0–64) | `64` |
| `--anonymization-strategy <s>` | Detection strategy — see below | `filtered` |
| `--optimize` | Enable all performance optimizations | off |

Run `./run-docker.sh --help` for the full options list.

---

## Anonymization Strategies

Choose with `--anonymization-strategy <name>`.

**Throughput — GPU** (NVIDIA RTX 5060 Ti 16 GB · 420 MB CSV / 551 MB JSON, 70,951 vulnerability records):

| Strategy | CSV (KB/s) | JSON (KB/s) | vs. slowest |
|----------|-----------|------------|-------------|
| `standalone` | **732** | **1,250** | **4.3×** faster |
| `hybrid` | 248 | 632 | 1.5× faster |
| `filtered` *(default)* | 240 | 627 | 1.4× faster |
| `presidio` | 171 | 575 | baseline |

**Throughput — CPU** (Intel Xeon E5-2650 · 136 OpenVAS vulnerability reports, median KB/s):

| Strategy | CSV (KB/s) | XML (KB/s) | PDF (KB/s) | vs. slowest |
|----------|-----------|-----------|-----------|------------|
| `standalone` | **0.94** | **2.05** | **4.26** | **~15 %** faster |
| `hybrid` | 0.85 | 1.83 | 3.57 | similar |
| `presidio` | 0.85 | 1.85 | 3.56 | similar |
| `filtered` *(default)* | 0.81 | 1.82 | 3.83 | baseline |

> On GPU, `standalone` is **4× faster** than `presidio` on CSV. On CPU, the gap shrinks to ~15 % — choose based on your hardware.

**Accuracy** (67 annotated vulnerability records · GPU · `attack-vector/SecureModernBERT-NER` model · annotated by 3 security specialists):

| Strategy | Precision | Recall | F1 | Notes |
|----------|-----------|--------|----|-------|
| `filtered` *(default)* | 91.9 % | 96.7 % | **94.2 %** | Best accuracy. Curated recognizer set; handles overlapping entity merges correctly. |
| `hybrid` | 91.9 % | 96.7 % | **94.2 %** | Same accuracy as `filtered`. Uses manual text replacement instead of Presidio's anonymizer. |
| `standalone` | 87.9 % | 94.5 % | 91.1 % | Slightly lower precision. Fastest on GPU. Experimental. |
| `presidio` | 71.6 % | 96.7 % | 82.3 % | Many false positives. Rarely the best choice. |

**Recommendation:** `filtered` (default) gives the best accuracy at a small throughput cost. Use `standalone` on GPU for maximum throughput.

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
./run-docker.sh ./YOUR_FILE.json --anonymization-config ./anon_config.json
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

**Portuguese document:**
```bash
./run-docker.sh ./YOUR_FILE.pdf --lang pt
```

**Preserve hostnames and IPs (don't anonymize them):**
```bash
./run-docker.sh ./YOUR_FILE.txt --preserve-entities "HOSTNAME,IP_ADDRESS"
```

**Structured file with field-level config:**
```bash
./run-docker.sh ./YOUR_FILE.json --anonymization-config ./anon_config.json
```

**GPU with cybersecurity-focused NER model:**
```bash
./run-docker.sh --gpu ./YOUR_FILE.txt --transformer-model attack-vector/SecureModernBERT-NER
```

**Entire folder, output to a separate directory:**
```bash
./run-docker.sh ./reports/ --output-dir ./results/
```

**List all supported entity types:**
```bash
./run-docker.sh --list-entities
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

Run `./run-docker.sh --list-entities` for the full list.
