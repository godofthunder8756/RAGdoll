from pathlib import Path
from typing import List, Optional
import logging
import numpy as np
import time
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from app.config import LOCAL_EMBED_MODEL, EMBED_DIM, OPENAI_API_KEY, EMBED_MODEL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Local BGE-M3 model -------------------------------------------------
_local_model_path = Path.home() / ".ragdoll_models" / LOCAL_EMBED_MODEL.replace("/", "_")
_model_instance = None

def _load_local_model():
    """Lazy loading of the BGE-M3 model to avoid loading on import."""
    global _model_instance
    if _model_instance is None:
        try:            # Try multiple model path options
            model_paths = [
                "/app/models/BAAI_bge-m3",  # Docker cached model location
                LOCAL_EMBED_MODEL,  # From config
                "./bge-m3_repo",
                "bge-m3_repo",
                "/app/bge-m3_repo",  # Docker model location
                "BAAI/bge-m3"  # Direct HuggingFace download
            ]
            
            model_loaded = False
            for model_path in model_paths:
                try:
                    if Path(model_path).exists():
                        logger.info(f"Loading BGE-M3 model from local directory: {model_path}")
                        _model_instance = SentenceTransformer(model_path)
                        model_loaded = True
                        break
                except Exception as e:
                    logger.warning(f"Failed to load model from {model_path}: {e}")
                    continue
              # If no local model found, download from HuggingFace
            if not model_loaded:
                logger.info(f"No local model found, downloading BAAI/bge-m3 from HuggingFace...")
                _model_instance = SentenceTransformer("BAAI/bge-m3", cache_folder=str(_local_model_path))
                model_loaded = True
            
            if model_loaded and _model_instance:
                logger.info(f"[RAGdoll] Successfully loaded BGE-M3 model with {_model_instance.get_sentence_embedding_dimension()} dimensions")
            else:
                raise RuntimeError("Could not load BGE-M3 model from any source")
                
        except Exception as e:
            logger.error(f"[RAGdoll] Failed to load local BGE-M3 model: {e}")
            _model_instance = None
    return _model_instance

def _embed_local(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Encode with the local BGE-M3 model and return 2-D Python lists (faiss needs float32).
    BGE-M3 is a multi-lingual model that produces 1024-dimensional embeddings.
    Supports batch processing for memory efficiency.
    """
    model = _load_local_model()
    if model is None:
        raise RuntimeError("Local BGE-M3 model is not available")
    
    # Process in batches to avoid memory issues
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            embeddings = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
            all_embeddings.extend(embeddings.astype("float32").tolist())
        except Exception as e:
            logger.error(f"Error encoding batch {i//batch_size + 1}: {e}")
            # Fallback: encode one by one for this batch
            for text in batch:
                try:
                    embedding = model.encode([text], show_progress_bar=False, convert_to_numpy=True)
                    all_embeddings.extend(embedding.astype("float32").tolist())
                except Exception as single_e:
                    logger.error(f"Failed to encode single text: {single_e}")
                    # Use zero vector as fallback
                    all_embeddings.append([0.0] * EMBED_DIM)
    
    return all_embeddings

# ---- Caching --------------------------------------------------------
@lru_cache(maxsize=1000)
def _cached_single_embed(text: str, use_local: bool = True) -> tuple:
    """Cache single text embeddings to avoid recomputation."""
    if use_local and LOCAL_EMBED_MODEL:
        return tuple(_embed_local([text])[0])
    elif OPENAI_API_KEY:
        return tuple(_embed_openai([text])[0])
    else:
        raise RuntimeError("No embedding backend configured!")

# ---- Optional OpenAI fallback ----------------------------------------
def _embed_openai(texts: List[str]) -> List[List[float]]:
    """
    Only used if an API key is present *and* LOCAL_EMBED_MODEL is None.
    Includes retry logic and rate limiting.
    """
    from openai import OpenAI
    import time
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Handle large batches by chunking (OpenAI has input limits)
    max_batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), max_batch_size):
        batch = texts[i:i + max_batch_size]
        
        # Retry logic for API calls
        for attempt in range(3):
            try:
                rsp = client.embeddings.create(model=EMBED_MODEL, input=batch)
                batch_embeddings = [r.embedding for r in rsp.data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    logger.error(f"Failed to get embeddings from OpenAI after 3 attempts")
                    # Use zero vectors as fallback
                    all_embeddings.extend([[0.0] * 1536] * len(batch))  # text-embedding-3-large is 1536-dim
                else:
                    time.sleep(2 ** attempt)  # Exponential backoff
    
    return all_embeddings

# ---- Public API ------------------------------------------------------
def embed_text(texts: List[str], use_cache: bool = False) -> List[List[float]]:
    """
    Try local BGE-M3 first. If you deliberately want OpenAI, set LOCAL_EMBED_MODEL = None.
    
    Args:
        texts: List of texts to embed
        use_cache: Use caching for single text embeddings (helpful for repeated queries)
    """
    if not texts:
        return []
    
    # Use cache for single texts if enabled
    if use_cache and len(texts) == 1:
        return [list(_cached_single_embed(texts[0], use_local=bool(LOCAL_EMBED_MODEL)))]
    
    if LOCAL_EMBED_MODEL:
        return _embed_local(texts)
    elif OPENAI_API_KEY:
        return _embed_openai(texts)
    else:
        raise RuntimeError("No embedding backend configured! Set LOCAL_EMBED_MODEL or OPENAI_API_KEY.")

def embed_query(query: str) -> List[float]:
    """
    Convenience function for embedding a single query with caching enabled.
    """
    return embed_text([query], use_cache=True)[0]

def get_model_info() -> dict:
    """
    Return information about the currently configured embedding model.
    """
    if LOCAL_EMBED_MODEL:
        model = _load_local_model()
        if model is not None:
            return {
                "type": "local",
                "model": "BAAI/bge-m3",
                "dimensions": model.get_sentence_embedding_dimension(),
                "path": LOCAL_EMBED_MODEL
            }
        else:
            return {"type": "local", "model": "BAAI/bge-m3", "status": "failed_to_load"}
    elif OPENAI_API_KEY:
        return {
            "type": "openai",
            "model": EMBED_MODEL,
            "dimensions": 3072 if EMBED_MODEL == "text-embedding-3-large" else 1536
        }
    else:
        return {"type": "none", "status": "no_backend_configured"}
