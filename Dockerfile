# Stage 1: build the Next.js static export
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime serving API + static frontend
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
RUN uv sync --frozen --no-dev
COPY --from=frontend /frontend/out ./static
ENV STATIC_DIR=/app/backend/static \
    DB_PATH=/app/db/finally.db \
    PATH="/app/backend/.venv/bin:$PATH"
RUN mkdir -p /app/db
VOLUME ["/app/db"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
