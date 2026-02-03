# syntax=docker/dockerfile:1.4

FROM python:3.12-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Copy project files
COPY --link pyproject.toml .
COPY --link uv.lock .

# Install the dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application files
COPY --link . .

EXPOSE 8080

# Run marimo edit in headless mode with authentication
# Token password should be provided via environment variable
CMD ["sh", "-c", "uv run marimo edit --headless --host 0.0.0.0 --port 8080 --token --token-password=${MARIMO_TOKEN_PASSWORD:-changeme}"]
