from fastapi.testclient import TestClient
from main import app
from database import get_db, Base
from test_database import test_engine, override_get_db
from test_database import TestingSessionLocal
import models
Base.metadata.create_all(bind=test_engine)

import pytest

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_test_database():
    yield

    db = TestingSessionLocal()
    try:
        db.query(models.Employee).delete()
        db.commit()
    finally:
        db.close()

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
        json={
            "name": "Arun",
            "email": "arun_test@gmail.com",
            "age": 25
        }
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Arun"
    assert response.json()["email"] == "arun_test@gmail.com"



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

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Employee not found"


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
    
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Employee not found"
    

    
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

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"