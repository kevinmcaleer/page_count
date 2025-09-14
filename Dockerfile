
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS app
WORKDIR /app

# System deps (rarely change) -> keep cache hot
RUN apt-get update && apt-get install -y --no-install-recommends \
     build-essential curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
     PYTHONUNBUFFERED=1

# === Dependency layer (cacheable) ===
# Copy ONLY requirements so code changes don't bust this layer
COPY requirements*.txt pyproject.toml* poetry.lock* ./
# Use BuildKit cache for pip downloads (keeps wheels between builds)
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --only main --no-interaction --no-ansi; \
    elif [ -f "requirements.txt" ]; then \
        pip install --upgrade pip && \
        --mount=type=cache,target=/root/.cache/pip \
        pip install -r requirements.txt; \
    fi

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Entrypoint: expects code to be mounted at /app
CMD ["uvicorn", "page_count:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
