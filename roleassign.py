
from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter
from auth import get_current_user
from database import get_db
from models import Competency, Role, RoleCompetency
from schemas import CompetencyOut, RoleCreate, RoleResponse

router = APIRouter()
# Get all competencies assigned to a role


@router.get("/roles/{role_code}/competencies", response_model=List[str])
def get_role_competencies(
    role_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    role = db.query(Role).filter(Role.role_code == role_code).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    assignments = db.query(RoleCompetency.competency_code).filter(
        RoleCompetency.role_code == role_code
    ).all()
    return [competency.competency_code for competency in assignments]





@router.post("/roles/{role_code}/competencies", response_model=List[str])
def assign_competencies_to_role(
    role_code: str,
    competency_codes: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    # 1. Verify role exists

    role = db.query(Role).filter(
        Role.role_code == role_code
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # 2. Get existing assignments for this role
    existing_assignments = db.query(RoleCompetency.competency_code).filter(
        RoleCompetency.role_code == role_code
    ).all()
    existing_codes = {a.competency_code for a in existing_assignments}

    # 3. Filter out already assigned competencies
    new_codes = set(competency_codes) - existing_codes
    if not new_codes:
        return []  # No new assignments needed

    # 4. Verify competencies exist and get their required scores
    competencies = db.query(Competency.code, Competency.required_score).filter(
        Competency.code.in_(new_codes)
    ).all()
    
    existing_competency_codes = {c.code for c in competencies}
    missing = new_codes - existing_competency_codes
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Competencies not found: {', '.join(missing)}"
        )

    # Create a dictionary of code to required_score
    competency_scores = {c.code: c.required_score for c in competencies}

    # 5. Create new assignments with the correct required_score
    for code in new_codes:
        rc = RoleCompetency(
            role_code=role_code,
            competency_code=code,
            required_score=competency_scores[code]
        )
        db.add(rc)
    
    db.commit()
    return list(new_codes)



# Remove competencies from a role
@router.delete("/roles/{role_code}/competencies", response_model=List[str])
def remove_competencies_from_role(
    role_code: str,
    competency_codes: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access") 
    # Verify role exists
    role = db.query(Role).filter(Role.role_code == role_code).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Delete specified assignments
    result = db.query(RoleCompetency).filter(
        RoleCompetency.role_code == role_code,
        RoleCompetency.competency_code.in_(competency_codes)
    ).delete(synchronize_session=False)
    
    db.commit()
    
    if result == 0:
        raise HTTPException(
            status_code=404,
            detail="No matching competency assignments found"
        )
    
    return competency_codes