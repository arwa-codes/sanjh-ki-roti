from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.analytics import AdminDashboardResponse
from app.services.delivery_service import delivery_service
from app.services.report_service import report_service
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

@router.get(
    "/report",
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Download monthly PDF operational report (Admin only)"
)
def download_monthly_report(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db)
) -> Response:
    """Download monthly operation PDF report containing stats on subscriptions, billing, and runs."""
    pdf_bytes = report_service.generate_monthly_pdf_report(db, year=year, month=month)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Operational_Report_{year}_{month:02d}.pdf"
        }
    )
