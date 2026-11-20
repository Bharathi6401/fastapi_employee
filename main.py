
from fastapi import FastAPI, HTTPException, Depends, Response, status, Query
from pydantic import BaseModel, EmailStr, Field,field_validator
import models
from sqlalchemy.orm import Session
from database import get_db
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import Path
from fastapi.security import OAuth2PasswordRequestForm
import httpx
import logging
from schemas import UserCreate, UserLogin
from security import hash_password, verify_password
from auth import create_access_token, oauth2_scheme, verify_access_token
from typing import Optional


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    email = payload.get("sub")

    if email is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return email
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Employee Management API",
    description="API for managing employee records",
    version="1.0.0"
)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "Resource not found"
        }
    )

@app.exception_handler(400)
async def duplicate_found_handler(request:Request, exc):
    return JSONResponse(status_code=400,
                        content={
                            "success":False,
                            "message":exc.detail
                        })

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    logger.exception("Unexpected error occurred")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error"
        }
    )
@app.post("/register", status_code=201)
def register_user(user: UserCreate,db : Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
    models.User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    hashed_password=hash_password(user.password)
    new_user=models.User(email=user.email,hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
    "id": new_user.id,
    "email": new_user.email,
    "message": "User registered successfully"
}

@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        models.User.email == form_data.username).first()
    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password")
    if not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    access_token=create_access_token(data={"sub":db_user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: int

    model_config = {"from_attributes": True}
@app.get(
    "/employees/",
    summary="Get all employees",
    description="Retrieve all employee records from the database."
)
def get_employees(db: Session = Depends(get_db) ,current_user: str = Depends(get_current_user)):
    employees = db.query(models.Employee).all()
    return employees

@app.get("/employees/count")
def employee_count(db: Session=Depends(get_db),current_user: str = Depends(get_current_user)):
    employee_count=db.query(models.Employee).count()
    return {"total_employees":employee_count}


@app.get(
    "/employees/search",
    response_model=list[EmployeeResponse],
    summary="Search employees by age",
    description="Filter employees using optional minimum and maximum age."
)
def search_employees(
    min_age: Optional[int] = Query(default=None, ge=0),
    max_age: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    if (
        min_age is not None
        and max_age is not None
        and min_age > max_age
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_age cannot be greater than max_age"
        )

    query = db.query(models.Employee)

    if min_age is not None:
        query = query.filter(models.Employee.age >= min_age)

    if max_age is not None:
        query = query.filter(models.Employee.age <= max_age)

    employees = query.all()

    return employees


class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(ge=18, le=60)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Jaya",
                "email": "jaya@gmail.com",
                "age": 25
            }
        }
    }

# @app.get("/employees/{employee_id}", status_code=200,
#     response_model=EmployeeResponse)
# def get_employee_by_id(employee_id: int,db: Session = Depends(get_db)):
#     employee=db.query(models.Employee).filter(models.Employee.id ==employee_id).first()

#     if not employee:
#         raise HTTPException(status_code=404, detail="Employee not found")

#     return {
#     "id": employee.id,
#     "name": employee.name,
#     "email": employee.email,
#     "age":employee.age,
# }

@app.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee by ID"
)
def get_employee_by_id(
    employee_id: int = Path(gt=0,
        description="Enter the employee ID to retrieve"
    ),
    db: Session = Depends(get_db),current_user: str = Depends(get_current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return employee
@app.post(
    "/employees/",
    status_code=201,
    response_model=EmployeeResponse,
    summary="Create a new employee",
    description="Create an employee record with name, email and age.",
    responses={
        400: {"description": "Email already registered"},
        422: {"description": "Validation error"}
    }
)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db),current_user: str = Depends(get_current_user)):
    logger.info("Creating a new employee")
    existing_employee = db.query(models.Employee).filter(models.Employee.email == employee.email).first()
    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    new_employee = models.Employee(
        name=employee.name,
        email=employee.email,
        age=employee.age
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return new_employee

class EmployeeUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=18, le=60)

    @field_validator("name", "email", "age")
    @classmethod
    def validate_not_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

