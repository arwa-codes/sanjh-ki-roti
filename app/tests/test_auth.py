from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import get_password_hash

def test_register_user_success(client: TestClient) -> None:
    """Test successful user registration."""
    payload = {
        "email": "customer@example.com",
        "phone": "+919999999999",
        "password": "securepassword123",
        "role": "customer"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["role"] == payload["role"]
    assert "id" in data
    assert "password" not in data

def test_register_user_duplicate_email(client: TestClient, db_session: Session) -> None:
    """Test registration failure with duplicate email."""
    # Seed initial user
    hashed_pwd = get_password_hash("somepassword")
    existing_user = User(
        email="duplicate@example.com",
        phone="+918888888888",
        hashed_password=hashed_pwd,
        role="customer"
    )
    db_session.add(existing_user)
    db_session.commit()

    payload = {
        "email": "duplicate@example.com",
        "phone": "+917777777777",
        "password": "newpassword123",
        "role": "customer"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]

def test_register_user_duplicate_phone(client: TestClient, db_session: Session) -> None:
    """Test registration failure with duplicate phone."""
    # Seed initial user
    hashed_pwd = get_password_hash("somepassword")
    existing_user = User(
        email="first@example.com",
        phone="+919999988888",
        hashed_password=hashed_pwd,
        role="customer"
    )
    db_session.add(existing_user)
    db_session.commit()

    payload = {
        "email": "second@example.com",
        "phone": "+919999988888",
        "password": "newpassword123",
        "role": "customer"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]

def test_login_success(client: TestClient, db_session: Session) -> None:
    """Test successful login and token generation."""
    hashed_pwd = get_password_hash("mypassword")
    user = User(
        email="login@example.com",
        phone="+919999955555",
        hashed_password=hashed_pwd,
        role="customer"
    )
    db_session.add(user)
    db_session.commit()

    # Form login expects username and password parameters
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "mypassword"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(client: TestClient, db_session: Session) -> None:
    """Test login rejection on invalid password."""
    hashed_pwd = get_password_hash("mypassword")
    user = User(
        email="login@example.com",
        phone="+919999955555",
        hashed_password=hashed_pwd,
        role="customer"
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]

def test_get_me_success(client: TestClient, db_session: Session) -> None:
    """Test retrieving authenticated user profile."""
    hashed_pwd = get_password_hash("mypassword")
    user = User(
        email="me@example.com",
        phone="+919999944444",
        hashed_password=hashed_pwd,
        role="customer"
    )
    db_session.add(user)
    db_session.commit()

    # Authenticate to get token
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "me@example.com", "password": "mypassword"}
    )
    token = login_response.json()["access_token"]

    # Send profile request with Bearer Authorization token header
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["phone"] == "+919999944444"

def test_get_me_unauthorized(client: TestClient) -> None:
    """Test profile request rejection when missing token header."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
