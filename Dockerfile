

FROM python:3.12-slim

WORKDIR /app

# Install only what you need (add build-essential if you have C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
     curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
     PYTHONUNBUFFERED=1

# Only copy dependency files for layer caching
COPY requirements.txt* pyproject.toml* poetry.lock* ./

RUN pip install --upgrade pip
# Install dependencies (prefer Poetry if present)
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --only main --no-interaction --no-ansi; \
    elif [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

EXPOSE 8000

# Entrypoint: expects code to be mounted at /app
CMD ["uvicorn", "page_count:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
