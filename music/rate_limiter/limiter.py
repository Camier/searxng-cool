"""
Token bucket rate limiter implementation for music engines

Uses Redis for distributed rate limiting across multiple workers
"""

import time
import redis
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.key_prefix = "ratelimit"
        
    def acquire(self, identifier: str, limit: int, period: int) -> bool:
        """
        Try to acquire a token for the given identifier
        
        Args:
            identifier: Unique identifier (e.g., engine name)
            limit: Maximum requests allowed
            period: Time period in seconds
            
        Returns:
            True if token acquired, False if rate limited
        """
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            now = int(time.time())
            
            # Key for this rate limiter
            key = f"{self.key_prefix}:{identifier}"
            
            # Clean old entries
            pipe.zremrangebyscore(key, 0, now - period)
            
            # Count current entries
            pipe.zcard(key)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]
            
            # Check if under limit
            if current_count < limit:
                # Add current timestamp
                self.redis.zadd(key, {str(now): now})
                self.redis.expire(key, period + 1)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            # On error, allow the request (fail open)
            return True
            
    def get_remaining(self, identifier: str, limit: int, period: int) -> Dict[str, Any]:
        """
        Get remaining tokens and reset time
        
        Args:
            identifier: Unique identifier
            limit: Maximum requests allowed
            period: Time period in seconds
            
        Returns:
            Dictionary with remaining tokens and reset time
        """
        try:
            now = int(time.time())
            key = f"{self.key_prefix}:{identifier}"
            
            # Clean old entries
            self.redis.zremrangebyscore(key, 0, now - period)
            
            # Count current entries
            current_count = self.redis.zcard(key)
            
            # Get oldest entry
            oldest_entries = self.redis.zrange(key, 0, 0, withscores=True)
            
            reset_time = None
            if oldest_entries:
                oldest_timestamp = int(oldest_entries[0][1])
                reset_time = oldest_timestamp + period
                
            return {
                'remaining': max(0, limit - current_count),
                'limit': limit,
                'reset': reset_time,
                'reset_in': reset_time - now if reset_time else period
            }
            
        except Exception as e:
            logger.error(f"Rate limiter stats error: {str(e)}")
            return {
                'remaining': limit,
                'limit': limit,
                'reset': None,
                'reset_in': None
            }
            
    def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for identifier
        
        Args:
            identifier: Unique identifier
            
        Returns:
            True if successful
        """
        try:
            key = f"{self.key_prefix}:{identifier}"
            self.redis.delete(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limiter reset error: {str(e)}")
            return False


class MultiEngineRateLimiter:
    """
    Rate limiter that handles multiple engines with different limits
    """
    
    def __init__(self, redis_client: redis.Redis, engine_configs: Dict[str, Dict[str, Any]]):
        """
        Initialize multi-engine rate limiter
        
        Args:
            redis_client: Redis client instance
            engine_configs: Configuration for each engine
        """
        self.limiter = RateLimiter(redis_client)
        self.engine_configs = engine_configs
        
    def acquire(self, engine_name: str) -> bool:
        """
        Try to acquire token for specific engine
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            True if token acquired
        """
        config = self.engine_configs.get(engine_name, {})
        limit = config.get('rate_limit', 60)
        period = config.get('rate_period', 60)
        
        return self.limiter.acquire(engine_name, limit, period)
        
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get rate limit stats for all engines"""
        stats = {}
        
        for engine_name, config in self.engine_configs.items():
            if config.get('enabled', True):
                limit = config.get('rate_limit', 60)
                period = config.get('rate_period', 60)
                stats[engine_name] = self.limiter.get_remaining(engine_name, limit, period)
                
        return stats