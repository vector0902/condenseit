# ---------------------------------------------------------------------------
# Stage 1: Build frontend SPA
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

# Cache node_modules via bind mount (docker-compose volume) or npm cache
RUN mkdir -p /usr/local/lib/node_modules
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline || npm install --prefer-offline
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# System dependencies (rarely changes)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ffmpeg \
    libxml2 \
    libxslt1.1 \
  && rm -rf /var/lib/apt/lists/*

# Copy dependency files AND source code (pip needs src/ to install)
COPY pyproject.toml README.md ./
COPY src ./src

# Install Python dependencies (cached unless pyproject.toml or src/ changes)
# pip cache is mounted as volume in docker-compose.yml at /root/.cache/pip
RUN pip install .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV CONDENSEIT_DATA_DIR=/app/data
RUN mkdir -p /app/data/digests

EXPOSE 8899

CMD ["condenseit", "serve", "--host", "0.0.0.0", "--port", "8899"]
