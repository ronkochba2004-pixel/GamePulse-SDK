FROM python:3.11-slim AS base
WORKDIR /app

RUN pip install --no-cache-dir uv

# ── Install dependencies ─────────────────────────────────────────────────
FROM base AS deps
COPY pyproject.toml ./
COPY packages/gamepulse-core ./packages/gamepulse-core
COPY services/api ./services/api

RUN uv pip install --system -e ./packages/gamepulse-core -e ./services/api

# ── Runtime image ────────────────────────────────────────────────────────
FROM deps AS runtime
WORKDIR /app/services/api
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-level", "info"]
