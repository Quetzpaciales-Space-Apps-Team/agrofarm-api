# syntax=docker/dockerfile:1
FROM python:3.14-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY docs/contract ./docs/contract
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim-trixie AS runtime
# Apply pending Debian security updates, and drop pip: the runtime never installs
# anything and pip vendors packages that image scanners flag.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip \
    && useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PORT=8080
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz', timeout=2)"]
CMD ["sh", "-c", "exec uvicorn core_api.main:create_app --factory --host 0.0.0.0 --port ${PORT} --no-access-log"]
