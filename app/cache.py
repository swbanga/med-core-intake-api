# app/cache.py
import redis.asyncio as redis
from app.config import settings

# Global Connection Pool for the entire DevSecOps Vault
redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)