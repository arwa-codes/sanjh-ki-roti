from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.analytics import AdminDashboardResponse
from app.services.delivery_service import delivery_service
from app.api.dependencies import RoleChecker

router = APIRouter()

@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Retrieve real-time kitchen counters (Admin only)"
)
def get_dashboard_counters(db: Session = Depends(get_db)) -> AdminDashboardResponse:
    """Fetch live counts of active subscriptions, meal preparation limits, and logistics metrics."""
    return delivery_service.get_admin_dashboard_stats(db)
