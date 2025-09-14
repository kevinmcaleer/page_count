# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS app
WORKDIR /app

# System deps (cacheable)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install deps using whichever manifest exists (Poetry or pip)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=pyproject.toml,target=/tmp/pyproject.toml,required=false \
    --mount=type=bind,source=poetry.lock,target=/tmp/poetry.lock,required=false \
    --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt,required=false \
    bash -lc 'set -e
      if [[ -f /tmp/pyproject.toml ]]; then
        echo "[deps] Using Poetry"
        pip install poetry
        poetry config virtualenvs.create false
        # If lock missing, this will still work but is less reproducible
        poetry install --no-interaction --no-ansi --only main
      elif [[ -f /tmp/requirements.txt ]]; then
        echo "[deps] Using pip requirements.txt"
        pip install -r /tmp/requirements.txt
      else
        echo "[deps] No dependency manifest found; skipping"
      fi
    '

# Now copy the rest of your app (cheap layer that invalidates with code changes)
COPY . .

CMD ["python", "-m", "your_app"]
