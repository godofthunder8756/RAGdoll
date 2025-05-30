# RAGdoll 🤖

A robust Retrieval-Augmented Generation (RAG) system using BGE-M3 embeddings and FAISS vector database. RAGdoll provides semantic document search and retrieval capabilities for building intelligent Q&A systems.

## Features

- **BGE-M3 Embeddings**: Multilingual, high-performance local embeddings (1024-dimensional)
- **FAISS Vector Database**: Fast similarity search with metadata storage
- **Document Processing**: Support for TXT and PDF files with intelligent chunking
- **Interactive Query Interface**: Command-line interface for real-time document retrieval
- **Metadata-Rich Storage**: Track document sources, chunks, and context
- **Robust Error Handling**: Graceful handling of file processing errors
- **Persistent Storage**: Automatic save/load of vector indexes

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd RAGdoll

# Install dependencies
pip install -r requirements.txt
```

### 2. Add Documents

Place your documents in the `data/` folder:
- **Supported formats**: `.txt`, `.pdf`
- The system will recursively scan subdirectories
- Example documents are included in the `data/` folder

### 3. Index Documents

```bash
python -m app.ingest
```

### 4. Query the System

```bash
# Interactive query interface
python -m app.query

# Or run programmatically
python test_rag.py
```

## Architecture

### Embedding Model

**BGE-M3 (BAAI/bge-m3)**
- **Multilingual support**: Works with 100+ languages
- **1024-dimensional embeddings**: High-quality semantic representations
- **Local execution**: No API calls required
- **Multi-granularity**: Handles short sentences to long documents (up to 8192 tokens)
- **Multi-functionality**: Dense retrieval, multi-vector, and sparse retrieval capabilities

### Vector Store

- **FAISS**: Facebook's similarity search library for fast vector operations
- **Metadata tracking**: Document source, chunk information, and full text storage
- **Persistent storage**: Automatic index save/load with `.faiss` and `.pkl` files
- **Efficient search**: L2 distance-based similarity with score conversion

### Document Processing

- **File support**: TXT and PDF files with recursive directory scanning
- **Intelligent chunking**: Configurable chunk size (512 tokens) with overlap (128 tokens)
- **Metadata preservation**: Filename, file type, chunk index, and full text
- **Error handling**: Graceful handling of corrupted or unreadable files

## Usage Examples

### Basic Query
```python
from app.query import RAGRetriever

retriever = RAGRetriever()
results = retriever.query("What is machine learning?", top_k=5)

for i, result in enumerate(results):
    print(f"{i+1}. Score: {result['score']:.3f}")
    print(f"   Source: {result['metadata']['filename']}")
    print(f"   Text: {result['text'][:200]}...")
```

### Interactive Mode
```bash
python -m app.query

# Example session:
💬 Enter your query: machine learning
🔍 Processing query: machine learning
✅ Found 3 relevant documents

1. Score: 0.6012
   Source: machine_learning.txt
   Chunk: 0
   Text: Machine Learning Fundamentals Machine learning is a subset...
```

### Programmatic Integration
```python
from app.embedder import embed_text
from app.vector_store import VectorStore

# Generate embeddings
texts = ["Your documents here"]
embeddings = embed_text(texts)

# Store in vector database
vs = VectorStore()
vs.add(embeddings, metadata_list)
vs.save()

# Search
query_embedding = embed_text(["search query"])[0]
indices, distances, metadata = vs.search(query_embedding, top_k=5)
```

## Project Structure

```
RAGdoll/
├── app/
│   ├── __init__.py
│   ├── embedder.py          # BGE-M3 embedding service
│   ├── vector_store.py      # FAISS vector database
│   ├── ingest.py           # Document ingestion pipeline
│   ├── query.py            # Query interface and retrieval
│   └── config.py           # Configuration settings
├── data/                   # Document storage directory
│   ├── machine_learning.txt
│   ├── python_guide.txt
│   └── vector_databases.txt
├── bge-m3_repo/           # Local BGE-M3 model files
├── test_rag.py            # Comprehensive test suite
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

## Testing

Run the comprehensive test suite:

```bash
python test_rag.py
```

This tests:
- **Embedding functionality**: BGE-M3 model loading and text encoding
- **Vector store operations**: Index creation, search, and persistence
- **RAG retrieval pipeline**: End-to-end document retrieval with scoring

## Docker Deployment

```bash
# Build the container
docker build -t ragdoll .

# Run with document volume
docker run -v /path/to/your/documents:/app/data ragdoll

# Interactive mode
docker run -it ragdoll python -m app.query
```

---
**© Aidan Ahern 2025**