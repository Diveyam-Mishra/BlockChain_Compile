# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (optional: build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install first for better caching
COPY compliledger/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source
# Copy the entire package to preserve package structure (__init__.py)
COPY compliledger /app/compliledger

# Expose default (Railway will set PORT env; exposing is optional)
EXPOSE 8000

# Default envs (Railway overrides PORT)
ENV API_HOST=0.0.0.0

# Start the API
# Use module path so reload works when DEBUG=true (though reload not used in prod)
CMD ["python", "-m", "compliledger.backend.app.main"]
