"""
Intelligent Caching System for RAG with Query Similarity Matching
"""
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Caching will be disabled.")

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence transformers not available. Semantic caching will be limited.")


class RAGCacheManager:
    """
    Intelligent cache manager with:
    - Semantic similarity-based query matching
    - TTL management based on query patterns
    - Popular query detection and prioritization
    - Cache warming for common questions
    """
    
    def __init__(self):
        # Get Redis settings from Django cache configuration
        redis_settings = settings.CACHES.get('default', {}).get('LOCATION', 'redis://localhost:6379/1')
        # Parse redis URL
        from urllib.parse import urlparse
        parsed = urlparse(redis_settings)

        self.redis_client = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            db=int(parsed.path.strip('/')) if parsed.path else 0,
            decode_responses=True
        ) if REDIS_AVAILABLE else None
        
        # Initialize sentence transformer for query similarity
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2') if SENTENCE_TRANSFORMERS_AVAILABLE else None
        
        # Cache configuration
        self.similarity_threshold = 0.85
        self.default_ttl = 3600  # 1 hour
        self.popular_query_ttl = 86400  # 24 hours
        self.max_cache_size = 10000
        
        # Cache keys
        self.QUERY_EMBEDDINGS_KEY = "rag:query_embeddings"
        self.QUERY_RESULTS_KEY = "rag:query_results"
        self.QUERY_STATS_KEY = "rag:query_stats"
        self.POPULAR_QUERIES_KEY = "rag:popular_queries"
    
    def get_cached_response(self, query: str, context: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get cached response using semantic similarity matching
        """
        # Try exact match first
        exact_key = self._generate_cache_key(query, context)
        exact_result = self._get_exact_match(exact_key)
        
        if exact_result:
            self._update_stats(query, "exact_hit")
            return exact_result
        
        # Try semantic similarity match
        similar_result = self._get_similar_match(query, context)
        
        if similar_result:
            self._update_stats(query, "similar_hit")
            return similar_result
        
        self._update_stats(query, "miss")
        return None
    
    def cache_response(self, query: str, response: Dict, context: Optional[Dict] = None):
        """
        Cache response with intelligent TTL and similarity indexing
        """
        cache_key = self._generate_cache_key(query, context)
        
        # Determine TTL based on query patterns
        ttl = self._calculate_ttl(query, response)
        
        # Store the response
        cache_data = {
            "query": query,
            "response": response,
            "context": context,
            "cached_at": datetime.now().isoformat(),
            "ttl": ttl,
            "hits": 0
        }
        
        # Cache the response
        self.redis_client.setex(
            f"{self.QUERY_RESULTS_KEY}:{cache_key}",
            ttl,
            json.dumps(cache_data)
        )
        
        # Store query embedding for similarity matching
        self._store_query_embedding(query, cache_key)
        
        # Update popular queries
        self._update_popular_queries(query)
        
        # Manage cache size
        self._evict_if_needed()
    
    def _generate_cache_key(self, query: str, context: Optional[Dict] = None) -> str:
        """Generate unique cache key"""
        key_data = {
            "query": query.lower().strip(),
            "context": context or {}
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_exact_match(self, cache_key: str) -> Optional[Dict]:
        """Get exact match from cache"""
        data = self.redis_client.get(f"{self.QUERY_RESULTS_KEY}:{cache_key}")
        
        if data:
            cache_data = json.loads(data)
            cache_data["hits"] += 1
            
            # Update hit count
            self.redis_client.set(
                f"{self.QUERY_RESULTS_KEY}:{cache_key}",
                json.dumps(cache_data)
            )
            
            return cache_data["response"]
        
        return None
    
    def _get_similar_match(self, query: str, context: Optional[Dict] = None) -> Optional[Dict]:
        """Find similar query using embeddings"""
        # Get query embedding
        query_embedding = self.similarity_model.encode([query.lower().strip()])[0]
        
        # Get all cached embeddings
        cached_embeddings = self.redis_client.hgetall(self.QUERY_EMBEDDINGS_KEY)
        
        best_match = None
        best_score = 0
        
        for cache_key, embedding_str in cached_embeddings.items():
            cached_embedding = np.frombuffer(
                embedding_str.encode('latin-1'), 
                dtype=np.float32
            )
            
            # Calculate similarity
            similarity = float(util.cos_sim(query_embedding, cached_embedding))
            
            if similarity > self.similarity_threshold and similarity > best_score:
                best_score = similarity
                best_match = cache_key
        
        if best_match:
            return self._get_exact_match(best_match)
        
        return None
    
    def _store_query_embedding(self, query: str, cache_key: str):
        """Store query embedding for similarity matching"""
        embedding = self.similarity_model.encode([query.lower().strip()])[0]
        
        # Convert to bytes for Redis storage
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        self.redis_client.hset(
            self.QUERY_EMBEDDINGS_KEY,
            cache_key,
            embedding_bytes.decode('latin-1')
        )
    
    def _calculate_ttl(self, query: str, response: Dict) -> int:
        """Calculate TTL based on query patterns and response quality"""
        # Popular queries get longer TTL
        if self._is_popular_query(query):
            return self.popular_query_ttl
        
        # High confidence responses get longer TTL
        confidence = response.get("confidence", 0.5)
        if confidence > 0.8:
            return int(self.default_ttl * 1.5)
        elif confidence < 0.5:
            return int(self.default_ttl * 0.5)
        
        return self.default_ttl
    
    def _is_popular_query(self, query: str) -> bool:
        """Check if query is popular"""
        popular_queries = self.redis_client.zrange(
            self.POPULAR_QUERIES_KEY, 
            -100, 
            -1, 
            withscores=True
        )
        
        query_lower = query.lower().strip()
        
        for cached_query, score in popular_queries:
            if cached_query == query_lower and score > 10:
                return True
        
        return False
    
    def _update_popular_queries(self, query: str):
        """Update popular queries ranking"""
        query_lower = query.lower().strip()
        self.redis_client.zincrby(self.POPULAR_QUERIES_KEY, 1, query_lower)
        
        # Keep only top 1000 queries
        self.redis_client.zremrangebyrank(self.POPULAR_QUERIES_KEY, 0, -1001)
    
    def _update_stats(self, query: str, hit_type: str):
        """Update cache statistics"""
        stats_key = f"{self.QUERY_STATS_KEY}:{datetime.now().strftime('%Y-%m-%d')}"
        
        self.redis_client.hincrby(stats_key, f"{hit_type}_count", 1)
        self.redis_client.hincrby(stats_key, "total_queries", 1)
        
        # Set expiry for stats
        self.redis_client.expire(stats_key, 86400 * 30)  # 30 days
    
    def _evict_if_needed(self):
        """Evict old entries if cache is too large"""
        cache_size = self.redis_client.dbsize()
        
        if cache_size > self.max_cache_size:
            # Get oldest entries
            pattern = f"{self.QUERY_RESULTS_KEY}:*"
            oldest_keys = []
            
            for key in self.redis_client.scan_iter(match=pattern, count=100):
                data = self.redis_client.get(key)
                if data:
                    cache_data = json.loads(data)
                    cached_at = datetime.fromisoformat(cache_data["cached_at"])
                    oldest_keys.append((key, cached_at, cache_data["hits"]))
            
            # Sort by age and hits (oldest with fewest hits first)
            oldest_keys.sort(key=lambda x: (x[1], x[2]))
            
            # Remove oldest 10%
            to_remove = int(len(oldest_keys) * 0.1)
            for key, _, _ in oldest_keys[:to_remove]:
                self.redis_client.delete(key)
                # Also remove from embeddings
                cache_key = key.split(":")[-1]
                self.redis_client.hdel(self.QUERY_EMBEDDINGS_KEY, cache_key)
    
    def warm_cache(self, common_queries: List[Dict]):
        """Warm cache with common queries and their responses"""
        for item in common_queries:
            query = item.get("query")
            response = item.get("response")
            context = item.get("context", {})
            
            if query and response:
                self.cache_response(query, response, context)
        
        logger.info(f"Warmed cache with {len(common_queries)} common queries")
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats_key = f"{self.QUERY_STATS_KEY}:{today}"
        
        stats = self.redis_client.hgetall(stats_key)
        
        # Calculate hit rate
        total = int(stats.get("total_queries", 0))
        exact_hits = int(stats.get("exact_hit_count", 0))
        similar_hits = int(stats.get("similar_hit_count", 0))
        misses = int(stats.get("miss_count", 0))
        
        hit_rate = (exact_hits + similar_hits) / total if total > 0 else 0
        
        # Get popular queries
        popular_queries = self.redis_client.zrange(
            self.POPULAR_QUERIES_KEY,
            -10,
            -1,
            withscores=True
        )
        
        return {
            "date": today,
            "total_queries": total,
            "exact_hits": exact_hits,
            "similar_hits": similar_hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "cache_size": self.redis_client.dbsize(),
            "popular_queries": [
                {"query": q, "count": int(s)} 
                for q, s in popular_queries
            ]
        }
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries"""
        if pattern:
            # Invalidate specific pattern
            for key in self.redis_client.scan_iter(match=f"{self.QUERY_RESULTS_KEY}:*{pattern}*"):
                self.redis_client.delete(key)
        else:
            # Invalidate all
            self.redis_client.flushdb()
        
        logger.info(f"Cache invalidated: {pattern or 'all'}")


# Create singleton instance
rag_cache = RAGCacheManager()

# Common medical queries for cache warming
COMMON_MEDICAL_QUERIES = [
    {
        "query": "what is chemotherapy",
        "response": {
            "content": "Chemotherapy is a type of cancer treatment that uses drugs to destroy cancer cells...",
            "confidence": 0.9
        }
    },
    {
        "query": "side effects of radiation therapy",
        "response": {
            "content": "Common side effects of radiation therapy include fatigue, skin changes...",
            "confidence": 0.9
        }
    },
    {
        "query": "what is immunotherapy",
        "response": {
            "content": "Immunotherapy is a type of cancer treatment that helps your immune system fight cancer...",
            "confidence": 0.9
        }
    },
    # Add more common queries
]