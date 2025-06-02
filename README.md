# RAGdoll 🤖

A robust Retrieval-Augmented Generation (RAG) system using BGE-M3 embeddings and FAISS vector database. RAGdoll provides semantic document search and retrieval capabilities for building intelligent Q&A systems with **enterprise-grade namespace isolation** for large organizations.

## Features

- **BGE-M3 Embeddings**: Multilingual, high-performance local embeddings (1024-dimensional)
- **FAISS Vector Database**: Fast similarity search with metadata storage
- **🏢 Enterprise Namespaces**: True knowledge silo isolation with separate FAISS indices per namespace
- **Document Processing**: Support for TXT and PDF files with intelligent chunking
- **Interactive Query Interface**: Command-line interface for real-time document retrieval
- **Metadata-Rich Storage**: Track document sources, chunks, and context
- **Robust Error Handling**: Graceful handling of file processing errors
- **Persistent Storage**: Automatic save/load of vector indexes
- **🔧 Enterprise Management**: Namespace CRUD operations, backup/restore, analytics

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

**Auto-detect namespaces from folder structure:**
```bash
python -m app.ingest_namespaced --auto
```

**Ingest to specific namespace:**
```bash
python -m app.ingest_namespaced --namespace engineering --description "Engineering documentation"
```

**Legacy single-index mode:**
```bash
python -m app.ingest
```

### 4. Query the System

**Interactive namespaced query interface:**
```bash
python -m app.query_namespaced --interactive
```

**Query specific namespace:**
```bash
python -m app.query_namespaced --namespace legal --query "compliance requirements"
```

**Cross-namespace search:**
```bash
python -m app.query_namespaced --cross-namespace --query "documentation standards"
```

**Legacy single-index mode:**
```bash
python -m app.query
```

## Enterprise Namespace Management

### Create and Manage Namespaces

```bash
# Create a new namespace
python -m app.namespace_manager create legal --description "Legal documents" --department "Legal" --contact "legal@company.com"

# List all namespaces
python -m app.namespace_manager list --details

# Show namespace details
python -m app.namespace_manager details engineering

# Delete a namespace
python -m app.namespace_manager delete old_namespace --force
```

### Backup and Migration

```bash
# Backup a namespace
python -m app.namespace_manager backup legal --dir ./backups/legal_backup_20250530

# Restore from backup
python -m app.namespace_manager restore ./backups/legal_backup_20250530

# Clone a namespace
python -m app.namespace_manager clone engineering engineering_dev

# Migrate content between namespaces
python -m app.namespace_manager migrate old_legal legal --merge
```

### Analytics and Monitoring

```bash
# System overview
python -m app.namespace_manager overview

# Analyze overlap between namespaces
python -m app.namespace_manager overlap engineering legal --sample-size 100

# Filter namespaces by department
python -m app.namespace_manager list --department Engineering
```

## Architecture

### Namespace Isolation

**Enterprise Knowledge Silos**
- **Separate FAISS indices**: Each namespace gets its own `.faiss` and metadata files
- **True modularity**: Add/remove departments without affecting others
- **Folder-based organization**: Auto-detect namespaces from `data/hr/`, `data/legal/`, etc.
- **Cross-namespace search**: Query across silos when needed
- **Metadata tracking**: Department, contact, and access control information

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
from app.query_namespaced import NamespacedRAGRetriever

retriever = NamespacedRAGRetriever("engineering")
results = retriever.query("What is machine learning?", top_k=5)

for i, result in enumerate(results):
    print(f"{i+1}. Score: {result['score']:.3f}")
    print(f"   Source: {result['metadata']['filename']}")
    print(f"   Namespace: {result['namespace']}")
    print(f"   Text: {result['text'][:200]}...")
```

### Cross-Namespace Query
```python
from app.query_namespaced import MultiNamespaceRAGRetriever

multi_retriever = MultiNamespaceRAGRetriever()
results = multi_retriever.query_best_across_namespaces("documentation standards", top_k=5)

