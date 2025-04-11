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



@router.post("/competency", response_model=CompetencyResponse)
def create_competency(
    competency: CompetencyCreate, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # Checking if competency already exists
    role =current_user["role"] 
    if role not in ["HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    db_competency = db.query(Competency).filter(Competency.code == competency.code).first()
    if db_competency:
        raise HTTPException(status_code=400, detail="Competency code already exists")
    
    new_competency = Competency(
        code=competency.code,
        name=competency.name,
        description=competency.description,
        required_score = competency.required_score
    )
    
    db.add(new_competency)
    db.commit()
    db.refresh(new_competency)
    
    return new_competency



@router.get("/competency", response_model=List[CompetencyResponse])
def get_all_competencies(db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    
    role =current_user["role"] 
    if role not in ["HOD", "HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    return db.query(Competency).all()




@router.put("/competency/{competency_id}", response_model=CompetencyResponse)
def update_competency(
    competency_id: int, 
    competency: CompetencyCreate, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    db_competency = db.query(Competency).filter(Competency.id == competency_id).first()
    if not db_competency:
        raise HTTPException(status_code=404, detail="Competency not found")
     
    if competency.code != db_competency.code:
        existing_code = db.query(Competency).filter(Competency.code == competency.code).first()
        if existing_code:
            raise HTTPException(status_code=400, detail="Competency code already exists")
    
    db_competency.code = competency.code
    db_competency.name = competency.name
    db_competency.description = competency.description
    db_competency.required_score = competency.required_score

    db.commit()
    db.refresh(db_competency)
    
    return db_competency



@router.delete("/competency/{competency_id}")
def delete_competency(
    competency_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)):
    
    role =current_user["role"] 
    if role not in ["HR","ADMIN"]:
        raise HTTPException(status_code=401, detail="No access")  
    competency = db.query(Competency).filter(Competency.id == competency_id).first()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    employees_in_dept = db.query(EmployeeCompetency).filter(EmployeeCompetency.competency_code == competency.code).first()
    if employees_in_dept:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete department. Employees are still assigned to this competency."
        )
    
    db.delete(competency)
    db.commit()
    return {"message": "Competency deleted successfully"}

























