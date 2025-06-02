#!/usr/bin/env python3
"""
Hybrid Search Engine for RAGdoll Enterprise
Combines dense vector search (BGE-M3) with sparse keyword search (BM25) 
and advanced metadata filtering for superior document retrieval
"""

import json
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import pickle
import os

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from app.embedder import embed_text, embed_query
from app.config import (
    BM25_WEIGHT, VECTOR_WEIGHT, RERANK_TOP_K, 
    ENABLE_HYBRID_SEARCH, NAMESPACED_INDEXES_DIR
)

logger = logging.getLogger(__name__)

@dataclass
class DocumentMetadata:
    """Enhanced document metadata with search-optimized fields"""
    doc_id: str
    source_file: str
    chunk_index: int
    content: str
    content_length: int
    
    # Enhanced metadata fields
    title: Optional[str] = None
    author: Optional[str] = None
    department: Optional[str] = None
    document_type: Optional[str] = None
    tags: List[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    language: Optional[str] = "en"
    security_level: Optional[str] = "public"
    
    # Search optimization fields
    keyword_density: Optional[Dict[str, float]] = None
    semantic_keywords: List[str] = None
    topic_categories: List[str] = None
    reading_level: Optional[str] = None
    
    # Usage analytics
    access_count: int = 0
    last_accessed: Optional[str] = None
    avg_relevance_score: float = 0.0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.semantic_keywords is None:
            self.semantic_keywords = []
        if self.topic_categories is None:
            self.topic_categories = []
        if self.keyword_density is None:
            self.keyword_density = {}

@dataclass
class SearchResult:
    """Enhanced search result with hybrid scoring"""
    doc_id: str
    content: str
    metadata: DocumentMetadata
    
    # Hybrid scoring components
    vector_score: float
    bm25_score: float = 0.0
    hybrid_score: float = 0.0
    
    # Search context
    query_match_highlights: List[str] = None
    semantic_similarity: float = 0.0
    keyword_matches: List[str] = None
    
    def __post_init__(self):
        if self.query_match_highlights is None:
            self.query_match_highlights = []
        if self.keyword_matches is None:
            self.keyword_matches = []

class HybridSearchEngine:
    """Advanced hybrid search combining vector and keyword search"""
    
    def __init__(self, namespace: str = "default"):
        """Initialize hybrid search engine for namespace"""
        self.namespace = namespace
        # Use direct embedding functions instead of class instance
        # self.embedder will be replaced with direct function calls
        
        # Search components
        self.vector_index = None
        self.bm25_index = None
        self.documents = []
        self.metadata_index = {}
        
        # Search indexes
        self.keyword_to_docs = {}  # Inverted index for keywords
        self.tag_to_docs = {}      # Tag-based index
        self.author_to_docs = {}   # Author-based index
        self.dept_to_docs = {}     # Department-based index
        
        self._load_indexes()
    
    def _load_indexes(self):
        """Load all search indexes for the namespace"""
        try:
            # Load FAISS vector index
            vector_path = os.path.join(NAMESPACED_INDEXES_DIR, f"{self.namespace}.faiss")
            metadata_path = os.path.join(NAMESPACED_INDEXES_DIR, f"{self.namespace}_metadata.pkl")
            
            if os.path.exists(vector_path) and FAISS_AVAILABLE:
                self.vector_index = faiss.read_index(vector_path)
                logger.info(f"📡 Loaded FAISS index for {self.namespace}: {self.vector_index.ntotal} vectors")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    raw_metadata = pickle.load(f)
                    # Convert to enhanced metadata
                    self.documents = []
                    for item in raw_metadata:
                        if isinstance(item, dict):
                            # Legacy format - convert to DocumentMetadata
                            doc_meta = DocumentMetadata(
                                doc_id=item.get('doc_id', ''),
                                source_file=item.get('source_file', ''),
                                chunk_index=item.get('chunk_index', 0),
                                content=item.get('content', ''),
                                content_length=len(item.get('content', ''))
                            )
                        else:
                            doc_meta = item
                        
                        self.documents.append(doc_meta)
                        self.metadata_index[doc_meta.doc_id] = doc_meta
                
                logger.info(f"📚 Loaded {len(self.documents)} documents for {self.namespace}")
                
                # Build BM25 index if available
                if BM25_AVAILABLE and self.documents:
                    doc_texts = [doc.content for doc in self.documents]
                    tokenized_docs = [text.lower().split() for text in doc_texts]
                    self.bm25_index = BM25Okapi(tokenized_docs)
                    logger.info(f"🔍 Built BM25 index for {self.namespace}")
                
                # Build auxiliary indexes
                self._build_auxiliary_indexes()
                
        except Exception as e:
            logger.error(f"Error loading indexes for {self.namespace}: {e}")
    
    def _build_auxiliary_indexes(self):
        """Build keyword, tag, author, and department indexes"""
        self.keyword_to_docs.clear()
        self.tag_to_docs.clear()
        self.author_to_docs.clear()
        self.dept_to_docs.clear()
        
        for doc in self.documents:
            # Keyword index
            words = doc.content.lower().split()
            for word in set(words):  # Unique words only
                if word not in self.keyword_to_docs:
                    self.keyword_to_docs[word] = []
                self.keyword_to_docs[word].append(doc.doc_id)
            
            # Tag index
            for tag in doc.tags:
                if tag not in self.tag_to_docs:
                    self.tag_to_docs[tag] = []
                self.tag_to_docs[tag].append(doc.doc_id)
            
            # Author index
            if doc.author:
                if doc.author not in self.author_to_docs:
                    self.author_to_docs[doc.author] = []
                self.author_to_docs[doc.author].append(doc.doc_id)
            
            # Department index
            if doc.department:
                if doc.department not in self.dept_to_docs:
                    self.dept_to_docs[doc.department] = []
                self.dept_to_docs[doc.department].append(doc.doc_id)
        
        logger.info(f"🗂️ Built auxiliary indexes: {len(self.keyword_to_docs)} keywords, "
                   f"{len(self.tag_to_docs)} tags, {len(self.author_to_docs)} authors")
    
    def vector_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """Perform dense vector search"""
        if not self.vector_index or not FAISS_AVAILABLE:
            return []
        
        try:
            # Embed query
            query_vector = embed_query(query)
            query_vector = np.array([query_vector], dtype=np.float32)
            
            # Search
            scores, indices = self.vector_index.search(query_vector, k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append((doc.doc_id, float(score)))
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def keyword_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """Perform BM25 keyword search"""
        if not self.bm25_index or not BM25_AVAILABLE:
            return self._simple_keyword_search(query, k)
        
        try:
            query_tokens = query.lower().split()
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k results
            doc_scores = [(self.documents[i].doc_id, score) 
                         for i, score in enumerate(scores)]
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            return doc_scores[:k]
            
        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return self._simple_keyword_search(query, k)
    
    def _simple_keyword_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """Fallback simple keyword search using inverted index"""
        query_words = set(query.lower().split())
        doc_scores = {}
        
        for word in query_words:
            if word in self.keyword_to_docs:
                for doc_id in self.keyword_to_docs[word]:
                    if doc_id not in doc_scores:
                        doc_scores[doc_id] = 0
                    doc_scores[doc_id] += 1
        
        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:k]
    
    def metadata_filter(self, filters: Dict[str, Any]) -> List[str]:
        """Apply metadata filters to get candidate document IDs"""
        candidate_docs = set()
        
        # Apply filters
        for filter_key, filter_value in filters.items():
            matching_docs = set()
            
            if filter_key == "author" and filter_value in self.author_to_docs:
                matching_docs.update(self.author_to_docs[filter_value])
            
            elif filter_key == "department" and filter_value in self.dept_to_docs:
                matching_docs.update(self.dept_to_docs[filter_value])
            
            elif filter_key == "tags":
                if isinstance(filter_value, list):
                    for tag in filter_value:
                        if tag in self.tag_to_docs:
                            matching_docs.update(self.tag_to_docs[tag])
                elif filter_value in self.tag_to_docs:
                    matching_docs.update(self.tag_to_docs[filter_value])
            
            elif filter_key == "document_type":
                for doc in self.documents:
                    if doc.document_type == filter_value:
                        matching_docs.add(doc.doc_id)
            
            elif filter_key == "security_level":
                for doc in self.documents:
                    if doc.security_level == filter_value:
                        matching_docs.add(doc.doc_id)
            
            elif filter_key == "created_after":
                # Date filtering
                for doc in self.documents:
                    if doc.created_date and doc.created_date >= filter_value:
                        matching_docs.add(doc.doc_id)
            
            # Intersect with previous results (AND logic)
            if candidate_docs:
                candidate_docs = candidate_docs.intersection(matching_docs)
            else:
                candidate_docs = matching_docs
        
        return list(candidate_docs)
    
    def hybrid_search(self, query: str, k: int = 10, filters: Dict[str, Any] = None) -> List[SearchResult]:
        """
        Perform hybrid search combining vector, keyword, and metadata filtering
        """
        try:
            # Apply metadata filters first if provided
            candidate_doc_ids = None
            if filters:
                candidate_doc_ids = set(self.metadata_filter(filters))
                if not candidate_doc_ids:
                    return []  # No documents match filters
            
            # Get results from both search methods
            vector_results = self.vector_search(query, k=RERANK_TOP_K)
            keyword_results = self.keyword_search(query, k=RERANK_TOP_K)
            
            # Apply filters to search results if needed
            if candidate_doc_ids:
                vector_results = [(doc_id, score) for doc_id, score in vector_results 
                                if doc_id in candidate_doc_ids]
                keyword_results = [(doc_id, score) for doc_id, score in keyword_results 
                                 if doc_id in candidate_doc_ids]
            
            # Normalize scores
            vector_results = self._normalize_scores(vector_results)
            keyword_results = self._normalize_scores(keyword_results)
            
            # Combine scores
            combined_scores = {}
            
            # Add vector scores
            for doc_id, score in vector_results:
                combined_scores[doc_id] = {
                    'vector_score': score,
                    'bm25_score': 0.0
                }
            
            # Add BM25 scores
            for doc_id, score in keyword_results:
                if doc_id not in combined_scores:
                    combined_scores[doc_id] = {
                        'vector_score': 0.0,
                        'bm25_score': score
                    }
                else:
                    combined_scores[doc_id]['bm25_score'] = score
            
            # Calculate hybrid scores
            hybrid_results = []
            for doc_id, scores in combined_scores.items():
                if doc_id in self.metadata_index:
                    doc_meta = self.metadata_index[doc_id]
                    
                    # Calculate hybrid score
                    hybrid_score = (VECTOR_WEIGHT * scores['vector_score'] + 
                                  BM25_WEIGHT * scores['bm25_score'])
                    
                    # Create search result
                    result = SearchResult(
                        doc_id=doc_id,
                        content=doc_meta.content,
                        metadata=doc_meta,
                        vector_score=scores['vector_score'],
                        bm25_score=scores['bm25_score'],
                        hybrid_score=hybrid_score,
                        semantic_similarity=scores['vector_score'],
                        keyword_matches=self._find_keyword_matches(query, doc_meta.content)
                    )
                    
                    # Update access analytics
                    doc_meta.access_count += 1
                    doc_meta.last_accessed = datetime.now().isoformat()
                    
                    hybrid_results.append(result)
            
            # Sort by hybrid score and return top-k
            hybrid_results.sort(key=lambda x: x.hybrid_score, reverse=True)
            return hybrid_results[:k]
            
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []
    
    def _normalize_scores(self, results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Normalize scores to 0-1 range"""
        if not results:
            return results
        
        scores = [score for _, score in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [(doc_id, 1.0) for doc_id, _ in results]
        
        normalized = []
        for doc_id, score in results:
            norm_score = (score - min_score) / (max_score - min_score)
            normalized.append((doc_id, norm_score))
        
        return normalized
    
    def _find_keyword_matches(self, query: str, content: str) -> List[str]:
        """Find keyword matches in content"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        return list(query_words.intersection(content_words))
    
    def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics for the namespace"""
        if not self.documents:
            return {}
        
        total_docs = len(self.documents)
        total_accesses = sum(doc.access_count for doc in self.documents)
        
        # Most accessed documents
        most_accessed = sorted(self.documents, key=lambda x: x.access_count, reverse=True)[:10]
        
        # Document type distribution
        doc_types = {}
        for doc in self.documents:
            doc_type = doc.document_type or "unknown"
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        # Department distribution
        departments = {}
        for doc in self.documents:
            dept = doc.department or "unknown"
            departments[dept] = departments.get(dept, 0) + 1
        
        return {
            "namespace": self.namespace,
            "total_documents": total_docs,
            "total_accesses": total_accesses,
            "avg_accesses_per_doc": total_accesses / total_docs if total_docs > 0 else 0,
            "most_accessed_docs": [
                {
                    "doc_id": doc.doc_id,
                    "source_file": doc.source_file,
                    "access_count": doc.access_count,
                    "last_accessed": doc.last_accessed
                }
                for doc in most_accessed
            ],
            "document_types": doc_types,
            "departments": departments,
            "search_capabilities": {
                "vector_search": self.vector_index is not None,
                "bm25_search": self.bm25_index is not None,
                "metadata_filtering": True,
                "hybrid_search": ENABLE_HYBRID_SEARCH
            }
        }


class MultiNamespaceHybridSearchEngine:
    """Hybrid search across multiple namespaces"""
    
    def __init__(self):
        self.namespace_engines = {}
    
    def get_engine(self, namespace: str) -> HybridSearchEngine:
        """Get or create search engine for namespace"""
        if namespace not in self.namespace_engines:
            self.namespace_engines[namespace] = HybridSearchEngine(namespace)
        return self.namespace_engines[namespace]
    
    def search_single_namespace(self, query: str, namespace: str, k: int = 10, 
                               filters: Dict[str, Any] = None) -> List[SearchResult]:
        """Search within a single namespace"""
        engine = self.get_engine(namespace)
        return engine.hybrid_search(query, k, filters)
    
    def search_multiple_namespaces(self, query: str, namespaces: List[str], 
                                  k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, List[SearchResult]]:
        """Search across multiple namespaces"""
        results = {}
        
        for namespace in namespaces:
            try:
                engine = self.get_engine(namespace)
                namespace_results = engine.hybrid_search(query, k, filters)
                results[namespace] = namespace_results
            except Exception as e:
                logger.error(f"Error searching namespace {namespace}: {e}")
                results[namespace] = []
        
        return results
    
    def search_all_namespaces(self, query: str, k: int = 10, 
                             filters: Dict[str, Any] = None) -> List[SearchResult]:
        """Search across all available namespaces and merge results"""
        # Find all available namespaces
        namespaces = []
        if os.path.exists(NAMESPACED_INDEXES_DIR):
            for file in os.listdir(NAMESPACED_INDEXES_DIR):
                if file.endswith('.faiss'):
                    namespace = file.replace('.faiss', '')
                    namespaces.append(namespace)
        
        if not namespaces:
            return []
        
        # Search all namespaces
        all_results = []
        for namespace in namespaces:
            try:
                engine = self.get_engine(namespace)
                namespace_results = engine.hybrid_search(query, k * 2, filters)  # Get more results for merging
                
                # Add namespace info to results
                for result in namespace_results:
                    result.metadata.department = result.metadata.department or namespace
                    all_results.append(result)
                    
            except Exception as e:
                logger.error(f"Error searching namespace {namespace}: {e}")
        
        # Sort all results by hybrid score and return top-k
        all_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        return all_results[:k]

# Global hybrid search engine
hybrid_search_engine = MultiNamespaceHybridSearchEngine()