for result in results:
    print(f"Namespace: {result['namespace']}, Score: {result['score']:.3f}")
    print(f"Text: {result['text'][:200]}...")
```

### Interactive Mode
```bash
python -m app.query_namespaced --interactive

# Example session:
💬 [Multi-namespace] Enter your query: machine learning
🔍 [Multi-namespace] Processing query: machine learning
✅ Found 3 relevant documents across 2 namespaces

🏢 Namespace: engineering (2 results)
1. Score: 0.612
   Source: technical_standards.txt
   Text: Machine Learning best practices for our engineering team...

🏢 Namespace: default (1 results)
1. Score: 0.587
   Source: machine_learning.txt
   Text: Machine Learning Fundamentals...
```

### Enterprise Management
```python
from app.namespace_manager import EnterpriseNamespaceManager

manager = EnterpriseNamespaceManager()

# Create department-specific namespace
manager.create_namespace(
    "legal", 
    "Legal compliance documents", 
    tags=["compliance", "policy"],
    department="Legal",
    contact="legal@company.com"
)

# Analyze namespace overlap
overlap = manager.analyze_namespace_overlap("engineering", "legal", sample_size=100)
print(f"Average similarity: {overlap['average_similarity']}")

# Get system overview
overview = manager.get_system_overview()
print(f"Total namespaces: {overview['total_namespaces']}")
print(f"Total documents: {overview['total_documents']}")
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
│   ├── embedder.py              # BGE-M3 embedding service
│   ├── vector_store.py          # Legacy FAISS vector database
│   ├── namespaced_vector_store.py  # Enterprise namespaced vector store
│   ├── ingest.py               # Legacy document ingestion
│   ├── ingest_namespaced.py    # Namespaced document ingestion
│   ├── query.py                # Legacy query interface
│   ├── query_namespaced.py     # Namespaced query interface
│   ├── namespace_manager.py    # Enterprise namespace management CLI
│   ├── config.py               # Configuration settings
│   └── indexes/                # Directory for namespace-specific FAISS files
│       ├── engineering.faiss
│       ├── engineering_metadata.pkl
│       ├── legal.faiss
│       ├── legal_metadata.pkl
│       └── ...
├── data/                       # Document storage directory
│   ├── engineering/            # Auto-detected namespace
│   │   └── technical_standards.txt
│   ├── hr/                     # Auto-detected namespace
│   │   └── employee_handbook.txt
│   ├── legal/                  # Auto-detected namespace
│   │   └── compliance_guidelines.txt
│   ├── marketing/              # Auto-detected namespace
│   │   └── strategy_guidelines.txt
│   ├── machine_learning.txt    # Goes to 'default' namespace
│   ├── python_guide.txt
│   └── vector_databases.txt
├── bge-m3_repo/               # Local BGE-M3 model files
├── backups/                   # Namespace backup directory
├── test_rag.py               # Legacy test suite
├── test_namespaced_system.py # Comprehensive namespace test suite
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Multi-service orchestration
└── README.md               # This file
```

## Testing

Run the comprehensive test suite:

```bash
# Test namespaced system (recommended)
python test_namespaced_system.py

# Test legacy system
python test_rag.py
```

This tests:
- **Namespace isolation**: Separate FAISS indices per namespace
- **Enterprise management**: CRUD operations, backup/restore, analytics
- **Cross-namespace search**: Query across knowledge silos
- **Embedding functionality**: BGE-M3 model loading and text encoding
- **Vector store operations**: Index creation, search, and persistence
- **RAG retrieval pipeline**: End-to-end document retrieval with scoring

## Docker Deployment

```bash
# Build and run with Docker Compose (recommended)
docker-compose up --build

# Or build manually
docker build -t ragdoll .

# Run with document volume
docker run -v /path/to/your/documents:/app/data ragdoll

# Interactive namespace query mode
docker run -it ragdoll python -m app.query_namespaced --interactive

# Namespace management
docker run -it ragdoll python -m app.namespace_manager list --details
```

---
**© Aidan Ahern 2025**