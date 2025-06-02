#!/usr/bin/env python3
"""
Fixed Cache Manager for RAGdoll Enterprise
Provides Redis-based caching with proper async handling and fallback support
"""

import json
import hashlib
import time
import asyncio
from typing import Dict, Optional, Any, Union
import logging
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        REDIS_AVAILABLE = True
    except ImportError:
        redis = None
        REDIS_AVAILABLE = False

try:
    from pybloom_live import BloomFilter as PyBloomFilter
    BLOOM_AVAILABLE = True
except ImportError:
    PyBloomFilter = None
    BLOOM_AVAILABLE = False

from app.config import CACHE_TTL, REDIS_URL

logger = logging.getLogger(__name__)

class QueryCache:
    """High-performance query result caching with Redis backend"""
    
    def __init__(self, redis_url: Optional[str] = None, ttl: int = 3600):
        """Initialize cache manager with Redis support"""
        self.ttl = ttl
        self.redis_client = None
        self.local_cache = {}
        self.max_local_cache = 1000
        
        # Initialize Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                if hasattr(redis, 'from_url'):
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                else:
                    # Fallback for regular redis
                    self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                logger.info("✅ Redis cache initialized")
            except Exception as e:
                logger.warning(f"❌ Redis initialization failed: {e}. Using local cache.")
                self.redis_client = None
        else:
            logger.info("📝 Using local memory cache (Redis not available)")
    
    def _hash_query(self, query: str, namespace: str = "", filters: Optional[Dict] = None) -> str:
        """Generate cache key for query"""
        cache_data = {
            "query": query,
            "namespace": namespace,
            "filters": filters or {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    async def get_cached_result(self, query: str, namespace: str = "", 
                               filters: Optional[Dict] = None) -> Optional[Dict]:
        """Get cached query result"""
        cache_key = f"query:{self._hash_query(query, namespace, filters)}"
        
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.get(cache_key)
                    if cached_data:
                        result = json.loads(cached_data)
                        logger.info(f"🎯 Cache HIT (Redis): {query[:50]}...")
                        return result
                except Exception as e:
                    logger.warning(f"Redis get error: {e}")
            
            # Fallback to local cache
            if cache_key in self.local_cache:
                cached_entry = self.local_cache[cache_key]
                if cached_entry['expires'] > time.time():
                    logger.info(f"🎯 Cache HIT (Local): {query[:50]}...")
                    return cached_entry['data']
                else:
                    del self.local_cache[cache_key]
            
            logger.debug(f"❌ Cache MISS: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def cache_result(self, query: str, result: Dict, namespace: str = "", 
                          filters: Optional[Dict] = None):
        """Cache query result"""
        cache_key = f"query:{self._hash_query(query, namespace, filters)}"
        
        try:
            cached_data = {
                "result": result,
                "cached_at": datetime.now().isoformat(),
                "query": query[:100],
                "namespace": namespace
            }
            
            # Try Redis first
            if self.redis_client:
                try:
                    await self.redis_client.setex(
                        cache_key, 
                        self.ttl, 
                        json.dumps(cached_data, default=str)
                    )
                    logger.debug(f"💾 Cached to Redis: {query[:50]}...")
                    return
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
            
            # Fallback to local cache
            if len(self.local_cache) >= self.max_local_cache:
                oldest_keys = sorted(
                    self.local_cache.keys(),
                    key=lambda k: self.local_cache[k]['cached_at']
                )[:100]
                for key in oldest_keys:
                    del self.local_cache[key]
            
            self.local_cache[cache_key] = {
                "data": cached_data,
                "expires": time.time() + self.ttl,
                "cached_at": time.time()
            }
            logger.debug(f"💾 Cached locally: {query[:50]}...")
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def invalidate_namespace(self, namespace: str):
        """Invalidate all cached results for a namespace"""
        try:
            if self.redis_client:
                try:
                    pattern = f"query:*"
                    keys = await self.redis_client.keys(pattern)
                    
                    for key in keys:
                        cached_data = await self.redis_client.get(key)
                        if cached_data:
                            data = json.loads(cached_data)
                            if data.get("namespace") == namespace:
                                await self.redis_client.delete(key)
                    
                    logger.info(f"🗑️ Invalidated Redis cache for namespace: {namespace}")
                except Exception as e:
                    logger.warning(f"Redis invalidation error: {e}")
            
            # Clean local cache
            keys_to_remove = []
            for key, entry in self.local_cache.items():
                if entry['data'].get("namespace") == namespace:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.local_cache[key]
            
            logger.info(f"🗑️ Invalidated local cache for namespace: {namespace}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "redis_available": self.redis_client is not None,
            "local_cache_size": len(self.local_cache),
            "ttl_seconds": self.ttl
        }
        
        try:
            if self.redis_client:
                info = await self.redis_client.info()
                stats.update({
                    "redis_memory_used": info.get("used_memory_human", "Unknown"),
                    "redis_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0,
                    "redis_connected_clients": info.get("connected_clients", 0)
                })
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            
        return stats


class DocumentBloomFilter:
    """BloomFilter for fast document existence checks"""
    
    def __init__(self, capacity: int = 1000000, error_rate: float = 0.1):
        self.capacity = capacity
        self.error_rate = error_rate
        self.bloom_filters = {}
        
        if not BLOOM_AVAILABLE:
            logger.warning("⚠️ pybloom_live not available. Document existence checks will be slower.")
    
    def _get_namespace_filter(self, namespace: str):
        """Get or create BloomFilter for namespace"""
        if not BLOOM_AVAILABLE:
            return None
            
        if namespace not in self.bloom_filters:
            try:
                self.bloom_filters[namespace] = PyBloomFilter(
                    capacity=self.capacity,
                    error_rate=self.error_rate
                )
                logger.info(f"🌸 Created BloomFilter for namespace: {namespace}")
            except Exception as e:
                logger.error(f"Error creating BloomFilter: {e}")
                return None
        
        return self.bloom_filters[namespace]
    
    def add_document(self, doc_id: str, namespace: str = "default"):
        """Add document to BloomFilter"""
        bloom_filter = self._get_namespace_filter(namespace)
        if bloom_filter:
            bloom_filter.add(doc_id)
            logger.debug(f"🌸 Added document to BloomFilter: {doc_id}")
    
    def might_contain(self, doc_id: str, namespace: str = "default") -> bool:
        """Check if document might exist"""
        bloom_filter = self._get_namespace_filter(namespace)
        if bloom_filter:
            return doc_id in bloom_filter
        return True
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get BloomFilter statistics"""
        if not BLOOM_AVAILABLE:
            return {"available": False}
        
        stats = {
            "available": True,
            "namespaces": list(self.bloom_filters.keys()),
            "capacity": self.capacity,
            "error_rate": self.error_rate
        }
        
        for namespace, bloom_filter in self.bloom_filters.items():
            try:
                stats[f"{namespace}_count"] = len(bloom_filter)
            except:
                stats[f"{namespace}_count"] = "unknown"
        
        return stats


class CacheManager:
    """Combined cache management for queries and document existence"""
    
    def __init__(self, redis_url: Optional[str] = None, cache_ttl: int = 3600):
        """Initialize cache manager"""
        self.query_cache = QueryCache(redis_url, cache_ttl)
        self.bloom_filter = DocumentBloomFilter()
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "bloom_hits": 0,
            "bloom_misses": 0
        }
    
    async def get_or_compute_query(self, query_func, query: str, namespace: str = "", 
                                  filters: Optional[Dict] = None, **kwargs) -> Dict:
        """Get cached result or compute and cache"""
        # Try cache first
        cached_result = await self.query_cache.get_cached_result(query, namespace, filters)
        if cached_result:
            self.stats["cache_hits"] += 1
            return cached_result["result"]
        
        # Cache miss - compute result
        self.stats["cache_misses"] += 1
        start_time = time.time()
        
        # Execute query function with parameters
        try:
            if asyncio.iscoroutinefunction(query_func):
                result = await query_func(query, **kwargs)
            else:
                result = query_func(query, **kwargs)
        except Exception as e:
            logger.error(f"Query function error: {e}")
            raise
        
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
        await self.query_cache.cache_result(query, result_with_meta, namespace, filters)
        
        return result_with_meta
    
    def check_document_exists_fast(self, doc_id: str, namespace: str = "default") -> bool:
        """Fast document existence check using BloomFilter"""
        exists = self.bloom_filter.might_contain(doc_id, namespace)
        
        if exists:
            self.stats["bloom_hits"] += 1
        else:
            self.stats["bloom_misses"] += 1
        
        return exists
    
    def register_document(self, doc_id: str, namespace: str = "default"):
        """Register document in BloomFilter"""
        self.bloom_filter.add_document(doc_id, namespace)
    
    async def invalidate_namespace_cache(self, namespace: str):
        """Invalidate all cache for namespace"""
        await self.query_cache.invalidate_namespace(namespace)
        
        # Reset BloomFilter for namespace
        if BLOOM_AVAILABLE and namespace in self.bloom_filter.bloom_filters:
            try:
                self.bloom_filter.bloom_filters[namespace] = PyBloomFilter(
                    capacity=self.bloom_filter.capacity,
                    error_rate=self.bloom_filter.error_rate
                )
                logger.info(f"🌸 Reset BloomFilter for namespace: {namespace}")
            except Exception as e:
                logger.error(f"Error resetting BloomFilter: {e}")
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        cache_stats = await self.query_cache.get_cache_stats()
        bloom_stats = self.bloom_filter.get_filter_stats()
        
        total_queries = self.stats["cache_hits"] + self.stats["cache_misses"]
        total_bloom = self.stats["bloom_hits"] + self.stats["bloom_misses"]
        
        return {
            "cache": cache_stats,
            "bloom_filter": bloom_stats,
            "performance": self.stats,
            "hit_rates": {
                "cache_hit_rate": self.stats["cache_hits"] / max(1, total_queries),
                "bloom_hit_rate": self.stats["bloom_hits"] / max(1, total_bloom)
            }
        }

# Global cache manager instance
cache_manager = CacheManager(redis_url=REDIS_URL, cache_ttl=CACHE_TTL)
