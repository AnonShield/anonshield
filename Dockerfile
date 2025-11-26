# Use a slim and modern Python base image
FROM python:3.12-slim

# Set environment variables
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1
# Set the path for uv
ENV UV_HOME="/opt/uv"
ENV PATH="/opt/uv/bin:$PATH"
# Set a default secret key (should be overridden in production)
ENV ANON_SECRET_KEY="a-secure-default-secret-key-for-development"

# Install system dependencies required by the application
# - tesseract-ocr: For OCR capabilities
# - git: For version control and potentially fetching dependencies
# - curl: To download the uv installer
# - build-essential: For compiling dependencies if needed from source
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the Python package manager used by this project
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set the working directory inside the container
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv for a fast and reproducible install
RUN uv sync --no-cache

# Download NLP models during the build process to avoid runtime downloads
# This makes the image self-contained and avoids failures in environments without internet access.
RUN uv run python -m spacy download en_core_web_lg && \
    uv run python -m spacy download pt_core_news_lg

# Pre-download the transformer model to the expected directory
# The application looks for it in `models/Davlan/xlm-roberta-base-ner-hrl`
RUN uv run python -c "from transformers import AutoModel, AutoTokenizer; \
    model_name='Davlan/xlm-roberta-base-ner-hrl'; \
    model_dir='models/' + model_name; \
    AutoModel.from_pretrained(model_name, cache_dir=model_dir); \
    AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir);"

# Copy the rest of the application source code into the container
COPY . .

# Set the entrypoint for the container.
# This will execute the anon.py script when the container starts.
# Arguments can be passed to `docker run`. For example:
# docker run anon-lfi path/to/your/file.txt
ENTRYPOINT ["uv", "run", "anon.py"]

# Set a default command (can be overridden).
# For example, to show the help message.
CMD ["--help"]
