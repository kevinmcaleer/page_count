
# syntax=docker/dockerfile:1.4
# Production-ready Dockerfile for Python 3.12 FastAPI app with optimal layer caching
# See comments for cache tips and usage

FROM python:3.12-slim AS app

# 1. Set working directory
WORKDIR /app

# 2. Install system packages (rarely change)
RUN apt-get update \
        && apt-get install --no-install-recommends -y build-essential curl \
        && rm -rf /var/lib/apt/lists/*

# 3. Set environment variables for Python best practices
ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1

# 4. Install Python dependencies (cache-friendly)
# Copy only dependency files first to maximize cache
COPY pyproject.toml poetry.lock requirements.txt* ./

# Prefer Poetry if present, else fallback to pip
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
            pip install poetry && \
            poetry config virtualenvs.create false && \
            poetry install --only main --no-interaction --no-ansi; \
     elif [ -f "requirements.txt" ]; then \
            pip install --upgrade pip && \
            --mount=type=cache,target=/root/.cache/pip \
            pip install -r requirements.txt; \
     fi

# 5. Copy app code (changes often)
COPY . .

# 6. (Optional) Create non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 7. Expose port and add healthcheck
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 8. Default command: run FastAPI app with Uvicorn
CMD ["uvicorn", "page_count:app", "--host", "0.0.0.0", "--port", "8000"]

# ---
# Build tips:
# Regular build: docker build -t myapp:dev .
# Force only app stage to rebuild: docker buildx build --no-cache-filter=app -t myapp:dev .
# For dev: use docker-compose with bind-mount for /app to avoid rebuilds on code change.
