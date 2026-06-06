# Shared image for all Python agents. The specific agent is selected by the
# `command:` (e.g. cdmas-tma) in docker-compose.yml.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Default command is overridden per-service in docker-compose.yml.
CMD ["python", "-c", "print('Set a command: cdmas-tma | cdmas-aca | ...')"]
