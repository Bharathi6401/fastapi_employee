from fastapi.testclient import TestClient
from main import app, get_current_user
from database import get_db, Base
from tests.test_database import test_engine, override_get_db
from tests.test_database import TestingSessionLocal
import models
import httpx
Base.metadata.create_all(bind=test_engine)

import pytest
@pytest.fixture
def unauthenticated_client():
    app.dependency_overrides[get_db] = override_get_db

    # Ensure authentication is not overridden
    app.dependency_overrides.pop(get_current_user, None)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
# @pytest.fixture
# def client():
#     app.dependency_overrides[get_db] = override_get_db

#     with TestClient(app) as test_client:
#         yield test_client

#     app.dependency_overrides.clear()
@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: "test_user@example.com"

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

# @pytest.fixture(autouse=True)
# def clean_test_database():
#     yield

#     db = TestingSessionLocal()
#     try:
#         db.query(models.Employee).delete()
#         db.commit()
#     finally:
#         db.close()
@pytest.fixture(autouse=True)
def clean_test_database():

    def cleanup():
        db = TestingSessionLocal()
        try:
            db.query(models.Employee).delete()
            db.commit()
        finally:
            db.close()

    cleanup()  # Before each test
    yield
    cleanup()  # After each test

# def test_home():
#     response = client.get("/")

#     assert response.status_code == 200

def test_get_employees(client):

    # 1. Create Jaya using POST
    client.post(
        "/employees/",
        json={
            "name": "Jaya",
            "email": "jaya_test@gmail.com",
            "age": 25
        }
    )

    # 2. Fetch employees using GET
    response = client.get("/employees/")

    # 3. Check status code
    assert response.status_code == 200

    # 4. Check employee name
    assert response.json()[0]["name"] == "Jaya"


def test_employee_count(client):
    client.post("/employees",json={
                "name": "Andrew",
                "email": "jaya_tfgdgfdgest@gmail.com",
                "age": 25
            })
    client.post("/employees",json={
                    "name": "Abel",
                    "email": "jaya_tfbdgfgdgfdgest@gmail.com",
                    "age": 25
                })
    response=client.get("/employees/count")
    assert response.status_code==200
    assert response.json()["total_employees"] == 2

def test_get_employee_by_id(client):
    create_response=client.post("/employees",
                                json={"name":"jaya","email":"jaya@gmail.com","age":25})

    employee_id=create_response.json()["id"]
    get_employee=client.get(f"/employees/{employee_id}")

    assert get_employee.status_code==200
    assert get_employee.json()["name"] == "jaya"

def test_create_employee(client):
    response = client.post(
        "/employees/",
        json={"name":"Jaya","email":"jaya@gmail.com","age":25},)
    assert response.status_code == 201
    assert response.json()["name"] == "Jaya"
    assert response.json()["email"] == "jaya@gmail.com"



def test_create_employee_invalid_age(client):
    response = client.post(
        "/employees/",
        json={
            "name": "Invalid Employee",
            "email": "invalidemployee@gmail.com",
            "age": 15
        }
    )

    assert response.status_code == 422

def test_update_employee(client):
    create_response=client.post("/employees/",
                json={"name":"Arun",
                      "email":"arun@gmail.com",
                      "age":20})
    
    
    employee_id=create_response.json()["id"]

    update_response=client.patch(f"/employees/{employee_id}",
                 json={"name":"Kumar"},)

    assert update_response.status_code==200
    assert update_response.json()["name"]

def test_update_employee_not_found(client):

    update_response = client.patch(
        "/employees/9999",
        json={"name": "Kumar"}
    )

    assert update_response.json()["success"] is False
    assert update_response.json()["message"] == "Resource not found"


def test_delete_employee(client):
    create_response=client.post("/employees/",
                json={"name":"Arun",
                      "email":"arun@gmail.com",
                      "age":20})
    
    
    employee_id=create_response.json()["id"]

    update_response=client.delete(f"/employees/{employee_id}")

    assert update_response.status_code==204


def test_delete_employee_not_found(client):
    delete_response = client.delete(
            "/employees/9999"
        )
    
    assert delete_response.json()["success"] is False
    assert delete_response.json()["message"] == "Resource not found"
    

    
def test_create_employee_invalid_email(client):
    response = client.post(
        "/employees/",
        json={
            "name": "Test Employee",
            "email": "test123",
            "age": 25
        }
    )

    assert response.status_code == 422

