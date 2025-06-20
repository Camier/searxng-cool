"""
Redis-based caching for music search engines

Provides intelligent caching with compression and TTL management
"""

import json
import zlib
import redis
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class MusicCache:
    """Redis cache implementation for music search results"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cache with Redis connection
        
        Args:
            config: Cache configuration dictionary
        """
        self.config = config
        self.enabled = config.get('backend') == 'redis'
        self.compression = config.get('compression', True)
        self.key_prefix = config.get('key_prefix', 'searxng_music')
        
        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host=config.get('host', 'localhost'),
                    port=config.get('port', 6379),
                    db=config.get('db', 1),
                    decode_responses=False  # We'll handle encoding/decoding
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis cache: {str(e)}")
                self.enabled = False
                self.redis_client = None
        else:
            self.redis_client = None
            
    def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.redis_client:
            return None
            
        try:
            full_key = f"{self.key_prefix}:{key}"
            value = self.redis_client.get(full_key)
            
            if value is None:
                return None
                
            # Decompress if needed
            if self.compression:
                try:
                    value = zlib.decompress(value)
                except:
                    # Data might not be compressed
                    pass
                    
            # Decode to string
            if isinstance(value, bytes):
                value = value.decode('utf-8')
                
            return value
            
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {str(e)}")
            return None
            
    def setex(self, key: str, ttl: int, value: str) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            value: Value to cache
            
        Returns:
            True if successful
        """
        if not self.enabled or not self.redis_client:
            return False
            
        try:
            full_key = f"{self.key_prefix}:{key}"
            
            # Compress if enabled
            cache_value = value.encode('utf-8')
            if self.compression:
                cache_value = zlib.compress(cache_value)
                
            self.redis_client.setex(full_key, ttl, cache_value)
            return True
            
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {str(e)}")
            return False
            
    def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        if not self.enabled or not self.redis_client:
            return False
            
        try:
            full_key = f"{self.key_prefix}:{key}"
            self.redis_client.delete(full_key)
            return True
            
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {str(e)}")
            return False
            
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Redis pattern (e.g., "music:search:discogs:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis_client:
            return 0
            
        try:
            full_pattern = f"{self.key_prefix}:{pattern}"
            keys = self.redis_client.keys(full_pattern)
            
            if keys:
                return self.redis_client.delete(*keys)
                
            return 0
            
        except Exception as e:
            logger.warning(f"Cache clear failed for pattern {pattern}: {str(e)}")
            return 0
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.redis_client:
            return {'enabled': False}
            
        try:
            info = self.redis_client.info()
            dbinfo = self.redis_client.info('keyspace').get(f'db{self.config.get("db", 1)}', {})
            
            return {
                'enabled': True,
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_keys': dbinfo.get('keys', 0),
                'hit_rate': f"{info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)) * 100:.2f}%"
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {'enabled': True, 'error': str(e)}