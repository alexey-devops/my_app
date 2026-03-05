# ./worker/Dockerfile
FROM python:3.10-slim-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY healthcheck.py healthcheck.py

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user with a specific UID for runtime
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/sh --create-home appuser && \
    chown -R 1001:1001 /app
USER 1001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python healthcheck.py || exit 1

CMD ["python", "main.py"]
