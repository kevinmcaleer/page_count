# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS app
WORKDIR /app

# System deps (rarely change) -> keep cache hot
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# === Dependency layer (cacheable) ===
# Copy ONLY requirements so code changes don't bust this layer
COPY requirements*.txt ./
# Use BuildKit cache for pip downloads (keeps wheels between builds)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# === App code (changes often) ===
COPY . .

# Pick one of these or adjust to your app
# CMD ["python", "main.py"]
CMD ["python", "-m", "your_app"]
