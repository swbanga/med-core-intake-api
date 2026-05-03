# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import FBIFeedbackLoopMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter # type: ignore

from app.config import settings
from app.routers import users, auth, patients

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server Startup and Shutdown protocol.
    Establishes the Redis connection pool for the rate limiter.
    """
    # 1. Boot connection to the medcore_cache container
    redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)
    
    yield # API runs while this is yielded
    
    # 2. Teardown protocol
    await redis_connection.close()

# Initialize the API Vault
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Zero-Trust Healthcare Backend",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Policy: Currently open for dev, will be brutally restricted in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the routing matrix
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(patients.router)
app.add_middleware(FBIFeedbackLoopMiddleware)

@app.get("/health", tags=["System Diagnostics"])
async def health_check():
    """The FBI Feedback Loop: Basic heartbeat."""
    return {"status": "operational", "environment": settings.ENVIRONMENT}