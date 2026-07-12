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
from app.models.delivery import Route, DeliveryPartner, DeliveryLog
from app.core.security import get_password_hash, create_access_token
from app.services.subscription_service import IST

# Helper to create headers
def get_auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

def test_logistics_route_and_partner_crud(client: TestClient, db_session: Session) -> None:
    """Test creating routes, registering delivery partners, and admin assignments."""
    pwd = get_password_hash("password")
    admin = User(email="admin_logistics@example.com", phone="+918000000010", hashed_password=pwd, role="admin")
    driver = User(email="driver_logistics@example.com", phone="+917000000010", hashed_password=pwd, role="delivery")
    db_session.add_all([admin, driver])
    db_session.commit()

    admin_headers = get_auth_headers(admin)
    driver_headers = get_auth_headers(driver)

    # 1. Admin creates Route
    route_payload = {
        "name": "Vigyan Nagar Route",
        "area": "Vigyan Nagar Area",
        "pincodes": ["324005", "324009"]
    }
    res = client.post("/api/v1/deliveries/routes", json=route_payload, headers=admin_headers)
    assert res.status_code == status.HTTP_201_CREATED
    route_data = res.json()
    assert route_data["name"] == "Vigyan Nagar Route"
    route_id = route_data["id"]

    # 2. Driver registers profile
    partner_payload = {
        "first_name": "Ramesh",
        "last_name": "Kumar",
        "dl_number": "DL-1234567890"
    }
    res = client.post("/api/v1/deliveries/partners", json=partner_payload, headers=driver_headers)
    assert res.status_code == status.HTTP_201_CREATED
    partner_data = res.json()
    assert partner_data["dl_number"] == "DL-1234567890"
    assert partner_data["is_verified"] is False
    partner_id = partner_data["id"]

    # Try registering again (should conflict)
    res = client.post("/api/v1/deliveries/partners", json=partner_payload, headers=driver_headers)
    assert res.status_code == status.HTTP_409_CONFLICT

    # 3. Driver uploads Driving License (DL)
    files = {"file": ("license.jpg", b"mock image content bytes", "image/jpeg")}
    res = client.post("/api/v1/deliveries/partners/upload-dl", files=files, headers=driver_headers)
    assert res.status_code == status.HTTP_200_OK
    assert "document_url" in res.json()

    # 4. Admin verifies driver DL
    res = client.patch(
        f"/api/v1/deliveries/partners/{partner_id}/verify?is_verified=true",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_verified"] is True

    # 5. Admin assigns route to verified driver
    res = client.patch(
        f"/api/v1/deliveries/partners/{partner_id}/assign-route?route_id={route_id}",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["current_route_id"] == route_id

def test_daily_run_generation_and_skipping(client: TestClient, db_session: Session) -> None:
    """Test generating runs correctly allocates active subscribers and ignores paused/expired ones."""
    pwd = get_password_hash("password")
    admin = User(email="admin_runs@example.com", phone="+918000000011", hashed_password=pwd, role="admin")
    cust_a = User(email="cust_active@example.com", phone="+919000000011", hashed_password=pwd, role="customer")
    cust_p = User(email="cust_paused@example.com", phone="+919000000012", hashed_password=pwd, role="customer")
    driver = User(email="driver_runs@example.com", phone="+917000000011", hashed_password=pwd, role="delivery")
    db_session.add_all([admin, cust_a, cust_p, driver])
    db_session.commit()

    admin_headers = get_auth_headers(admin)
    driver_headers = get_auth_headers(driver)

    # Setup route and verify driver
    route = Route(name="Route A", area="Area A", pincodes='["324005"]', is_active=True)
    db_session.add(route)
    db_session.commit()

    partner = DeliveryPartner(
        user_id=driver.id, first_name="D", last_name="Runs", dl_number="DL-RUNS",
        is_verified=True, is_active=True, current_route_id=route.id
    )
    db_session.add(partner)
    db_session.commit()

    # Customer A (Active)
    profile_a = Customer(
        user_id=cust_a.id, first_name="A", last_name="User", address="Vigyan Nagar", pincode="324005",
        aadhaar_number="111100001111", referral_code="REF-A", is_verified=True
    )
    # Customer P (Paused tomorrow)
    profile_p = Customer(
        user_id=cust_p.id, first_name="P", last_name="User", address="Vigyan Nagar", pincode="324005",
        aadhaar_number="222200002222", referral_code="REF-P", is_verified=True
    )
    plan = Plan(name="Double Plan", duration_days=30, price=3000.00, meals_included="both", is_active=True)
    db_session.add_all([profile_a, profile_p, plan])
    db_session.commit()

    # Active subscription for Customer A
    sub_a = Subscription(
        customer_id=profile_a.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=60, original_price=3000.00
    )
    # Active subscription for Customer P (but paused tomorrow)
    sub_p = Subscription(
        customer_id=profile_p.id, plan_id=plan.id, status="active",
        start_date=date.today(), end_date=date.today() + timedelta(days=30),
        remaining_meals=60, original_price=3000.00
    )
    db_session.add_all([sub_a, sub_p])
    db_session.commit()

    # Setup subscription pause for sub_p on tomorrow
    tomorrow = date.today() + timedelta(days=1)
    pause = SubscriptionPause(
        subscription_id=sub_p.id, start_date=tomorrow, end_date=tomorrow, status="active"
    )
    db_session.add(pause)
    db_session.commit()

    # 1. Admin generates delivery runs for Today Lunch
    res = client.post(
        f"/api/v1/deliveries/generate-run?delivery_date={date.today()}&meal_type=lunch",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    runs_today = res.json()
    
    # Both sub_a and sub_p should have a run today since pause is for tomorrow
    assert len(runs_today) == 2
    
    # Verify remaining meals decremented
    db_session.expire_all()
    assert sub_a.remaining_meals == 59
    assert sub_p.remaining_meals == 59

    # Generate again (should not duplicate)
    res = client.post(
        f"/api/v1/deliveries/generate-run?delivery_date={date.today()}&meal_type=lunch",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) == 0  # 0 new runs generated

    # 2. Admin generates runs for Tomorrow Lunch
    res = client.post(
        f"/api/v1/deliveries/generate-run?delivery_date={tomorrow}&meal_type=lunch",
        headers=admin_headers
    )
    assert res.status_code == status.HTTP_200_OK
    runs_tomorrow = res.json()
    
    # sub_p is paused on tomorrow, so only sub_a should get a run tomorrow!
    assert len(runs_tomorrow) == 1
    assert runs_tomorrow[0]["subscription_id"] == str(sub_a.id)

def test_delivery_status_flow_and_rejections(client: TestClient, db_session: Session) -> None:
    """Test transitions of daily run sheet logs and verification constraints."""
    pwd = get_password_hash("password")
    admin = User(email="admin_status@example.com", phone="+918000000012", hashed_password=pwd, role="admin")
    cust = User(email="cust_status@example.com", phone="+919000000013", hashed_password=pwd, role="customer")
    driver1 = User(email="driver_status1@example.com", phone="+917000000012", hashed_password=pwd, role="delivery")
    driver2 = User(email="driver_status2@example.com", phone="+917000000013", hashed_password=pwd, role="delivery")
    db_session.add_all([admin, cust, driver1, driver2])
    db_session.commit()

    admin_headers = get_auth_headers(admin)
    cust_headers = get_auth_headers(cust)
    d1_headers = get_auth_headers(driver1)
    d2_headers = get_auth_headers(driver2)

    # Setup routes and partners
    route = Route(name="Route status", area="Area status", pincodes='["324001"]', is_active=True)
    db_session.add(route)
    db_session.commit()

    p1 = DeliveryPartner(user_id=driver1.id, first_name="D1", last_name="P", dl_number="DL-S1", is_verified=True, current_route_id=route.id)
    p2 = DeliveryPartner(user_id=driver2.id, first_name="D2", last_name="P", dl_number="DL-S2", is_verified=True, current_route_id=route.id)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Subscription
    profile = Customer(user_id=cust.id, first_name="C", last_name="S", address="Vigyan", pincode="324001", aadhaar_number="999900009999", referral_code="REF-STATUS", is_verified=True)
    plan = Plan(name="Lunch Plan Status", duration_days=30, price=1500.00, meals_included="lunch", is_active=True)
    db_session.add_all([profile, plan])
    db_session.commit()

    sub = Subscription(customer_id=profile.id, plan_id=plan.id, status="active", start_date=date.today(), end_date=date.today() + timedelta(days=30), remaining_meals=30, original_price=1500.00)
    db_session.add(sub)
    db_session.commit()

    # Generate run
    log = DeliveryLog(
        subscription_id=sub.id, delivery_partner_id=p1.id, route_id=route.id,
        delivery_date=date.today(), meal_type="lunch", status="pending"
    )
    db_session.add(log)
    db_session.commit()

    # 1. Driver 1 fetches their daily sheet
    res = client.get(f"/api/v1/deliveries/daily?delivery_date={date.today()}", headers=d1_headers)
    assert res.status_code == status.HTTP_200_OK
    sheet = res.json()
    assert len(sheet) == 1
    assert sheet[0]["id"] == str(log.id)

    # 2. Driver 2 tries to update status of Driver 1's run -> Forbidden
    status_payload = {"status": "out_for_delivery"}
    res = client.patch(f"/api/v1/deliveries/{log.id}/status", json=status_payload, headers=d2_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Customer tries to update status -> Forbidden
    res = client.patch(f"/api/v1/deliveries/{log.id}/status", json=status_payload, headers=cust_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 3. Driver 1 updates status to out_for_delivery
    res = client.patch(f"/api/v1/deliveries/{log.id}/status", json=status_payload, headers=d1_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "out_for_delivery"

    # 4. Driver 1 updates status to failed (without failure reason -> Fails)
    res = client.patch(
        f"/api/v1/deliveries/{log.id}/status",
        json={"status": "failed"},
        headers=d1_headers
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Driver 1 updates status to failed (with reason -> Success)
    res = client.patch(
        f"/api/v1/deliveries/{log.id}/status",
        json={"status": "failed", "failure_reason": "Door Locked"},
        headers=d1_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "failed"
    assert res.json()["failure_reason"] == "Door Locked"

    # 5. Driver 1 updates status to delivered
    res = client.patch(
        f"/api/v1/deliveries/{log.id}/status",
        json={"status": "delivered", "photo_proof_url": "https://proofs.s3.com/del.jpg"},
        headers=d1_headers
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "delivered"
    assert res.json()["photo_proof_url"] == "https://proofs.s3.com/del.jpg"
    assert res.json()["delivered_at"] is not None

def test_admin_dashboard_metrics(client: TestClient, db_session: Session) -> None:
    """Test real-time operations stats are summarized correctly on admin dashboard."""
    pwd = get_password_hash("password")
    admin = User(email="admin_analytics@example.com", phone="+918000000013", hashed_password=pwd, role="admin")
    db_session.add(admin)
    db_session.commit()

    admin_headers = get_auth_headers(admin)

    # Seed some metrics
    route = Route(name="Route metrics", area="Area status", pincodes='["324001"]', is_active=True)
    db_session.add(route)
    db_session.commit()

    # Active Verified Driver
    driver = User(email="driver_metrics@example.com", phone="+917000000014", hashed_password=pwd, role="delivery")
    db_session.add(driver)
    db_session.commit()

    partner = DeliveryPartner(user_id=driver.id, first_name="D", last_name="M", dl_number="DL-M1", is_verified=True, is_active=True, current_route_id=route.id)
    db_session.add(partner)
    db_session.commit()

    # Fetch counters
    res = client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "active_subscriptions" in data
    assert "lunch_meal_prep_count" in data
    assert "active_drivers_count" in data
    assert data["active_drivers_count"] >= 1
    assert data["unassigned_routes_count"] == 0  # because our route has partner assigned
