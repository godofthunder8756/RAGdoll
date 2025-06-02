FROM python:3.11-slim

WORKDIR /app

# --- OS dependencies (minimal, offline-first) -------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# --- Python dependencies -----------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy application code ----------------------------------------------
COPY app/ app/
COPY data/ data/
COPY bge-m3_repo/ bge-m3_repo/
COPY test_rag.py .
COPY test_namespaced_system.py .
COPY test_layers_2_and_4.py .

# --- Create necessary directories ---------------------------------------
RUN mkdir -p app/indexes && \
    mkdir -p backups && \
    chmod -R 755 /app

# --- Environment variables (offline-first) ----------------------------
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV OFFLINE_MODE=true
ENV BGE_MODEL_PATH=/app/bge-m3_repo

# --- Verify model exists and create startup script --------------------
RUN echo '#!/bin/bash\n\
echo "🚀 Starting RAGdoll Enterprise (Offline Mode)"\n\
echo "📂 Checking BGE-M3 model..."\n\
if [ -f "./bge-m3_repo/config.json" ]; then\n\
    echo "✅ BGE-M3 model found locally"\n\
else\n\
    echo "❌ BGE-M3 model not found. Please ensure bge-m3_repo/ is properly mounted."\n\
    exit 1\n\
fi\n\
echo "🔄 Starting application..."\n\
exec "$@"' > /app/startup.sh && chmod +x /app/startup.sh

# --- Default command (offline ingestion) -------------------------------
CMD ["/app/startup.sh", "python", "-m", "app.ingest_namespaced", "--auto"]

# --- Usage examples ---------------------------------------------------
# Build: docker build -t ragdoll .
# Run auto-ingestion: docker run -v /your/docs:/app/data ragdoll
# Manual namespace ingestion: docker run -v /your/docs:/app/data ragdoll python -m app.ingest_namespaced --namespace engineering
# Interactive query: docker run -it ragdoll python -m app.query_namespaced --interactive
# Namespace management: docker run -it ragdoll python -m app.namespace_manager list --details
# Run legacy tests: docker run ragdoll python test_rag.py
# Run namespace tests: docker run ragdoll python test_namespaced_system.py
