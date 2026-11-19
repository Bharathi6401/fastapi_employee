import pytest
from fastapi.testclient import TestClient
from auth import create_access_token
from main import app
from datetime import datetime, timedelta, timezone
from jose import jwt
from database import get_db
from tests.test_database import override_get_db
from auth import SECRET_KEY, ALGORITHM  
import pytest
from fastapi.testclient import TestClient

from main import app
from auth import create_access_token, SECRET_KEY, ALGORITHM
from database import Base, get_db
from tests.test_database import (
    test_engine,
    override_get_db,
    TestingSessionLocal
)

import models
from datetime import datetime, timedelta, timezone
from jose import jwt

Base.metadata.create_all(bind=test_engine)
@pytest.fixture
def auth_client():
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def clean_user_database():
    def cleanup():
        db = TestingSessionLocal()
        try:
            db.query(models.User).delete()
            db.commit()
        finally:
            db.close()

    cleanup()
    yield
    cleanup()
def test_get_employees_without_token(auth_client):
    response = auth_client.get("/employees/")

    assert response.status_code == 401

def test_get_employees_with_invalid_token(auth_client):
    headers = {
        "Authorization": "Bearer invalid_token_123"
    }

    response = auth_client.get(
        "/employees/",
        headers=headers
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"

def test_get_employees_with_valid_token(auth_client):
    token = create_access_token(
        data={"sub": "test_user@example.com"}
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = auth_client.get(
        "/employees/",
        headers=headers
    )

    assert response.status_code == 200

def test_get_employees_with_expired_token(auth_client):
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    token = jwt.encode(
        {
            "sub": "test_user@example.com",
            "exp": expired_time
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = auth_client.get(
        "/employees/",
        headers=headers
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_register_user(auth_client):
    response = auth_client.post(
        "/register",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 201
    assert response.json()["email"] == "testuser@example.com"
    assert response.json()["message"] == "User registered successfully"
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()

def test_register_duplicate_email(auth_client):
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123"
    }

    # First registration
    auth_client.post("/register", json=user_data)

    # Second registration with same email
    response = auth_client.post("/register", json=user_data)

    assert response.status_code == 400
    assert response.json()["message"] == "Email already registered"

def test_login_success(auth_client):
    # First register the user
    auth_client.post(
        "/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123"
        }
    )

    # Then log in
    response = auth_client.post(
        "/login",
        data={
            "username": "login@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(auth_client):
    auth_client.post(
        "/register",
        json={
            "email": "wrongpass@example.com",
            "password": "testpassword123"
        }
    )

    response = auth_client.post(
        "/login",
        data={
            "username": "wrongpass@example.com",
            "password": "wrongpassword123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_login_unknown_email(auth_client):
    response = auth_client.post(
        "/login",
        data={
            "username": "unknown@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"