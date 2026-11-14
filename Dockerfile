# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid appuser --shell /bin/false --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8080\")}/healthz', timeout=2)" || exit 1

CMD ["sh", "-c", "uvicorn agrofarm_api.main:app_factory --factory --host 0.0.0.0 --port ${PORT:-8080}"]
