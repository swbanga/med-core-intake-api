# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.database import get_db_session
from app.models import Base
from app.config import settings

# 1. Connect to the Sterile Sandbox
engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    The Architect's Sandbox.
    Creates all tables before a test, yields the connection, and drops all tables after.
    Guarantees absolute data isolation between tests.
    """
    # Build the concrete
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Hand the session to the test
    async with TestingSessionLocal() as session:
        yield session
        
    # Nuke the sandbox
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    """
    The Hijacker.
    Intercepts FastAPI's database dependency and forces it to use the sandbox.
    """
    async def override_get_db():
        yield db_session

    # Execute the hijack
    app.dependency_overrides[get_db_session] = override_get_db
    
    # Spin up the fake async browser
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
        
    # Clean up the hijack after the test
    app.dependency_overrides.clear()