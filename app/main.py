# app/main.py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
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
    """
    Server Startup and Shutdown protocol.
    Establishes the Redis connection pool for the rate limiter.
    """
    # 1. Boot connection to the medcore_cache container
    await FastAPILimiter.init(redis_client)
    
    yield # API runs while this is yielded
    
    # 2. Teardown protocol
    await redis_client.close()

# Initialize the API Vault
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    version="1.0.0",
    docs_url="/swagger", # Moves Swagger out of the way
    redoc_url="/redoc",
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

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/redoc")