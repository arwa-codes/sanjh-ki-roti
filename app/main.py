from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.auth import router as auth_router

# Setup JSON logging interceptors on startup
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Saanjh Ki Roti tiffin subscription service",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/health", tags=["System Health"], summary="Service Health Check Status")
def health_check() -> dict:
    """Verifies the API is online and reports basic config state."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
