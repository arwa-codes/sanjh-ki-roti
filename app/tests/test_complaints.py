import uuid
from datetime import date, datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.delivery import Route, DeliveryPartner, DeliveryLog
from app.models.complaint import Complaint
from app.models.notification import NotificationQueue
from app.models.billing import BillingTransaction
from app.core.security import get_password_hash, create_access_token

def get_auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

def test_complaint_and_resolution_flow(client: TestClient, db_session: Session) -> None:
    """Test logging a complaint, duplicate prevention, admin list, and resolution emails."""
    pwd = get_password_hash("password")
    admin = User(email="admin_support@example.com", phone="+918000000020", hashed_password=pwd, role="admin")
    cust = User(email="cust_support@example.com", phone="+919000000020", hashed_password=pwd, role="customer")
    db_session.add_all([admin, cust])
    db_session.commit()

    admin_headers = get_auth_headers(admin)
    cust_headers = get_auth_headers(cust)

    # Setup customer subscription and delivery run
    profile = Customer(
        user_id=cust.id, first_name="CS", last_name="User", address="Kota hostel", pincode="324005",
        aadhaar_number="121212121212", referral_code="REF-SUPPORT", is_verified=True
    )
    plan = Plan(name="Support Plan", duration_days=30, price=2000.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(
        customer_id=profile.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=60, original_price=2000.00
    )
    db_session.add(sub)
    db_session.commit()

    log = DeliveryLog(
        subscription_id=sub.id, delivery_date=date.today(), meal_type="lunch", status="failed",
        failure_reason="Late Delivery"
    )
    db_session.add(log)
    db_session.commit()

    # 1. Customer logs complaint against their run
    complaint_payload = {
        "delivery_log_id": str(log.id),
        "category": "delay",
        "description": "Tiffin was delivered 2 hours late and food was cold."
    }
    res = client.post("/api/v1/complaints", json=complaint_payload, headers=cust_headers)
    assert res.status_code == status.HTTP_201_CREATED
    complaint_data = res.json()
    assert complaint_data["status"] == "open"
    assert complaint_data["category"] == "delay"
    complaint_id = uuid.UUID(complaint_data["id"])

    # Verify outbox pending email notification is queued
    db_session.expire_all()
    notif = db_session.query(NotificationQueue).filter(NotificationQueue.recipient == cust.email).first()
    assert notif is not None
    assert notif.status == "pending"
    assert "We have received your complaint" in notif.body

    # Try logging duplicate complaint on same run -> Denied
    res = client.post("/api/v1/complaints", json=complaint_payload, headers=cust_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Admin retrieves list of all complaints
    res = client.get("/api/v1/complaints", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) >= 1

    # 3. Admin resolves complaint
    resolve_payload = {
        "status": "resolved",
        "resolution_notes": "We have credited your account with Rs. 50."
    }
    res = client.patch(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json=resolve_payload,
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "resolved"
    assert res.json()["resolution_notes"] == "We have credited your account with Rs. 50."

    # Verify resolve notification queued in outbox
    db_session.expire_all()
    resol_notif = db_session.query(NotificationQueue).filter(
        NotificationQueue.recipient == cust.email,
        NotificationQueue.subject == "Complaint Resolved - Saanjh Ki Roti Support"
    ).first()
    assert resol_notif is not None
    assert resol_notif.status == "pending"

def test_sla_escalation_rules(client: TestClient, db_session: Session) -> None:
    """Test SLA background scans flags open disputes older than 24 hours as escalated."""
    pwd = get_password_hash("password")
    admin = User(email="admin_sla@example.com", phone="+918000000021", hashed_password=pwd, role="admin")
    cust = User(email="cust_sla@example.com", phone="+919000000021", hashed_password=pwd, role="customer")
    db_session.add_all([admin, cust])
    db_session.commit()

    admin_headers = get_auth_headers(admin)

    # Setup customer profile and log
    profile = Customer(
        user_id=cust.id, first_name="SLA", last_name="User", address="Kota hostel", pincode="324005",
        aadhaar_number="131313131313", referral_code="REF-SLA", is_verified=True
    )
    plan = Plan(name="SLA Plan", duration_days=30, price=2000.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(
        customer_id=profile.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=60, original_price=2000.00
    )
    db_session.add(sub)
    db_session.commit()

    log = DeliveryLog(subscription_id=sub.id, delivery_date=date.today(), meal_type="lunch", status="pending")
    db_session.add(log)
    db_session.commit()

    # Create complaint and backdate created_at to 30 hours ago to simulate SLA breach
    complaint = Complaint(
        customer_id=profile.id,
        delivery_log_id=log.id,
        category="quality",
        description="Hair found in tiffin.",
        status="open",
        created_at=datetime.utcnow() - timedelta(hours=30)
    )
    db_session.add(complaint)
    db_session.commit()

    # Admin triggers SLA escalation scan
    res = client.post("/api/v1/complaints/escalate-sla", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    assert "Escalated 1 complaints" in res.json()["message"]

    # Verify complaint status transitioned to escalated
    db_session.expire_all()
    escalated_comp = db_session.query(Complaint).filter(Complaint.id == complaint.id).first()
    assert escalated_comp.status == "escalated"

    # Verify escalation email queued
    notif = db_session.query(NotificationQueue).filter(
        NotificationQueue.recipient == cust.email,
        NotificationQueue.subject == "Complaint Status Escalated - Tier 2 Support"
    ).first()
    assert notif is not None
    assert notif.status == "pending"

def test_notification_queue_worker(client: TestClient, db_session: Session) -> None:
    """Test notification outbox mock runner processes pending entries successfully."""
    # Add a mock pending notification
    notif = NotificationQueue(
        recipient="test@example.com",
        subject="Hello",
        body="World",
        status="pending"
    )
    db_session.add(notif)
    db_session.commit()

    # Run the worker process
    from app.services.notification_service import notification_service
    processed = notification_service.process_outbox_notifications(db_session)
    assert processed == 1

    # Verify status changed to sent
    db_session.expire_all()
    updated_notif = db_session.query(NotificationQueue).filter(NotificationQueue.id == notif.id).first()
    assert updated_notif.status == "sent"
    assert updated_notif.sent_at is not None

def test_monthly_pdf_report_api(client: TestClient, db_session: Session) -> None:
    """Test downloading the operational statistics PDF report."""
    pwd = get_password_hash("password")
    admin = User(email="admin_report@example.com", phone="+918000000022", hashed_password=pwd, role="admin")
    cust = User(email="cust_report@example.com", phone="+919000000022", hashed_password=pwd, role="customer")
    db_session.add_all([admin, cust])
    db_session.commit()

    admin_headers = get_auth_headers(admin)

    # Add active subscription & transaction
    profile = Customer(user_id=cust.id, first_name="Rep", last_name="User", address="Kota hostel", pincode="324005", aadhaar_number="141414141414", referral_code="REF-REP", is_verified=True)
    plan = Plan(name="Report Plan", duration_days=30, price=3000.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(customer_id=profile.id, plan_id=plan.id, status="active", start_date=date.today(), end_date=date.today() + timedelta(days=30), remaining_meals=60, original_price=3000.00)
    db_session.add(sub)
    db_session.commit()

    # Paid invoice transaction
    tx = BillingTransaction(customer_id=profile.id, subscription_id=sub.id, billing_date=date.today(), amount=3000.00, payment_status="paid")
    db_session.add(tx)
    db_session.commit()

    # Trigger report download
    current_year = date.today().year
    current_month = date.today().month
    res = client.get(
        f"/api/v1/analytics/report?year={current_year}&month={current_month}",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.headers["content-type"] == "application/pdf"
    
    # Verify PDF content structure
    pdf_bytes = res.content
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"Saanjh Ki Roti - Monthly Operational Report" in pdf_bytes
    assert b"Total Active Subscriptions: 1" in pdf_bytes
    assert b"Total Revenue Generated: Rs. 3000.00" in pdf_bytes
