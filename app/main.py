from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.plans import router as plans_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.billing import router as billing_router

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
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(plans_router, prefix="/api/v1/plans", tags=["Plans"])
app.include_router(subscriptions_router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])

@app.get("/health", tags=["System Health"], summary="Service Health Check Status")
def health_check() -> dict:
    """Verifies the API is online and reports basic config state."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
