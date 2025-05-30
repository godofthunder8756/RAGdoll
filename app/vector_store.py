import faiss
import numpy as np
import os
import json
import pickle
from typing import List, Dict, Tuple, Optional, Any
from app.config import VECTOR_STORE_PATH, EMBED_DIM

class VectorStore:
    def __init__(self, index_path: str = VECTOR_STORE_PATH):
        self.index_path = index_path
        self.metadata_path = index_path.replace('.faiss', '_metadata.pkl')
        self.index = None
        self.metadata = []
        self.load()
    
    def load(self):
        """Load FAISS index and metadata"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            print(f"Loaded FAISS index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(EMBED_DIM)
            print("Created new FAISS index")
        
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"Loaded metadata for {len(self.metadata)} chunks")
        else:
            self.metadata = []
    
    def save(self):
        """Save FAISS index and metadata"""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        print(f"Saved index with {self.index.ntotal} vectors and {len(self.metadata)} metadata entries")
    
    def add(self, embeddings: List[List[float]], metadata: Optional[List[Dict]] = None):
        """Add embeddings and metadata to the store"""
        np_embeddings = np.array(embeddings).astype('float32')
        self.index.add(np_embeddings)
        
        if metadata:
            self.metadata.extend(metadata)
        else:
            # Add empty metadata for each embedding
            self.metadata.extend([{}] * len(embeddings))
    
    def search(self, query_vector: List[float], top_k: int = 5) -> Tuple[List[int], List[float], List[Dict]]:
        """Search for similar vectors and return indices, scores, and metadata"""
        np_query = np.array([query_vector]).astype('float32')
        distances, indices = self.index.search(np_query, top_k)
        
        # Get metadata for results
        result_metadata = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                result_metadata.append(self.metadata[idx])
            else:
                result_metadata.append({})
        
        return indices[0].tolist(), distances[0].tolist(), result_metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'num_documents': self.index.ntotal if self.index else 0,
            'dimension': EMBED_DIM,
            'index_file': self.index_path,
            'metadata_entries': len(self.metadata)
        }

# Legacy functions for backward compatibility
def save_index(index, path=VECTOR_STORE_PATH):
    faiss.write_index(index, path)

def load_index(path=VECTOR_STORE_PATH):
    if os.path.exists(path):
        return faiss.read_index(path)
    return faiss.IndexFlatL2(EMBED_DIM)

def add_to_index(index, embeddings, metadata=None):
    np_embeddings = np.array(embeddings).astype('float32')
    index.add(np_embeddings)
    return index

def search(index, query_vector, top_k=5):
    np_query = np.array([query_vector]).astype('float32')
    D, I = index.search(np_query, top_k)
    return I[0], D[0]
