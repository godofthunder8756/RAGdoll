import os
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = "text-embedding-3-large"
VECTOR_STORE_PATH = "app/ragdoll_index.faiss"
DATA_DIR = "data"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional fallback

# BGE-M3 model configuration
LOCAL_EMBED_MODEL = "./bge-m3_repo"  # Use local model directory
EMBED_DIM = 1024                     # BGE-M3 produces 1024-dimensional embeddings