def test_create_employee_duplicate_email(client):
    # First request: create employee
    client.post(
        "/employees/",
        json={
            "name": "First Employee",
            "email": "duplicate@gmail.com",
            "age": 25
        }
    )

    # Second request: use the same email
    response = client.post(
        "/employees/",
        json={
            "name": "Second Employee",
            "email": "duplicate@gmail.com",
            "age": 28
        }
    )

    assert response.json()["success"] is False
    assert response.json()["message"] == "Email already registered"


def test_update_employee_duplicate_email(client):
    client.post(
    "/employees/",
    json={
        "name": "Jaya",
        "email": "jaya@gmail.com",
        "age": 25
    }
)
    create_response=client.post("/employees/",json={"name":"Saran",
                                                    "email":"saran@gmail.com",
                                                    "age":25},
                                                  )
    employee_id=create_response.json()["id"]

    update_response=client.patch(f"/employees/{employee_id}",
                 json={"email":"jaya@gmail.com"},
                 )
    assert update_response.status_code==400
    assert update_response.json()["message"] == "Email already registered"

def test_update_employee_invalid_id(client):
    response = client.patch(
        "/employees/-2",
        json={"name": "Kumar"}
    )

    assert response.status_code == 422

def test_get_employee_invalid_id(client):
    response = client.get("/employees/-2")

    assert response.status_code == 422

def test_external_users(client, monkeypatch):

    def mock_api(request):
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Test User",
                    "email": "test@gmail.com"
                }
            ]
        )
    mock_transport = httpx.MockTransport(mock_api)
    real_async_client = httpx.AsyncClient

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=mock_transport,
            **kwargs
        )
    )
    response = client.get("/external-users")
    assert response.status_code==200
    assert response.json()[0]["name"]=="Test User"


def test_external_api_failure(client, monkeypatch):

    def mock_api(request):
        return httpx.Response(500)

    mock_transport = httpx.MockTransport(mock_api)
    real_async_client = httpx.AsyncClient

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=mock_transport,
            **kwargs
        )
    )

    response = client.get("/external-users")

    assert response.status_code == 502
    assert response.json()["detail"] == "External API returned an error"


def test_external_api_unavailable(client, monkeypatch):

    def mock_api(request):
        raise httpx.ConnectError("Connection failed")

    mock_transport = httpx.MockTransport(mock_api)
    real_async_client = httpx.AsyncClient

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=mock_transport,
            **kwargs
        )
    )

    response = client.get("/external-users")

    assert response.status_code == 503
    assert response.json()["detail"] == "External API is unavailable"
def test_update_employee_empty_data(client):

    # First create an employee
    create_response = client.post(
        "/employees/",
        json={
            "name": "Test Employee",
            "email": "emptytest@gmail.com",
            "age": 25
        }
    )

    employee_id = create_response.json()["id"]

    # Now send an empty PATCH request
    response = client.patch(
        f"/employees/{employee_id}",
        json={}
    )

    assert response.status_code == 400
    assert response.json()["message"] == "At least one field is required for update"

import pytest

@pytest.mark.parametrize(
    "field",
    ["name", "email", "age"]
)
def test_update_employee_null_fields(client, field):

    create_response = client.post(
        "/employees/",
        json={
            "name": "Test Employee",
            "email": "nulltest@gmail.com",
            "age": 25
        }
    )

    assert create_response.status_code == 201

    employee_id = create_response.json()["id"]

    response = client.patch(
        f"/employees/{employee_id}",
        json={field: None}
    )

    assert response.status_code == 422
def test_search_employees_by_age(client):
    client.post(
        "/employees/",
        json={
            "name": "Employee One",
            "email": "one@gmail.com",
            "age": 25
        }
    )

    response = client.get(
        "/employees/search",
        params={"min_age": 20, "max_age": 35}
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
def test_search_employees_invalid_age_range(client):
    response = client.get(
        "/employees/search",
        params={"min_age": 40, "max_age": 20}
    )

    assert response.status_code == 400
    assert response.json()["message"] == (
        "min_age cannot be greater than max_age"
    )
def test_search_employees_without_authentication(
    unauthenticated_client
):
    response = unauthenticated_client.get("/employees/search")

    assert response.status_code == 401