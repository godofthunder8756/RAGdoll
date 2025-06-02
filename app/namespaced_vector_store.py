"""
Namespaced Vector Store for RAGdoll
Enables modular knowledge silos for large organizations
Each namespace maintains its own FAISS index and metadata
"""

import faiss
import numpy as np
import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Set
from datetime import datetime
from app.config import NAMESPACED_INDEXES_DIR, DEFAULT_NAMESPACE, NAMESPACE_CONFIG_FILE, EMBED_DIM


class NamespaceManager:
    """Manages namespace configuration and metadata"""
    
    def __init__(self, config_file: str = NAMESPACE_CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_config()
        self._ensure_indexes_dir()
    
    def _load_config(self) -> Dict:
        """Load namespace configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default configuration
            default_config = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "namespaces": {
                    DEFAULT_NAMESPACE: {
                        "description": "Default namespace for general documents",
                        "created": datetime.now().isoformat(),
                        "document_count": 0,
                        "chunk_count": 0,
                        "tags": ["general"]
                    }
                }
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict):
        """Save namespace configuration to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        self.config = config
    
    def _ensure_indexes_dir(self):
        """Ensure the indexes directory exists"""
        os.makedirs(NAMESPACED_INDEXES_DIR, exist_ok=True)
    
    def create_namespace(self, namespace: str, description: str = "", tags: List[str] = None) -> bool:
        """Create a new namespace"""
        if namespace in self.config["namespaces"]:
            print(f"Namespace '{namespace}' already exists")
            return False
        
        self.config["namespaces"][namespace] = {
            "description": description,
            "created": datetime.now().isoformat(),
            "document_count": 0,
            "chunk_count": 0,
            "tags": tags or []
        }
        self._save_config(self.config)
        print(f"Created namespace: {namespace}")
        return True
    
    def delete_namespace(self, namespace: str, force: bool = False) -> bool:
        """Delete a namespace and its associated files"""
        if namespace not in self.config["namespaces"]:
            print(f"Namespace '{namespace}' does not exist")
            return False
        
        if namespace == DEFAULT_NAMESPACE and not force:
            print(f"Cannot delete default namespace without force=True")
            return False
        
        # Delete FAISS files
        index_path = self._get_index_path(namespace)
        metadata_path = self._get_metadata_path(namespace)
        
        for path in [index_path, metadata_path]:
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted: {path}")
        
        # Remove from config
        del self.config["namespaces"][namespace]
        self._save_config(self.config)
        print(f"Deleted namespace: {namespace}")
        return True
    
    def list_namespaces(self) -> List[str]:
        """List all available namespaces"""
        return list(self.config["namespaces"].keys())
    
    def get_namespace_info(self, namespace: str) -> Optional[Dict]:
        """Get information about a specific namespace"""
        return self.config["namespaces"].get(namespace)
    
    def update_namespace_stats(self, namespace: str, document_count: int, chunk_count: int):
        """Update document and chunk counts for a namespace"""
        if namespace in self.config["namespaces"]:
            self.config["namespaces"][namespace]["document_count"] = document_count
            self.config["namespaces"][namespace]["chunk_count"] = chunk_count
            self.config["namespaces"][namespace]["last_updated"] = datetime.now().isoformat()
            self._save_config(self.config)
    
    def _get_index_path(self, namespace: str) -> str:
        """Get the FAISS index file path for a namespace"""
        return os.path.join(NAMESPACED_INDEXES_DIR, f"{namespace}.faiss")
    
    def _get_metadata_path(self, namespace: str) -> str:
        """Get the metadata file path for a namespace"""
        return os.path.join(NAMESPACED_INDEXES_DIR, f"{namespace}_metadata.pkl")


class NamespacedVectorStore:
    """
    Namespaced Vector Store that manages multiple FAISS indices
    Each namespace is a separate knowledge silo with its own index
    """
    
    def __init__(self, namespace: str = DEFAULT_NAMESPACE):
        self.namespace = namespace
        self.namespace_manager = NamespaceManager()
        self.index = None
        self.metadata = []
        
        # Ensure namespace exists
        if namespace not in self.namespace_manager.list_namespaces():
            self.namespace_manager.create_namespace(
                namespace, 
                f"Auto-created namespace: {namespace}"
            )
        
        self.index_path = self._get_index_path()
        self.metadata_path = self._get_metadata_path()
        self.load()
    
    def _get_index_path(self) -> str:
        """Get the FAISS index file path for current namespace"""
        return self.namespace_manager._get_index_path(self.namespace)
    
    def _get_metadata_path(self) -> str:
        """Get the metadata file path for current namespace"""
        return self.namespace_manager._get_metadata_path(self.namespace)
    
    def load(self):
        """Load FAISS index and metadata for current namespace"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            print(f"[{self.namespace}] Loaded FAISS index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(EMBED_DIM)
            print(f"[{self.namespace}] Created new FAISS index")
        
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"[{self.namespace}] Loaded metadata for {len(self.metadata)} chunks")
        else:
            self.metadata = []
    
    def save(self):
        """Save FAISS index and metadata for current namespace"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        # Update namespace statistics
        doc_count = len(set(m.get('filename', '') for m in self.metadata))
        chunk_count = len(self.metadata)
        self.namespace_manager.update_namespace_stats(self.namespace, doc_count, chunk_count)
        
        print(f"[{self.namespace}] Saved index with {self.index.ntotal} vectors and {len(self.metadata)} metadata entries")
    
    def add(self, embeddings: List[List[float]], metadata: Optional[List[Dict]] = None):
        """Add embeddings and metadata to the current namespace"""
        np_embeddings = np.array(embeddings).astype('float32')
        self.index.add(np_embeddings)
        
        if metadata:
            # Add namespace to metadata
            for meta in metadata:
                meta['namespace'] = self.namespace
            self.metadata.extend(metadata)
        else:
            # Add empty metadata with namespace for each embedding
            self.metadata.extend([{'namespace': self.namespace}] * len(embeddings))
    
    def search(self, query_vector: List[float], top_k: int = 5) -> Tuple[List[int], List[float], List[Dict]]:
        """Search for similar vectors within the current namespace"""
        if self.index.ntotal == 0:
            return [], [], []
        
        np_query = np.array([query_vector]).astype('float32')
        distances, indices = self.index.search(np_query, min(top_k, self.index.ntotal))
        
        # Get metadata for results
        result_metadata = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                result_metadata.append(self.metadata[idx])
            else:
                result_metadata.append({'namespace': self.namespace})
        
        return indices[0].tolist(), distances[0].tolist(), result_metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current namespace"""
        namespace_info = self.namespace_manager.get_namespace_info(self.namespace)
        return {
            'namespace': self.namespace,
            'num_documents': self.index.ntotal if self.index else 0,
            'dimension': EMBED_DIM,
            'index_file': self.index_path,
            'metadata_entries': len(self.metadata),
            'namespace_info': namespace_info
        }
    
    def clear_namespace(self):
        """Clear all data in the current namespace"""
        self.index = faiss.IndexFlatL2(EMBED_DIM)
        self.metadata = []
        print(f"[{self.namespace}] Cleared all data")


class MultiNamespaceVectorStore:
    """
    Multi-namespace vector store that can search across namespaces
    Useful for cross-silo queries in large organizations
    """
    
    def __init__(self):
        self.namespace_manager = NamespaceManager()
        self._stores = {}  # Cache of loaded stores
    
    def get_store(self, namespace: str) -> NamespacedVectorStore:
        """Get or create a vector store for a specific namespace"""
        if namespace not in self._stores:
            self._stores[namespace] = NamespacedVectorStore(namespace)
        return self._stores[namespace]
    
    def search_all_namespaces(self, query_vector: List[float], top_k: int = 5, 
                             namespace_filter: Optional[List[str]] = None) -> Dict[str, Tuple[List[int], List[float], List[Dict]]]:
        """Search across multiple namespaces"""
        results = {}
        namespaces = namespace_filter or self.namespace_manager.list_namespaces()
        
        for namespace in namespaces:
            store = self.get_store(namespace)
            indices, distances, metadata = store.search(query_vector, top_k)
            if indices:  # Only include namespaces with results
                results[namespace] = (indices, distances, metadata)
        
        return results
    
    def search_best_across_namespaces(self, query_vector: List[float], top_k: int = 5,
                                    namespace_filter: Optional[List[str]] = None) -> Tuple[List[int], List[float], List[Dict]]:
        """Search across namespaces and return the best results overall"""
        all_results = []
        namespaces = namespace_filter or self.namespace_manager.list_namespaces()
        
        for namespace in namespaces:
            store = self.get_store(namespace)
            indices, distances, metadata = store.search(query_vector, top_k * 2)  # Get more results per namespace
            
            for idx, dist, meta in zip(indices, distances, metadata):
                all_results.append((dist, idx, meta, namespace))
        
        # Sort by distance (lower is better) and take top_k
        all_results.sort(key=lambda x: x[0])
        best_results = all_results[:top_k]
        
        if not best_results:
            return [], [], []
        
        # Separate the results
        distances = [r[0] for r in best_results]
        indices = [r[1] for r in best_results]
        metadata = [r[2] for r in best_results]
        
        return indices, distances, metadata
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all namespaces"""
        stats = {}
        for namespace in self.namespace_manager.list_namespaces():
            store = self.get_store(namespace)
            stats[namespace] = store.get_stats()
        return stats
    
    def create_namespace(self, namespace: str, description: str = "", tags: List[str] = None) -> bool:
        """Create a new namespace"""
        return self.namespace_manager.create_namespace(namespace, description, tags)
    
    def delete_namespace(self, namespace: str, force: bool = False) -> bool:
        """Delete a namespace"""
        # Remove from cache if loaded
        if namespace in self._stores:
            del self._stores[namespace]
        return self.namespace_manager.delete_namespace(namespace, force)
    
    def list_namespaces(self) -> List[str]:
        """List all namespaces"""
        return self.namespace_manager.list_namespaces()
