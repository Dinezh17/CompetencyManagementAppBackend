from datetime import date
from http.client import HTTPException
from typing import List
from auth import get_current_user
from database import get_db
from fastapi import APIRouter, Depends
from models import Employee
from schemas import BulkEvaluationStatusUpdate, EmployeeEvaluationStatusUpdate, EmployeeResponse
from sqlalchemy.orm import Session



router = APIRouter()


@router.patch("/employees/evaluation-status", response_model=List[EmployeeResponse])
async def bulk_update_evaluation_status(
    update_data: BulkEvaluationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):  
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    employees = db.query(Employee).filter(
        Employee.employee_number.in_(update_data.employee_numbers)
    ).all()
    
    if not employees:
        raise HTTPException(status_code=404, detail="No employees found")
    
    for employee in employees:
        employee.evaluation_status = update_data.status
    
    db.commit()
    return employees