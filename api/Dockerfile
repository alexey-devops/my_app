# ./api/Dockerfile
FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" appuser
USER appuser

WORKDIR /app



COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Adjust this to the actual port your FastAPI app will listen on
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
