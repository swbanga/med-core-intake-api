from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.middleware import FBIFeedbackLoopMiddleware
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from app.cache import redis_client

from app.config import settings
from app.routers import users, auth, patients

description = """
### 🛡️ Enterprise Zero-Trust Healthcare API

Welcome to the Med-Core Intake API Documentation.

**Interactive API Testing:**
To test these endpoints dynamically, please use our official public workspace:
👉 **[Med-Core Postman Workspace](https://www.postman.com/superwbanga-7863188/workspace/med-core-devsecops-matrix)**

**Recruiter & Portfolio Access:**
To evaluate the DevSecOps architecture, authenticate via the `/login` endpoint using these read-only demo credentials:
* **Email:** `demo@medcore.com`
* **Password:** `medcore-demo-2026`

---
*Engineered by **Super Washington Banga*** | *Cloud Architect & DevSecOps Engineer*
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    await FastAPILimiter.init(redis_client)
    yield
    await redis_client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS – strictly from allowed origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feedback loop middleware (must come before routers for clarity)
app.add_middleware(FBIFeedbackLoopMiddleware)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(patients.router)


@app.get("/health", tags=["System Diagnostics"])
async def health_check():
    """Deep health check: pings DB and Redis."""
    from app.database import async_session_maker
    import redis.exceptions as redis_exc

    health = {
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "database": "unreachable",
        "redis": "unreachable",
    }

    # Database check
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        health["database"] = "healthy"
    except Exception:
        health["status"] = "degraded"

    # Redis check
    try:
        if await redis_client.ping(): # type: ignore
            health["redis"] = "healthy"
    except (redis_exc.ConnectionError, redis_exc.TimeoutError):
        health["status"] = "degraded"

    return health


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/redoc")