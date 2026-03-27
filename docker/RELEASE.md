# Docker Release Guide

How to build, test, and publish AnonShield Docker images.

## Prerequisites

- Docker and Docker Compose installed
- Docker Hub account with push access to `kapelinsky/anon`
- Logged in: `docker login`
- Docker Hub Personal Access Token (for README updates)

## 1. Build Images

From the project root:

```bash
# CPU image
docker build -t kapelinsky/anon:latest --target production -f docker/Dockerfile .

# GPU image
docker build -t kapelinsky/anon:gpu --target gpu -f docker/Dockerfile .
```

## 2. Run Unit Tests

```bash
docker-compose -f docker/docker-compose.yml --profile cpu run --rm \
  -e RUN_UNIT_TESTS=1 \
  -e ANON_SECRET_KEY=test-key \
  anon
```

All 48 tests must pass before pushing.

## 3. Smoke Test

```bash
# Quick functional test
echo "John Doe works at Microsoft. Email: john@microsoft.com" > /tmp/test.txt

docker run --rm \
  -e ANON_SECRET_KEY="test-key" \
  -v /tmp:/data \
  kapelinsky/anon:latest /data/test.txt --output-dir /data/output

cat /tmp/output/anon_test.txt
# Should show anonymized entities like [PERSON_...], [EMAIL_ADDRESS_...], [ORGANIZATION_...]
```

## 4. Push Images

```bash
docker push kapelinsky/anon:latest
docker push kapelinsky/anon:gpu
```

## 5. Update Docker Hub README

The README source is at `docker/DOCKERHUB_README.md`. To push it:

```bash
# Get auth token
HUB_TOKEN=$(curl -s -H "Content-Type: application/json" \
  -X POST -d '{"username":"kapelinsky","password":"YOUR_PAT_TOKEN"}' \
  https://hub.docker.com/v2/users/login/ | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Push README
python3 -c "
import json, urllib.request
readme = open('docker/DOCKERHUB_README.md').read()
data = json.dumps({
    'full_description': readme,
    'description': 'AnonShield - PII pseudonymization framework for CSIRTs with OCR, NER, and SLM support.'
}).encode()
req = urllib.request.Request('https://hub.docker.com/v2/repositories/kapelinsky/anon/', data=data, method='PATCH')
req.add_header('Authorization', 'Bearer $HUB_TOKEN')
req.add_header('Content-Type', 'application/json')
print(urllib.request.urlopen(req).status)
"
```

## 6. Tagging a Version Release

Only create version tags for actual releases:

```bash
docker tag kapelinsky/anon:latest kapelinsky/anon:3.1
docker push kapelinsky/anon:3.1

docker tag kapelinsky/anon:gpu kapelinsky/anon:3.1-gpu
docker push kapelinsky/anon:3.1-gpu
```

## Architecture

```
docker/Dockerfile stages:
  builder-cpu  → (discarded) Compiles deps with CPU-only torch
  production   → kapelinsky/anon:latest  (python:3.12-slim, ~570MB compressed)
  builder-gpu  → (discarded) Compiles deps with CUDA torch
  gpu          → kapelinsky/anon:gpu     (nvidia/cuda:12.1.1, ~2GB compressed)
```

## Checklist

- [ ] Code changes committed and pushed to git
- [ ] `docker build` succeeds for both targets
- [ ] All 48 unit tests pass inside container
- [ ] Smoke test produces anonymized output
- [ ] `docker push` for both `latest` and `gpu`
- [ ] `DOCKERHUB_README.md` updated if flags/features changed
- [ ] Docker Hub README pushed via API
