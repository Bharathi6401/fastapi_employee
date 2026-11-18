
from fastapi import FastAPI, HTTPException, Depends, Response, status
from pydantic import BaseModel, EmailStr, Field
import models
from sqlalchemy.orm import Session
from database import get_db
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import Path

import logging

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
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error"
        }
    )

@app.get(
    "/employees/",
    summary="Get all employees",
    description="Retrieve all employee records from the database."
)
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).all()
    return employees



class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: int

    model_config = {"from_attributes": True}
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
    db: Session = Depends(get_db)
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
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
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
    name: str | None=None
    email: EmailStr |None = None
    age : int | None =Field(default=None, ge=18, le=60)
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
def update_employee(employee_id: int, employee: EmployeeUpdate, db: Session = Depends(get_db)):
    update = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()

    if not update:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = employee.model_dump(exclude_unset=True)

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
def delete_employee(employee_id:int, db:Session= Depends(get_db)):
    logger.info("deleting an employee")
    delete_employee=db.query(models.Employee).filter(models.Employee.id ==employee_id).first()
    if not delete_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(delete_employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

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