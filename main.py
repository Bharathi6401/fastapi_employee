
from fastapi import FastAPI, HTTPException, Depends, Response, status
from pydantic import BaseModel, EmailStr, Field
from database import engine, Base
import models
from sqlalchemy.orm import Session
from database import get_db


Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/employees/")
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).all()
    return employees

class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(ge=18, le=60)

@app.post("/employees/", status_code=201)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
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

@app.patch("/employees/{employee_id}")
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
    db.refresh(update)

    return update



@app.delete("/employees/{employee_id}")
def delete_employee(employee_id:int, db:Session= Depends(get_db)):
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