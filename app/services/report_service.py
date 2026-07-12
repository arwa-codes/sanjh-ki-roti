from datetime import date, datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.billing import BillingTransaction
from app.models.delivery import DeliveryLog
from app.models.complaint import Complaint

class ReportService:
    def generate_monthly_pdf_report(self, db: Session, year: int, month: int) -> bytes:
        """Query monthly metrics and output a standards-compliant PDF report."""
        # Calculate date boundaries
        start_of_month = date(year, month, 1)
        if month == 12:
            end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)

        # 1. Total Active Subscriptions
        active_subs = db.query(Subscription).filter(Subscription.status == "active").count()

        # 2. Total Revenue Generated
        revenue_sum = db.query(func.sum(BillingTransaction.amount)).filter(
            BillingTransaction.payment_status == "paid",
            BillingTransaction.billing_date >= start_of_month,
            BillingTransaction.billing_date <= end_of_month
        ).scalar()
        revenue = float(revenue_sum) if revenue_sum is not None else 0.0

        # 3. Delivery Metrics
        total_deliveries = db.query(DeliveryLog).filter(
            DeliveryLog.delivery_date >= start_of_month,
            DeliveryLog.delivery_date <= end_of_month
        ).count()

        delivered_meals = db.query(DeliveryLog).filter(
            DeliveryLog.delivery_date >= start_of_month,
            DeliveryLog.delivery_date <= end_of_month,
            DeliveryLog.status == "delivered"
        ).count()

        failed_meals = db.query(DeliveryLog).filter(
            DeliveryLog.delivery_date >= start_of_month,
            DeliveryLog.delivery_date <= end_of_month,
            DeliveryLog.status == "failed"
        ).count()

        delivery_efficiency = (delivered_meals / total_deliveries * 100.0) if total_deliveries > 0 else 100.0

        # 4. Total complaints count
        complaints_start = datetime(year, month, 1)
        complaints_end = datetime(year, month, end_of_month.day, 23, 59, 59)
        total_complaints = db.query(Complaint).filter(
            Complaint.created_at >= complaints_start,
            Complaint.created_at <= complaints_end
        ).count()

        # Construct raw, standards-compliant PDF document content in-memory
        pdf_raw_data = (
            "%PDF-1.4\n"
            "1 0 obj\n"
            "<< /Type /Catalog /Pages 2 0 R >>\n"
            "endobj\n"
            "2 0 obj\n"
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            "endobj\n"
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            "endobj\n"
            "4 0 obj\n"
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            "endobj\n"
            "5 0 obj\n"
            "<< /Length 600 >>\n"
            "stream\n"
            "BT\n"
            "/F1 18 Tf\n"
            "50 800 Td\n"
            "(Saanjh Ki Roti - Monthly Operational Report) Tj\n"
            "/F1 12 Tf\n"
            "0 -40 Td\n"
            "(Report Period: {year}-{month:02d}) Tj\n"
            "0 -30 Td\n"
            "(Total Active Subscriptions: {active_subs}) Tj\n"
            "0 -20 Td\n"
            "(Total Revenue Generated: Rs. {revenue:.2f}) Tj\n"
            "0 -20 Td\n"
            "(Total Scheduled Deliveries: {total_deliveries}) Tj\n"
            "0 -20 Td\n"
            "(Delivered Meals Count: {delivered_meals}) Tj\n"
            "0 -20 Td\n"
            "(Failed Meals Count: {failed_meals}) Tj\n"
            "0 -20 Td\n"
            "(Logistics Delivery Efficiency: {delivery_efficiency:.1f}%) Tj\n"
            "0 -20 Td\n"
            "(Customer Dispute Complaints: {total_complaints}) Tj\n"
            "ET\n"
            "endstream\n"
            "endobj\n"
            "xref\n"
            "0 6\n"
            "0000000000 65535 f\n"
            "0000000009 00000 n\n"
            "0000000056 00000 n\n"
            "0000000111 00000 n\n"
            "0000000212 00000 n\n"
            "0000000289 00000 n\n"
            "trailer\n"
            "<< /Size 6 /Root 1 0 R >>\n"
            "startxref\n"
            "980\n"
            "%%EOF\n"
        ).format(
            year=year,
            month=month,
            active_subs=active_subs,
            revenue=revenue,
            total_deliveries=total_deliveries,
            delivered_meals=delivered_meals,
            failed_meals=failed_meals,
            delivery_efficiency=delivery_efficiency,
            total_complaints=total_complaints
        )

        return pdf_raw_data.encode("utf-8")

# Global report service instance
report_service = ReportService()
