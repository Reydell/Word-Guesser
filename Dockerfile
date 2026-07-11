FROM ghcr.io/astral-sh/uv:0.8.3-python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend ./backend
COPY frontend ./frontend
RUN mkdir /app/storage

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
