ARG CUDA=12.8.0
FROM nvidia/cuda:${CUDA}-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common curl ca-certificates gnupg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3.12-dev python3-pip git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN uv venv --python 3.12 /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN uv pip install --no-cache \
        "torch==2.11.0+cu128" "torchvision==0.26.0+cu128" \
        --index-url https://download.pytorch.org/whl/cu128

RUN uv pip install --no-cache \
        "transformers>=5.3.0" \
        accelerate sentencepiece sentence-transformers \
        pillow pydantic PyYAML einops \
        pypdfium2 \
        "huggingface_hub[hf_xet]"

COPY src/anon /app/src/anon
COPY pyproject.toml README.md /app/

RUN uv pip install --no-cache -e . --no-deps

CMD ["python", "-m", "anon.ocr.cli"]
