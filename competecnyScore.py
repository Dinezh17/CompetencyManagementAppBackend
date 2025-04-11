from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from auth import get_current_user
from database import get_db
from models import Competency, Department, Employee, EmployeeCompetency
from schemas import CompetencyCreate, CompetencyResponse, EmployeeCompetencyResponse
import schemas

router = APIRouter()

# @router.post("/evaluations")
# def submit_evaluation(
#     evaluation_data: dict,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     # Validate input
#     if not all(key in evaluation_data for key in ["employee_number", "evaluator_id", "scores"]):
#         raise HTTPException(status_code=400, detail="Invalid evaluation data format")
    
#     employee_number = evaluation_data["employee_number"]
#     evaluator_id = current_user["username"]
    
#     # Check if employee exists
#     employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
#     if not employee:
#         raise HTTPException(status_code=404, detail="Employee not found")
    
#     # Process each competency score
#     for score in evaluation_data["scores"]:
#         if not all(key in score for key in ["competency_code", "actual_score"]):
#             continue
            
#         # Update or create competency record
#         competency = db.query(EmployeeCompetency).filter(
#             EmployeeCompetency.employee_number == employee_number,
#             EmployeeCompetency.competency_code == score["competency_code"]
#         ).first()
        
#         if competency:
#             # Update existing record
#             competency.actual_score = score["actual_score"]
#             competency.last_updated = datetime.utcnow()
#             competency.updated_by = evaluator_id
        
#     employee.evaluation_status = True
#     employee.evaluation_by = evaluator_id
#     employee.last_evaluated_date = datetime.utcnow()
    
#     db.commit()
    
#     return {"message": "Evaluation submitted successfully"}

@router.post("/evaluations/{employee_number}")
def submit_evaluation(
    employee_number: str,
    evaluation_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["ADMIN","HOD"]:
        raise HTTPException(status_code=401, detail="No access")   
    # Validate input
    if "scores" not in evaluation_data:
        raise HTTPException(status_code=400, detail="Invalid evaluation data format")
    
   
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Process each competency score
    for score in evaluation_data["scores"]:
        has_competency_code = "competency_code" in score
        has_actual_score = "actual_score" in score

        if not (has_competency_code and has_actual_score):
            continue
            
        # Update or create competency record
        competency = db.query(EmployeeCompetency).filter(
            EmployeeCompetency.employee_number == employee_number,
            EmployeeCompetency.competency_code == score["competency_code"]
        ).first()
        
        if competency:
            # Update existing record
            competency.actual_score = score["actual_score"]
    evaluator_id=db.query(Employee).filter(Employee.employee_number==current_user["username"]).first()
    if not evaluator_id:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    employee.evaluation_status = True
    employee.evaluation_by = evaluator_id.employee_name
    employee.last_evaluated_date = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Evaluation submitted successfully"}










@router.get("/employee-competencies", response_model=List[EmployeeCompetencyResponse])

def get_all_employee_competencies(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["ADMIN", "HR","HOD"]:
        raise HTTPException(status_code=401, detail="No access") 


    return db.query(EmployeeCompetency).all()







@router.get("/employee-competencies/{employee_number}")
def get_employee_competencies(
    employee_number: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):  
    role =current_user["role"] 
    if role not in ["HR","ADMIN","HOD","EMPLOYEE"]:
        raise HTTPException(status_code=401, detail="No access")  
    
    if not db.query(Employee).filter(Employee.employee_number == employee_number).first():
        raise HTTPException(status_code=404, detail="Employee not found")
    
    competencies = db.query(
        EmployeeCompetency.competency_code,
        Competency.name,
        Competency.description,
        EmployeeCompetency.required_score,
        EmployeeCompetency.actual_score
    ).join(
        Competency, EmployeeCompetency.competency_code == Competency.code
    ).filter(
        EmployeeCompetency.employee_number == employee_number
    ).all()
    
    return [{
        "code": comp.competency_code,
        "name": comp.name,
        "description":comp.description,
        "required_score": comp.required_score,
        "actual_score": comp.actual_score,
        "gap":int(comp.required_score)-int(comp.actual_score)
    } for comp in competencies]
