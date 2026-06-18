# ---------------------------------------------------------------------------
# Stage 1: Build frontend SPA
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

RUN mkdir -p /usr/local/lib/node_modules
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline || npm install --prefer-offline
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: App image (base image has all system + Python deps)
# ---------------------------------------------------------------------------
FROM condenseit:base

WORKDIR /app

COPY src ./src
RUN pip install --no-cache-dir --no-deps .

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8899

CMD ["condenseit", "serve", "--host", "0.0.0.0", "--port", "8899"]
