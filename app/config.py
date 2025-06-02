import os
from dotenv import load_dotenv

load_dotenv()

# Offline mode configuration
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"
BGE_MODEL_PATH = os.getenv("BGE_MODEL_PATH", "./bge-m3_repo")

EMBED_MODEL = "text-embedding-3-large"
VECTOR_STORE_PATH = "app/ragdoll_index.faiss"
DATA_DIR = "data"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional fallback

# Namespace configuration for enterprise knowledge silos
NAMESPACED_INDEXES_DIR = "app/indexes"  # Directory for namespace-specific FAISS files
DEFAULT_NAMESPACE = "default"           # Default namespace if none specified
NAMESPACE_CONFIG_FILE = "app/namespace_config.json"  # Configuration for namespaces

# BGE-M3 model configuration (offline-first)
LOCAL_EMBED_MODEL = BGE_MODEL_PATH if OFFLINE_MODE else "./bge-m3_repo"
EMBED_DIM = 1024                     # BGE-M3 produces 1024-dimensional embeddings

# Cache configuration for sub-second performance
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")  # Redis connection
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))                  # Cache TTL in seconds (1 hour)
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
BLOOM_FILTER_CAPACITY = int(os.getenv("BLOOM_FILTER_CAPACITY", "1000000"))  # Expected docs
BLOOM_FILTER_ERROR_RATE = float(os.getenv("BLOOM_FILTER_ERROR_RATE", "0.1"))  # False positive rate

# Hybrid search configuration
ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", "0.3"))           # BM25 weight in hybrid search
VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", "0.7"))       # Vector weight in hybrid search
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "100"))          # Documents to rerank
