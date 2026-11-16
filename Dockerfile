FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH=/app/backend/.venv/bin:$PATH
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# Last, so a new SHA doesn't invalidate the cached layers above.
ARG GIT_SHA
ENV GIT_SHA=$GIT_SHA
EXPOSE 8000
USER nobody
# Render sets PORT; locally it defaults to 8000.
CMD alembic upgrade head && exec uvicorn woodshed.main:app --host 0.0.0.0 --port ${PORT:-8000}
