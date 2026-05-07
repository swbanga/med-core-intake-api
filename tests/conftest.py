# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
import uuid
from fastapi_limiter import FastAPILimiter

# 1. TOP-LEVEL IMPORTS: Prevents Python Namespace Shadowing
from app.main import app
import app.main as main_module
from app import cache, oauth2
from app.routers import auth as auth_router
from app.database import get_db_session
from app.models import Base
from app.config import settings
from app.models import Role

# 2. NULL POOL: Prevents SQLAlchemy from holding ghost connections
engine = create_async_engine(settings.TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Wipes the database clean for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db_session] = override_get_db
        yield session
        app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    """
    Injects a fresh Redis connection into the API for EVERY test.
    The namespace is strictly protected.
    """
    fresh_redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    
    # Patch the global application state in memory securely
    cache.redis_client = fresh_redis
    oauth2.redis_client = fresh_redis
    auth_router.redis_client = fresh_redis
    main_module.redis_client = fresh_redis 

    # 2. NEW OVERRIDE: Mathematically force the DDoS shield to arm itself
    await FastAPILimiter.init(fresh_redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
        
    # Clean up the socket
    await fresh_redis.close()

@pytest_asyncio.fixture(scope="function")
async def seeded_role(db_session):
    """Injects the foundational identity role."""
    role_id = uuid.uuid4()
    role = Role(id=role_id, name="Patient", description="Test Role")
    db_session.add(role)
    await db_session.commit()
    return str(role_id)