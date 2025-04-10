
from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter
from auth import get_current_user
from database import get_db
from models import Competency, Employee, Role, RoleCompetency
from schemas import CompetencyOut, RoleCreate, RoleResponse


router = APIRouter()


@router.post("/roles", response_model=RoleResponse)
def create_role(role_data: RoleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    # Check if role already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role already exists")

    # Create new role
    new_role = Role(role_code = role_data.role_code,name=role_data.name)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return new_role


@router.get("/roles", response_model=List[RoleResponse])
def get_all_roles(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    roles = db.query(Role).all()
    return roles



@router.get("/getrole/{role_code}", response_model=RoleResponse)
def get_role_by_id(role_code: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    role =current_user["role"] 
    if role not in ["Hod","HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    role = db.query(Role).filter(Role.role_code == role_code).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role_data: RoleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.role_code = role_data.role_code
    role.name = role_data.name
    db.commit()
    db.refresh(role)

    return role



@router.delete("/roles/{role_id}", response_model=dict)
def delete_role(role_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):

    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    employees_in_dept = db.query(Employee).filter(Employee.role_code == role.role_code).first()
    if employees_in_dept:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete department. Employees are still assigned to this role."
        )
    db.delete(role)
    db.commit()

    return {"message": "Role deleted successfully"}

