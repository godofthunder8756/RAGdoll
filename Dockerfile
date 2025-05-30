FROM python:3.11-slim

WORKDIR /app

# --- OS dependencies ---------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# --- Python dependencies -----------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy application code ----------------------------------------------
COPY app/ app/
COPY bge-m3_repo/ bge-m3_repo/
COPY data/ data/
COPY test_rag.py .

# --- Create necessary directories ---------------------------------------
RUN mkdir -p data && \
    mkdir -p app/__pycache__

# --- Environment variables ---------------------------------------------
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# --- Default command ---------------------------------------------------
# Run ingestion by default, but allow override
CMD ["python", "-m", "app.ingest"]

# --- Usage examples ---------------------------------------------------
# Build: docker build -t ragdoll .
# Run ingestion: docker run -v /your/docs:/app/data ragdoll
# Interactive query: docker run -it ragdoll python -m app.query
# Run tests: docker run ragdoll python test_rag.py