@app.patch(
    "/employees/{employee_id}",
    status_code=200,
    response_model=EmployeeResponse,
    summary="Update employee details",
    description="Update employee information using employee ID.",
    responses={
        404: {"description": "Employee not found"},
        422: {"description": "Validation error"}
    }
)
# def update_employee(employee_id: int, employee: EmployeeUpdate, db: Session = Depends(get_db)):
#     update = db.query(models.Employee).filter(
#         models.Employee.id == employee_id
#     ).first()

#     if not update:
#         raise HTTPException(status_code=404, detail="Employee not found")

#     update_data = employee.model_dump(exclude_unset=True)

#     for key, value in update_data.items():
#         setattr(update, key, value)

#     db.commit()
#     logger.info("Employee updated successfully")
#     db.refresh(update)

#     return update
def update_employee(
    employee: EmployeeUpdate,
    employee_id: int = Path(gt=0),
    db: Session = Depends(get_db),current_user: str = Depends(get_current_user)
):
    update = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()

    if not update:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = employee.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Check duplicate email
    if "email" in update_data:
        existing_employee = db.query(models.Employee).filter(
            models.Employee.email == update_data["email"],
            models.Employee.id != employee_id
        ).first()

        if existing_employee:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

    for key, value in update_data.items():
        setattr(update, key, value)

    db.commit()
    logger.info("Employee updated successfully")
    db.refresh(update)

    return update


@app.delete(
    "/employees/{employee_id}",
    status_code=204,
    summary="Delete an employee",
    description="Delete an employee using their ID.",
    responses={
        404: {"description": "Employee not found"}
    }
)
def delete_employee(employee_id:int, db:Session= Depends(get_db),current_user: str = Depends(get_current_user)):
    logger.info("deleting an employee")
    delete_employee=db.query(models.Employee).filter(models.Employee.id ==employee_id).first()
    if not delete_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(delete_employee)
    db.commit()
    logger.info("Employee deleted successfully")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/external-users")
async def get_external_users(
    current_user: str = Depends(get_current_user)
):
    url = "https://jsonplaceholder.typicode.com/users"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()

            users = response.json()

            return [
                {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"]
                }
                for user in users
            ]

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="External API returned an error"
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="External API is unavailable")
# @app.get("/")
# def home():
#     return {"message": "Welcome to Employee Management API"}



# @app.get("/about")
# def about():
#     return {
#     "project": "Employee Management",
#     "developer": "Jaya",
#     "version": "1.0"
# }

# @app.get("/employees/{employee_id}")
# def get_employee(employee_id: int):
#     return {"employee_id": employee_id, "message":"Employee fetched successfully"}


# class Employee(BaseModel):
#     name:str
#     email: EmailStr
#     age: int = Field(default=18,ge=18,le=60)

# @app.post("/employees/", status_code=201)
# def create_employee(employee: Employee):
#     return {"message": "employee created successfully",
#             "name":employee.name,
#             "email":employee.email,
#             "age": employee.age}
# employees = {
#     1: {
#         "name": "Saran",
#         "email": "saran@gmail.com",
#         "age": 25
#     }
# }
# class EmployeeUpdate(BaseModel):
#     name: str | None = None
#     email: EmailStr | None = None
#     age: int | None = Field(default=None, ge=18, le=60)

# @app.patch("/employees/{employee_id}")
# def update_employee(employee_id: int, employee: EmployeeUpdate):

#     if employee_id not in employees:
#         raise HTTPException(
#             status_code=404,
#             detail="Employee not found"
#         )

#     update_data = employee.model_dump(exclude_unset=True)

#     employees[employee_id].update(update_data)

#     return {
#         "message": "Employee updated successfully",
#         "employee": employees[employee_id]
#     }

# @app.delete("/employees/{employee_id}")
# def delete_employee(employee_id: int):

#     if employee_id not in employees:
#         raise HTTPException(
#             status_code=404,
#             detail="Employee not found"
#         )

#     employees.pop(employee_id)

#     return {
#         "message": "Employee deleted successfully"
#     }   

# def get_employee_role():
#     return "Developer"

# def get_employee_department():
#     return "IT"

# @app.get("/employee-role")
# def get_role(role : str=Depends(get_employee_role), department:str=Depends(get_employee_department)):
#     return {"role": role, "department":department}