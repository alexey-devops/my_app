# ./worker/Dockerfile
FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY healthcheck.py healthcheck.py

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user for runtime after dependencies are installed
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# No exposed port for worker typically, as it doesn't serve HTTP directly
# But if it has a healthcheck endpoint, might need to expose a port.
# For now, let's assume it runs a background task.

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python healthcheck.py || exit 1

# Placeholder command. This will be replaced with actual worker command (e.g., celery worker)
CMD ["python", "main.py"]
