#!/usr/bin/env python3
"""
Enhanced Namespaced RAG Query Interface with Caching and Hybrid Search
Integrates vector search, keyword search, metadata filtering, and high-performance caching
"""

import argparse
import asyncio
import time
from typing import List, Dict, Any, Optional
import logging

from app.embedder import embed_text
from app.namespaced_vector_store import NamespacedVectorStore, MultiNamespaceVectorStore
from app.config import DEFAULT_NAMESPACE, ENABLE_CACHE, ENABLE_HYBRID_SEARCH
from app.cache_manager import cache_manager
from app.hybrid_search import hybrid_search_engine, SearchResult

logger = logging.getLogger(__name__)

class EnhancedNamespacedRAGRetriever:
    """
    Enhanced namespaced RAG retriever with caching and hybrid search capabilities
    """
    
    def __init__(self, namespace: str = DEFAULT_NAMESPACE):
        """
        Initialize the enhanced namespaced RAG retriever
        
        Args:
            namespace: Target namespace for queries
        """
        self.namespace = namespace
        self.vector_store = NamespacedVectorStore(namespace)
        self.hybrid_engine = hybrid_search_engine.get_engine(namespace)
        
        logger.info(f"🚀 Initialized enhanced retriever for namespace: {namespace}")
    
    async def query_async(self, query_text: str, top_k: int = 5, 
                         score_threshold: float = 0.0, 
                         filters: Dict[str, Any] = None,
                         use_hybrid: bool = None) -> List[Dict[str, Any]]:
        """
        Async query with caching and hybrid search support
        
        Args:
            query_text: The query string
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            filters: Metadata filters for search
            use_hybrid: Force hybrid search on/off
        
        Returns:
            List of enhanced search results
        """
        start_time = time.time()
        
        # Determine search method
        use_hybrid_search = (use_hybrid if use_hybrid is not None 
                           else ENABLE_HYBRID_SEARCH and self.hybrid_engine)
        
        logger.info(f"🔍 [{self.namespace}] Query: {query_text[:100]}...")
        logger.info(f"🔧 Using {'hybrid' if use_hybrid_search else 'vector'} search")
        
        try:
            if ENABLE_CACHE:
                # Try to get cached result
                cached_result = await cache_manager.get_or_compute_query(
                    query_func=self._execute_search,
                    query=query_text,
                    namespace=self.namespace,
                    filters=filters,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    use_hybrid=use_hybrid_search
                )
                
                if cached_result.get("metadata", {}).get("cached", True):
                    logger.info(f"⚡ Cache hit! Query time: {time.time() - start_time:.2f}s")
                    return cached_result["results"]
                else:
                    logger.info(f"🔍 Fresh search completed in: {cached_result['metadata']['compute_time_ms']}ms")
                    return cached_result["results"]
            else:
                # Direct search without caching
                results = self._execute_search(
                    query_text, top_k=top_k, score_threshold=score_threshold,
                    filters=filters, use_hybrid=use_hybrid_search
                )
                logger.info(f"🔍 Search completed in: {time.time() - start_time:.2f}s")
                return results
                
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
    
    def _execute_search(self, query_text: str, top_k: int = 5, 
                       score_threshold: float = 0.0,
                       filters: Dict[str, Any] = None,
                       use_hybrid: bool = False) -> List[Dict[str, Any]]:
        """Execute the actual search"""
        if use_hybrid and self.hybrid_engine:
            return self._hybrid_search(query_text, top_k, filters, score_threshold)
        else:
            return self._vector_search(query_text, top_k, score_threshold)
    
    def _hybrid_search(self, query_text: str, top_k: int, 
                      filters: Dict[str, Any], score_threshold: float) -> List[Dict[str, Any]]:
        """Execute hybrid search"""
        try:
            search_results = self.hybrid_engine.hybrid_search(
                query=query_text, 
                k=top_k, 
                filters=filters
            )
            
            # Convert to legacy format
            formatted_results = []
            for result in search_results:
                if result.hybrid_score >= score_threshold:
                    formatted_results.append({
                        'text': result.content,
                        'metadata': {
                            'filename': result.metadata.source_file,
                            'chunk_index': result.metadata.chunk_index,
                            'doc_id': result.metadata.doc_id,
                            'author': result.metadata.author,
                            'department': result.metadata.department,
                            'tags': result.metadata.tags,
                            'document_type': result.metadata.document_type,
                            'enhanced_metadata': True
                        },
                        'score': result.hybrid_score,
                        'vector_score': result.vector_score,
                        'bm25_score': result.bm25_score,
                        'keyword_matches': result.keyword_matches,
                        'namespace': self.namespace,
                        'search_type': 'hybrid'
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return self._vector_search(query_text, top_k, score_threshold)
    
    def _vector_search(self, query_text: str, top_k: int, score_threshold: float) -> List[Dict[str, Any]]:
        """Execute traditional vector search"""
        # Generate embedding for the query
        query_embeddings = embed_text([query_text])
        
        if query_embeddings is None or len(query_embeddings) == 0:
            logger.error("❌ Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]
        
        # Search the namespace-specific vector store
        indices, distances, metadata_list = self.vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by score threshold and format results
        filtered_results = []
        for i, (idx, distance, metadata) in enumerate(zip(indices, distances, metadata_list)):
            # Convert distance to similarity score (FAISS uses L2 distance)
            score = max(0, 1 - distance / 2)
            
            if score >= score_threshold:
                text = metadata.get('text', f'Document {idx}')
                
                filtered_results.append({
                    'text': text,
                    'metadata': metadata,
                    'score': score,
                    'namespace': self.namespace,
                    'search_type': 'vector'
                })
        
        return filtered_results
    
    def query(self, query_text: str, top_k: int = 5, score_threshold: float = 0.0,
              filters: Dict[str, Any] = None, use_hybrid: bool = None) -> List[Dict[str, Any]]:
        """
        Synchronous query wrapper for async functionality
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.query_async(query_text, top_k, score_threshold, filters, use_hybrid)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.query_async(query_text, top_k, score_threshold, filters, use_hybrid)
                )
        except Exception as e:
            logger.error(f"Sync query wrapper error: {e}")
            # Fallback to direct search
            return self._execute_search(query_text, top_k, score_threshold, filters, use_hybrid)
    
    def get_context(self, query_text: str, top_k: int = 3, 
                   max_context_length: int = 2000,
                   filters: Dict[str, Any] = None) -> str:
        """Get formatted context for RAG generation"""
        results = self.query(query_text, top_k=top_k, filters=filters)
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            text = result['text']
            metadata = result['metadata']
            score = result['score']
            search_type = result.get('search_type', 'vector')
            
            # Enhanced context formatting
            source_info = f"[Namespace: {self.namespace}, Source: {metadata.get('filename', 'Unknown')}"
            if metadata.get('author'):
                source_info += f", Author: {metadata['author']}"
            if metadata.get('department'):
                source_info += f", Dept: {metadata['department']}"
            source_info += f", Score: {score:.3f}, Type: {search_type}]"
            
            context_piece = f"Document {i} {source_info}:\n{text}\n"
            
            # Check if adding this would exceed max length
            if total_length + len(context_piece) > max_context_length and context_parts:
                break
                
            context_parts.append(context_piece)
            total_length += len(context_piece)
        
        return "\n".join(context_parts)
    
    def get_namespace_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics for the namespace"""
        analytics = {}
        
        # Basic vector store stats
        try:
            vector_stats = self.vector_store.get_stats()
            analytics['vector_store'] = vector_stats
        except Exception as e:
            logger.error(f"Error getting vector store stats: {e}")
        
        # Hybrid search analytics
        if self.hybrid_engine:
            try:
                search_analytics = self.hybrid_engine.get_search_analytics()
                analytics['search_analytics'] = search_analytics
            except Exception as e:
                logger.error(f"Error getting search analytics: {e}")
        
        # Cache statistics
        if ENABLE_CACHE:
            try:
                cache_stats = cache_manager.get_comprehensive_stats()
                analytics['cache_stats'] = cache_stats
            except Exception as e:
                logger.error(f"Error getting cache stats: {e}")
        
        return analytics


class EnhancedMultiNamespaceRAGRetriever:
    """
    Enhanced multi-namespace RAG retriever with cross-namespace capabilities
    """
    
    def __init__(self):
        """Initialize multi-namespace retriever"""
        self.retrievers = {}
        logger.info("🌐 Initialized enhanced multi-namespace retriever")
    
    def get_retriever(self, namespace: str) -> EnhancedNamespacedRAGRetriever:
        """Get or create retriever for namespace"""
        if namespace not in self.retrievers:
            self.retrievers[namespace] = EnhancedNamespacedRAGRetriever(namespace)
        return self.retrievers[namespace]
    
    async def query_namespace_async(self, query_text: str, namespace: str, 
                                   top_k: int = 5, score_threshold: float = 0.0,
                                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query a specific namespace asynchronously"""
        retriever = self.get_retriever(namespace)
        return await retriever.query_async(query_text, top_k, score_threshold, filters)
    
    async def query_multiple_namespaces_async(self, query_text: str, namespaces: List[str],
                                             top_k: int = 5, score_threshold: float = 0.0,
                                             filters: Dict[str, Any] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Query multiple namespaces asynchronously"""
        tasks = []
        for namespace in namespaces:
            task = self.query_namespace_async(query_text, namespace, top_k, score_threshold, filters)
            tasks.append((namespace, task))
        
        results = {}
        for namespace, task in tasks:
            try:
                results[namespace] = await task
            except Exception as e:
                logger.error(f"Error querying namespace {namespace}: {e}")
                results[namespace] = []
        
        return results
    
    def query_cross_namespace(self, query_text: str, namespaces: List[str] = None,
                             top_k: int = 5, score_threshold: float = 0.0,
                             filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Cross-namespace search with result aggregation and deduplication
        """
        try:
            if ENABLE_HYBRID_SEARCH:
                # Use hybrid search engine for cross-namespace search
                if namespaces:
                    search_results = hybrid_search_engine.search_multiple_namespaces(
                        query_text, namespaces, top_k, filters
                    )
                    
                    # Flatten and sort results
                    all_results = []
                    for namespace, results in search_results.items():
                        for result in results:
                            if result.hybrid_score >= score_threshold:
                                formatted_result = {
                                    'text': result.content,
                                    'metadata': {
                                        'filename': result.metadata.source_file,
                                        'namespace': namespace,
                                        'doc_id': result.metadata.doc_id,
                                        'author': result.metadata.author,
                                        'department': result.metadata.department,
                                    },
                                    'score': result.hybrid_score,
                                    'namespace': namespace,
                                    'search_type': 'hybrid_cross_namespace'
                                }
                                all_results.append(formatted_result)
                    
                    # Sort by score and return top results
                    all_results.sort(key=lambda x: x['score'], reverse=True)
                    return all_results[:top_k]
                else:
                    # Search all namespaces
                    search_results = hybrid_search_engine.search_all_namespaces(
                        query_text, top_k, filters
                    )
                    
                    formatted_results = []
                    for result in search_results:
                        if result.hybrid_score >= score_threshold:
                            formatted_result = {
                                'text': result.content,
                                'metadata': {
                                    'filename': result.metadata.source_file,
                                    'namespace': result.metadata.department or 'unknown',
                                    'doc_id': result.metadata.doc_id,
                                },
                                'score': result.hybrid_score,
                                'search_type': 'hybrid_all_namespaces'
                            }
                            formatted_results.append(formatted_result)
                    
                    return formatted_results
            else:
                # Fallback to traditional multi-namespace search
                return self._traditional_cross_namespace_search(
                    query_text, namespaces, top_k, score_threshold, filters
                )
                
        except Exception as e:
            logger.error(f"Cross-namespace search error: {e}")
            return []
    
    def _traditional_cross_namespace_search(self, query_text: str, namespaces: List[str],
                                           top_k: int, score_threshold: float,
                                           filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Traditional cross-namespace search fallback"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.query_multiple_namespaces_async(
                            query_text, namespaces or [], top_k, score_threshold, filters
                        )
                    )
                    results_dict = future.result()
            else:
                results_dict = loop.run_until_complete(
                    self.query_multiple_namespaces_async(
                        query_text, namespaces or [], top_k, score_threshold, filters
                    )
                )
            
            # Flatten and sort results
            all_results = []
            for namespace, results in results_dict.items():
                all_results.extend(results)
            
            # Sort by score and return top results
            all_results.sort(key=lambda x: x['score'], reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Traditional cross-namespace search error: {e}")
            return []

# Backward compatibility aliases
NamespacedRAGRetriever = EnhancedNamespacedRAGRetriever
MultiNamespaceRAGRetriever = EnhancedMultiNamespaceRAGRetriever
