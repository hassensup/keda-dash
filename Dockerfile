# Multi-stage Dockerfile for KEDA Dashboard (Monolithic)
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --frozen-lockfile
COPY frontend/ .
RUN yarn build

# Stage 2: Python backend + static frontend
FROM python:3.11-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build
COPY --from=frontend-build /app/frontend/build ./frontend/build

# Create a startup script that serves both
RUN echo '#!/bin/bash\ncd /app/backend && uvicorn server:app --host 0.0.0.0 --port 8001' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8001/api/health || exit 1

CMD ["/app/start.sh"]
