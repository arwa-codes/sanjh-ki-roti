import uuid
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionPause
from app.models.billing import BillingTransaction, Referral, MealAddon
from app.core.security import get_password_hash, create_access_token
from app.services.subscription_service import IST

# Helper to create headers
def get_auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

def test_customer_profile_flow(client: TestClient, db_session: Session) -> None:
    """Test successful customer profile creation, duplicate checks, and mock document uploads."""
    # Seed user
    pwd = get_password_hash("password")
    user = User(email="cust1@example.com", phone="+919000000001", hashed_password=pwd, role="customer")
    db_session.add(user)
    db_session.commit()

    headers = get_auth_headers(user)
    payload = {
        "first_name": "Arwa",
        "last_name": "Azad",
        "address": "Kota student hostel room 10",
        "pincode": "324005",
        "aadhaar_number": "123456789012"
    }

    # 1. Create Profile
    res = client.post("/api/v1/users/profile", json=payload, headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["first_name"] == "Arwa"
    assert data["is_verified"] is False
    assert "referral_code" in data

    # 2. Try creating again (should conflict)
    res = client.post("/api/v1/users/profile", json=payload, headers=headers)
    assert res.status_code == status.HTTP_409_CONFLICT

    # 3. Upload Aadhaar Card (Mock Upload)
    files = {"file": ("aadhaar.pdf", b"dummy PDF data content", "application/pdf")}
    res = client.post("/api/v1/users/profile/upload-aadhaar", files=files, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert "document_url" in res.json()

    # 4. Verify Profile (Admin scope)
    # Seed admin user
    admin_user = User(email="admin@example.com", phone="+918000000001", hashed_password=pwd, role="admin")
    db_session.add(admin_user)
    db_session.commit()
    admin_headers = get_auth_headers(admin_user)

    res = client.patch(
        f"/api/v1/users/profile/{data['id']}/verify?is_verified=true",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_verified"] is True

def test_admin_plans_crud(client: TestClient, db_session: Session) -> None:
    """Test plan configuration by admins and retrieval by customers."""
    pwd = get_password_hash("password")
    admin = User(email="admin_plan@example.com", phone="+918000000002", hashed_password=pwd, role="admin")
    cust = User(email="cust_plan@example.com", phone="+919000000002", hashed_password=pwd, role="customer")
    db_session.add_all([admin, cust])
    db_session.commit()

    admin_headers = get_auth_headers(admin)
    cust_headers = get_auth_headers(cust)

    plan_payload = {
        "name": "Monthly Executive Plan",
        "description": "Lunch and dinner for 30 days",
        "duration_days": 30,
        "price": "2999.00",
        "meals_included": "both"
    }

    # 1. Create plan (Admin)
    res = client.post("/api/v1/plans", json=plan_payload, headers=admin_headers)
    assert res.status_code == status.HTTP_201_CREATED
    plan_data = res.json()
    assert plan_data["name"] == plan_payload["name"]

    # 2. Customers list plans
    res = client.get("/api/v1/plans", headers=cust_headers)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) >= 1

    # 3. Retrieve plan details
    res = client.get(f"/api/v1/plans/{plan_data['id']}", headers=cust_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["name"] == plan_payload["name"]

def test_subscription_purchase_and_webhook_activation(client: TestClient, db_session: Session) -> None:
    """Test purchasing a plan, getting a pending status, and activating it via payment webhook."""
    pwd = get_password_hash("password")
    cust = User(email="subscriber@example.com", phone="+919000000003", hashed_password=pwd, role="customer")
    db_session.add(cust)
    db_session.commit()

    # Setup customer profile (verified)
    profile = Customer(
        user_id=cust.id,
        first_name="Sub",
        last_name="User",
        address="Kota",
        pincode="324005",
        aadhaar_number="987654321012",
        referral_code="REF-SUBU1",
        is_verified=True
    )
    # Setup active plan
    plan = Plan(name="Weekly Plan", duration_days=7, price=999.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    cust_headers = get_auth_headers(cust)

    # 1. Subscribe to plan
    res = client.post("/api/v1/subscriptions", json={"plan_id": str(plan.id)}, headers=cust_headers)
    assert res.status_code == status.HTTP_201_CREATED
    sub_data = res.json()
    assert sub_data["status"] == "pending"

    # Verify unpaid invoice was generated
    res = client.get("/api/v1/billing/invoices", headers=cust_headers)
    assert res.status_code == status.HTTP_200_OK
    invoices = res.json()
    assert len(invoices) == 1
    assert invoices[0]["payment_status"] == "unpaid"
    gw_txn_id = invoices[0]["gateway_transaction_id"]

    # 2. Trigger gateway payment success webhook (public endpoint)
    webhook_payload = {
        "event": "payment.captured",
        "transaction_id": gw_txn_id,
        "payment_status": "paid",
        "amount": "999.00"
    }
    res = client.post("/api/v1/billing/webhook", json=webhook_payload)
    assert res.status_code == status.HTTP_200_OK

    # 3. Verify subscription is now active and invoice is marked paid
    db_session.expire_all()
    sub_obj = db_session.query(Subscription).filter(Subscription.id == uuid.UUID(sub_data["id"])).first()
    assert sub_obj.status == "active"

    res = client.get("/api/v1/billing/invoices", headers=cust_headers)
    assert res.json()[0]["payment_status"] == "paid"

def test_cutoff_rules_for_pauses(client: TestClient, db_session: Session) -> None:
    """Test same-day pause constraints relative to cutoff times."""
    pwd = get_password_hash("password")
    cust = User(email="pauser@example.com", phone="+919000000004", hashed_password=pwd, role="customer")
    db_session.add(cust)
    db_session.commit()

    profile = Customer(
        user_id=cust.id, first_name="P", last_name="U", address="Kota", pincode="324005",
        aadhaar_number="333333333333", referral_code="REF-PAUSE", is_verified=True
    )
    plan = Plan(name="Lunch Plan", duration_days=30, price=2000.00, meals_included="lunch", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(
        customer_id=profile.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=30, original_price=2000.00
    )
    db_session.add(sub)
    db_session.commit()

    cust_headers = get_auth_headers(cust)

    # Scenario A: Request same-day pause at 07:00 AM IST (before 08:00 AM cutoff) -> Allowed
    test_time_before_cutoff = datetime(2026, 7, 12, 7, 0, tzinfo=IST)
    with patch("app.services.subscription_service.get_ist_now", return_value=test_time_before_cutoff):
        payload = {
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=2))
        }
        res = client.post(f"/api/v1/subscriptions/{sub.id}/pause", json=payload, headers=cust_headers)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["status"] == "active"  # Active pause starting today

    # Scenario B: Request same-day pause at 09:30 AM IST (after 08:00 AM cutoff) -> Denied
    # Re-active subscription first (remove old pause)
    db_session.query(SubscriptionPause).delete()
    sub.status = "active"
    db_session.commit()

    test_time_after_cutoff = datetime(2026, 7, 12, 9, 30, tzinfo=IST)
    with patch("app.services.subscription_service.get_ist_now", return_value=test_time_after_cutoff):
        payload = {
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=2))
        }
        res = client.post(f"/api/v1/subscriptions/{sub.id}/pause", json=payload, headers=cust_headers)
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert "Lunch pause request must be before 08:00 AM" in res.json()["detail"]

def test_resume_and_validity_extension(client: TestClient, db_session: Session) -> None:
    """Test subscription early resumption and date recalculations."""
    pwd = get_password_hash("password")
    cust = User(email="resumer@example.com", phone="+919000000005", hashed_password=pwd, role="customer")
    db_session.add(cust)
    db_session.commit()

    profile = Customer(
        user_id=cust.id, first_name="R", last_name="U", address="Kota", pincode="324005",
        aadhaar_number="444444444444", referral_code="REF-RESUME", is_verified=True
    )
    plan = Plan(name="Flex Plan", duration_days=30, price=2000.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    original_end_date = date.today() + timedelta(days=30)
    sub = Subscription(
        customer_id=profile.id, plan_id=plan.id, status="paused",
        start_date=date.today() - timedelta(days=5), end_date=original_end_date,
        remaining_meals=60, original_price=2000.00
    )
    db_session.add(sub)
    db_session.commit()

    # Scheduled pause started 2 days ago, and was set for 5 days
    pause = SubscriptionPause(
        subscription_id=sub.id,
        start_date=date.today() - timedelta(days=2),
        end_date=date.today() + timedelta(days=2),
        status="active"
    )
    db_session.add(pause)
    db_session.commit()

    cust_headers = get_auth_headers(cust)

    # Resume early today (2 days elapsed: start_date, yesterday. Today is active resumption date)
    res = client.post(f"/api/v1/subscriptions/{sub.id}/resume", headers=cust_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "active"
    
    # Verify new end date (extended by the 2 actual elapsed pause days)
    expected_new_end = original_end_date + timedelta(days=2)
    assert data["end_date"] == str(expected_new_end)

def test_meal_addon_flow(client: TestClient, db_session: Session) -> None:
    """Test daily meal add-on scheduling and billing generation."""
    pwd = get_password_hash("password")
    cust = User(email="addoner@example.com", phone="+919000000006", hashed_password=pwd, role="customer")
    db_session.add(cust)
    db_session.commit()

    profile = Customer(
        user_id=cust.id, first_name="Ad", last_name="On", address="Kota", pincode="324005",
        aadhaar_number="555555555555", referral_code="REF-ADDON", is_verified=True
    )
    plan = Plan(name="Plan Addon", duration_days=30, price=2000.00, meals_included="both", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(
        customer_id=profile.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=60, original_price=2000.00
    )
    db_session.add(sub)
    db_session.commit()

    cust_headers = get_auth_headers(cust)

    # Request addon extra roti for today before cutoff (moked 07:00 AM IST)
    test_time_before_cutoff = datetime(2026, 7, 12, 7, 0, tzinfo=IST)
    with patch("app.services.subscription_service.get_ist_now", return_value=test_time_before_cutoff):
        payload = {
            "addon_date": str(date.today()),
            "meal_type": "lunch",
            "addon_type": "extra_roti",
            "quantity": 2
        }
        res = client.post(f"/api/v1/subscriptions/{sub.id}/addons", json=payload, headers=cust_headers)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["price"] == "20.00"  # 10.00 * 2

        # Verify an unpaid invoice transaction was generated for the addon
        res = client.get("/api/v1/billing/invoices", headers=cust_headers)
        assert res.status_code == status.HTTP_200_OK
        txs = res.json()
        addon_txn = next(t for t in txs if t["gateway_transaction_id"].startswith("TXN-ADDON-"))
        assert addon_txn["payment_status"] == "unpaid"
        assert addon_txn["amount"] == "20.00"

        # Pay addon transaction via gateway webhook
        res = client.post("/api/v1/billing/webhook", json={
            "event": "payment.captured",
            "transaction_id": addon_txn["gateway_transaction_id"],
            "payment_status": "paid",
            "amount": "20.00"
        })
        assert res.status_code == status.HTTP_200_OK

        # Verify addon status is marked paid
        db_session.expire_all()
        addon_obj = db_session.query(MealAddon).filter(MealAddon.subscription_id == sub.id).first()
        assert addon_obj.is_paid is True

def test_referrals_promotion_unlock(client: TestClient, db_session: Session) -> None:
    """Test referral links promotions credits unlock on monthly subscription activation."""
    pwd = get_password_hash("password")
    referrer_user = User(email="referrer@example.com", phone="+919000000007", hashed_password=pwd, role="customer")
    referee_user = User(email="referee@example.com", phone="+919000000008", hashed_password=pwd, role="customer")
    db_session.add_all([referrer_user, referee_user])
    db_session.commit()

    # Referrer profile (verified)
    referrer = Customer(
        user_id=referrer_user.id, first_name="R", last_name="F", address="Kota", pincode="324005",
        aadhaar_number="777777777777", referral_code="REF-REFERRER", is_verified=True
    )
    db_session.add(referrer)
    db_session.commit()

    referee_headers = get_auth_headers(referee_user)

    # 1. Referee creates profile with referral code
    profile_payload = {
        "first_name": "Ref",
        "last_name": "Eree",
        "address": "Kota student hostel room 15",
        "pincode": "324005",
        "aadhaar_number": "888888888888",
        "referral_code": "REF-REFERRER"
    }
    res = client.post("/api/v1/users/profile", json=profile_payload, headers=referee_headers)
    assert res.status_code == status.HTTP_201_CREATED
    referee_profile_id = res.json()["id"]

    # Verify a pending referral is registered
    ref_obj = db_session.query(Referral).filter(Referral.referee_id == uuid.UUID(referee_profile_id)).first()
    assert ref_obj is not None
    assert ref_obj.status == "pending"

    # Make referee verified
    admin = User(email="admin_ref@example.com", phone="+918000000003", hashed_password=pwd, role="admin")
    db_session.add(admin)
    db_session.commit()
    admin_headers = get_auth_headers(admin)
    client.patch(f"/api/v1/users/profile/{referee_profile_id}/verify?is_verified=true", headers=admin_headers)

    # 2. Referee purchases Monthly Plan
    plan = Plan(name="Monthly Plan Promotion", duration_days=30, price=3000.00, meals_included="lunch", is_active=True)
    db_session.add(plan)
    db_session.commit()

    res = client.post("/api/v1/subscriptions", json={"plan_id": str(plan.id)}, headers=referee_headers)
    sub_id = res.json()["id"]

    res = client.get("/api/v1/billing/invoices", headers=referee_headers)
    invoice = res.json()[0]

    # Trigger payment webhook for referee monthly subscription plan
    res = client.post("/api/v1/billing/webhook", json={
        "event": "payment.captured",
        "transaction_id": invoice["gateway_transaction_id"],
        "payment_status": "paid",
        "amount": "3000.00"
    })
    assert res.status_code == status.HTTP_200_OK

    # 3. Check if referral promo credit transitioned to "claimed" status
    db_session.expire_all()
    ref_obj = db_session.query(Referral).filter(Referral.referee_id == uuid.UUID(referee_profile_id)).first()
    assert ref_obj.status == "claimed"
