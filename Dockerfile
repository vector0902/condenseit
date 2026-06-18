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

# Copy only pyproject.toml – rarely changes
COPY pyproject.toml README.md ./

# Create a minimal placeholder so pip can resolve & cache ALL dependencies
# This layer is reused as long as pyproject.toml stays the same.
RUN mkdir -p src/condenseit && touch src/condenseit/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf src/

# Copy the actual source code (changes on every edit)
COPY src ./src

# Install only the package wheel, no dependency re-resolution
RUN pip install --no-cache-dir --no-deps .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV CONDENSEIT_DATA_DIR=/app/data
RUN mkdir -p /app/data/digests

EXPOSE 8899

CMD ["condenseit", "serve", "--host", "0.0.0.0", "--port", "8899"]
