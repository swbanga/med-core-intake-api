# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import users

# Initialize the API Vault
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Zero-Trust Healthcare Backend",
    version="1.0.0",
    docs_url="/api/docs", # Exposes Swagger UI
    redoc_url="/api/redoc"
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

@app.get("/health", tags=["System Diagnostics"])
async def health_check():
    """The FBI Feedback Loop: Basic heartbeat."""
    return {"status": "operational", "environment": settings.ENVIRONMENT}