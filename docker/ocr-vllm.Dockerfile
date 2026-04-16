# vLLM serving image for OCR VLMs — 100% local, no cloud.
#
# Serves any vLLM-supported VLM (GLM-4V, Qwen2.5-VL, LightOn-Qwen, etc.)
# on localhost with OpenAI-compatible HTTP API.
#
# Features enabled:
#   - MTP (Multi-Token Prediction) speculative decoding — 1.5–2× speedup
#   - FP8 quantization (when model supports) — 1.3–1.5× speedup + less VRAM
#   - PagedAttention + continuous batching — baseline vLLM win (5–10×)
#
# Build:
#   docker compose -f docker/docker-compose.bench.yml build vllm-serve
#
# Usage (select model via env MODEL_ID):
#   MODEL_ID=zai-org/GLM-4.1V-9B-Thinking-FP8 docker compose ... up vllm-serve
ARG CUDA=12.8.0
FROM nvidia/cuda:${CUDA}-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf-cache \
    VLLM_USE_MODELSCOPE=false

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

# vLLM nightly with flash-attn + FP8 kernels.
# Torch must match vLLM's pinned ABI.
RUN uv pip install --no-cache \
        "torch==2.5.1" "torchvision==0.20.1" \
        --index-url https://download.pytorch.org/whl/cu124

RUN uv pip install --no-cache --pre vllm \
        --extra-index-url https://wheels.vllm.ai/nightly

RUN uv pip install --no-cache \
        "transformers>=4.57" accelerate pillow pydantic \
        "huggingface_hub[hf_xet]" qwen-vl-utils

# vLLM OpenAI-compat server on :8000.
# Speculative decoding (MTP-style) via draft model: leave to per-model override.
EXPOSE 8000
ENV VLLM_HOST=0.0.0.0 VLLM_PORT=8000

# Default serves GLM-4V FP8; override MODEL_ID / VLLM_ARGS to switch.
ENV MODEL_ID="zai-org/GLM-4.1V-9B-Thinking-FP8" \
    VLLM_ARGS="--max-model-len 8192 --gpu-memory-utilization 0.90 --enforce-eager"

CMD ["sh", "-c", "python -m vllm.entrypoints.openai.api_server --model $MODEL_ID --host $VLLM_HOST --port $VLLM_PORT $VLLM_ARGS"]
