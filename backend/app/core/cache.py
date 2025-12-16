import redis
from .config import settings

# Redis connection with error handling
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
except redis.ConnectionError:
    # Fallback to in-memory cache if Redis is not available
    redis_client = None

def get_cache_key(prefix: str, *args) -> str:
    """Generate a cache key from prefix and arguments"""
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def cache_get(key: str):
    """Get value from cache"""
    if redis_client is None:
        return None
    try:
        return redis_client.get(key)
    except redis.ConnectionError:
        return None

def cache_set(key: str, value: str, expire: int = 3600):
    """Set value in cache with expiration"""
    if redis_client is None:
        return
    try:
        redis_client.setex(key, expire, value)
    except redis.ConnectionError:
        pass

def cache_delete(key: str):
    """Delete value from cache"""
    if redis_client is None:
        return
    try:
        redis_client.delete(key)
    except redis.ConnectionError:
        pass

def cache_exists(key: str) -> bool:
    """Check if key exists in cache"""
    if redis_client is None:
        return False
    try:
        return redis_client.exists(key) > 0
    except redis.ConnectionError:
        return False


class RedisCache:
    """Redis cache wrapper class"""

    def __init__(self, url: str = None):
        try:
            self.client = redis.Redis.from_url(url or settings.REDIS_URL, decode_responses=True)
            # Test connection
            self.client.ping()
        except redis.ConnectionError:
            # Fallback if Redis is not available
            self.client = None

    def get(self, key: str):
        """Get value from cache"""
        if self.client is None:
            return None
        try:
            return self.client.get(key)
        except redis.ConnectionError:
            return None

    def set(self, key: str, value: str, expire: int = 3600):
        """Set value in cache with expiration"""
        if self.client is None:
            return
        try:
            self.client.setex(key, expire, value)
        except redis.ConnectionError:
            pass

    def delete(self, key: str):
        """Delete value from cache"""
        if self.client is None:
            return
        try:
            self.client.delete(key)
        except redis.ConnectionError:
            pass

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if self.client is None:
            return False
        try:
            return self.client.exists(key) > 0
        except redis.ConnectionError:
            return False

    def get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments"""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"