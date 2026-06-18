# ---------------------------------------------------------------------------
# Base image: system + Python dependencies (rarely changes)
# Build: docker build -t condenseit:base -f docker-base/Dockerfile .
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ffmpeg \
    libxml2 \
    libxslt1.1 \
  && rm -rf /var/lib/apt/lists/*

# Cache all pip dependencies via a placeholder package
COPY pyproject.toml README.md ./
RUN mkdir -p src/condenseit && touch src/condenseit/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf src/

ENV CONDENSEIT_DATA_DIR=/app/data
RUN mkdir -p /app/data/digests
