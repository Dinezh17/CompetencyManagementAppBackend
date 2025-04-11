from datetime import date
from fastapi import APIRouter, Depends, File, UploadFile
from models import Competency, Department, Employee, EmployeeCompetency, Role, RoleCompetency
from fastapi.responses import JSONResponse
import pandas as pd
import re
import json
from io import BytesIO
from typing import List
from sqlalchemy.orm import Session
from models import Employee, EmployeeCompetency, RoleCompetency
from database import get_db
from auth import get_current_user
from schemas import BulkEvaluationStatusUpdate, EmployeeCreateRequest, EmployeeEvaluationStatusUpdate, EmployeeResponse





router = APIRouter()
from fastapi import HTTPException, status



@router.get("/employee/{employee_number}", response_model=dict)
def get_employee_details(
    employee_number: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):      
    role =current_user["role"] 
    if role not in ["HR","ADMIN","EMPLOYEE","HOD"]:
        raise HTTPException(status_code=401, detail="No access")  
    # Use JOIN to fetch employee with department and role names in a single query
    employee_data = db.query(
        Employee,
        Department.name.label("department_name"),
        Role.name.label("role_name")
    ).join(
        Department, Employee.department_code == Department.department_code
    ).join(
        Role, Employee.role_code == Role.role_code
    ).filter(
        Employee.employee_number == employee_number
    ).first()
    
    if not employee_data:
        # If the employee exists but has no related department or role, try fetching just the employee
        employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Default values for missing relationships
        department_name = "Unknown Department"
        role_name = "Unknown Role"
    else:
        employee = employee_data[0]  # First item is the Employee object
        department_name = employee_data[1]  # Second item is department_name
        role_name = employee_data[2]  # Third item is role_name
    
    # Return employee details with department and role names
    print(department_name,role_name)
    return {
        "employee": {
            "employee_number": employee.employee_number,
            "employee_name": employee.employee_name,
            "job_code": employee.job_code,
            "reporting_employee_name": employee.reporting_employee_name,
            "role_code": employee.role_code,
            "department_code": employee.department_code,
            "evaluation_status": employee.evaluation_status,
            "evaluation_by": employee.evaluation_by,
            "last_evaluated_date": employee.last_evaluated_date.isoformat() if employee.last_evaluated_date else None,
            "department": department_name,
            "role": role_name
    }
    }


@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    employee_data: EmployeeCreateRequest, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Check if employee already exists
    role =current_user["role"] 
    if role not in [ "HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    existing_employee = db.query(Employee).filter(
        Employee.employee_number == employee_data.employee_number
    ).first()
    
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with number {employee_data.employee_number} already exists"
        )
    
    try:
        # Create employee
        db_employee = Employee(**employee_data.dict())
        db.add(db_employee)
        db.flush()  # Ensure we get the employee_number
        
        # Get competencies for the role
        role_competencies = db.query(RoleCompetency).filter(
            RoleCompetency.role_code == employee_data.role_code
        ).all()
        
        # Create employee competencies
        for rc in role_competencies:
            db_competency = EmployeeCompetency(
                employee_number=db_employee.employee_number,
                competency_code=rc.competency_code,
                required_score=rc.required_score,
                actual_score=0 # Changed to None as per your original requirement
            )
            db.add(db_competency)
        
        db.commit()
        db.refresh(db_employee)
        return db_employee
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee: {str(e)}"
        )
    




@router.put("/employees/{employee_number}", response_model=EmployeeResponse)
def update_employee(
    employee_number: str,
    employee_data: EmployeeCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):  
    role =current_user["role"] 
    if role not in ["HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:
        # Check if employee exists
        db_employee = db.query(Employee).filter(
            Employee.employee_number == employee_number
        ).first()
        
        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with number {employee_number} not found"
            )
        
        # Check if new employee_number already exists (if it's being changed)
        if employee_number != employee_data.employee_number:
            existing_employee = db.query(Employee).filter(
                Employee.employee_number == employee_data.employee_number
            ).first()
            
            if existing_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with number {employee_data.employee_number} already exists"
                )
        
        # First delete all existing employee competencies
        db.query(EmployeeCompetency).filter(
            EmployeeCompetency.employee_number == employee_number
        ).delete()
        
        # Update employee data
        for field, value in employee_data.dict().items():
            setattr(db_employee, field, value)
        
        # Get competencies for the new role
        role_competencies = db.query(RoleCompetency).filter(
            RoleCompetency.role_code == employee_data.role_code
        ).all()
        
        # Create new employee competencies
        for rc in role_competencies:
            db_competency = EmployeeCompetency(
                employee_number=employee_data.employee_number,
                competency_code=rc.competency_code,
                required_score=rc.required_score,
                actual_score=0
            )
            db.add(db_competency)
        
        db.commit()
        db.refresh(db_employee)
        return db_employee
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating employee: {str(e)}"
        )

@router.delete("/employees/{employee_number}")
def delete_employee(
    employee_number: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):  
    role =current_user["role"] 
    if role not in ["HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:

        db_employee = db.query(Employee).filter(
            Employee.employee_number == employee_number
        ).first()
        
        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with number {employee_number} not found"
            )
        
        # First delete all employee competencies
        db.query(EmployeeCompetency).filter(
            EmployeeCompetency.employee_number == employee_number
        ).delete()
        
        # Then delete the employee
        db.delete(db_employee)
        db.commit()
        
        return {"message": f"Employee {employee_number} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting employee: {str(e)}"
        )



@router.get("/employees", response_model=List[EmployeeResponse])
def get_all_employees(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HOD", "HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:
        if(current_user["role"]=="HR"):

            employees = db.query(Employee).all()
            return employees
        
        else:
            employees = db.query(Employee).filter(
            Employee.department_code == current_user["department_code"]
        ).all()
            
            return employees

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employees: {str(e)}"
        )





