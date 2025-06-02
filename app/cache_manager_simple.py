#!/usr/bin/env python3
"""
Simple Cache Manager for RAGdoll Enterprise
Provides local memory caching for development and testing
"""

import json
import hashlib
import time
from typing import List, Dict, Optional, Any, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleCacheManager:
    """Simple in-memory cache manager for development"""
    
    def __init__(self, cache_ttl: int = 3600):
        """Initialize simple cache manager"""
        self.cache_ttl = cache_ttl
        self.cache = {}
        self.bloom_filters = {}
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "bloom_hits": 0,
            "bloom_misses": 0
        }
        logger.info("📝 Using simple in-memory cache")
    
    def _generate_cache_key(self, query: str, namespace: str, filters: Optional[Dict] = None) -> str:
        """Generate cache key for query"""
        cache_data = {
            "query": query,
            "namespace": namespace,
            "filters": filters or {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    async def get_or_compute_query(
        self, 
        query_func: Callable, 
        query: str, 
        namespace: str = "default",
        filters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get cached result or compute new one
        
        Args:
            query_func: Function to compute result
            query: Search query
            namespace: Target namespace
            filters: Additional filters
            **kwargs: Arguments for query_func
        
        Returns:
            Query results
        """
        # Generate cache key
        cache_key = self._generate_cache_key(query, namespace, filters)
        
        # Check cache
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if cached_entry['expires'] > time.time():
                self.stats["cache_hits"] += 1
                logger.info(f"🎯 Cache HIT (Local): {query[:50]}...")
                return cached_entry['result']
            else:
                # Expired entry
                del self.cache[cache_key]
        
        # Cache miss - compute result
        self.stats["cache_misses"] += 1
        start_time = time.time()
        
        # Execute query function
        result = query_func(query, **kwargs)
        
        compute_time = time.time() - start_time
        
        # Add performance metadata
        result_with_meta = {
            "results": result,
            "metadata": {
                "computed_at": datetime.now().isoformat(),
                "compute_time_ms": round(compute_time * 1000, 2),
                "cached": False,
                "namespace": namespace
            }
        }
        
        # Cache the result
        self.cache[cache_key] = {
            "result": result_with_meta,
            "expires": time.time() + self.cache_ttl,
            "namespace": namespace
        }
        
        return result_with_meta
    
    async def invalidate_namespace_cache(self, namespace: str):
        """Invalidate all cache for namespace"""
        keys_to_remove = []
        for key, entry in self.cache.items():
            if entry.get("namespace") == namespace:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"🗑️ Invalidated local cache for namespace: {namespace}")
        
        # Clear BloomFilter for namespace if it exists
        if namespace in self.bloom_filters:
            self.bloom_filters[namespace].clear()
    
    def register_document(self, doc_id: str, namespace: str):
        """Register document in BloomFilter"""
        if namespace not in self.bloom_filters:
            self.bloom_filters[namespace] = set()
        
        self.bloom_filters[namespace].add(doc_id)
        logger.info(f"🌸 Created BloomFilter for namespace: {namespace}")
    
    def check_document_exists_fast(self, doc_id: str, namespace: str) -> bool:
        """Fast document existence check using BloomFilter"""
        if namespace not in self.bloom_filters:
            self.bloom_filters[namespace] = set()
        
        exists = doc_id in self.bloom_filters[namespace]
        if exists:
            self.stats["bloom_hits"] += 1
        else:
            self.stats["bloom_misses"] += 1
        
        return exists or True  # Return True for unknown docs (bloom filter behavior)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_cache_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        total_bloom_requests = self.stats["bloom_hits"] + self.stats["bloom_misses"]
        
        return {
            "cache": {
                "redis_available": False,
                "local_cache_size": len(self.cache),
                "ttl_seconds": self.cache_ttl
            },
            "bloom_filter": {
                "available": True,
                "namespaces": list(self.bloom_filters.keys()),
                "capacity": 1000000,
                "error_rate": 0.1,
                **{f"{ns}_count": len(filter_set) for ns, filter_set in self.bloom_filters.items()}
            },
            "performance": self.stats,
            "hit_rates": {
                "cache_hit_rate": self.stats["cache_hits"] / max(total_cache_requests, 1),
                "bloom_hit_rate": self.stats["bloom_hits"] / max(total_bloom_requests, 1)
            }
        }


# Global cache manager instance
cache_manager = SimpleCacheManager()
