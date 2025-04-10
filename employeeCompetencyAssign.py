from typing import List
from auth import get_current_user
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Competency, Employee, EmployeeCompetency
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/employees/{employee_number}/assigncompetencies")
def add_competencies_to_employee(
    employee_number: str,
    competency_codes: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Check if current user has permission (HR or same department)
        if current_user["role"] != "HR" :
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this employee's competencies"
            )
        
        # Check all competencies exist and get their required scores
        competencies = db.query(Competency).filter(Competency.code.in_(competency_codes)).all()
        if len(competencies) != len(competency_codes):
            existing_codes = {c.code for c in competencies}
            missing_codes = set(competency_codes) - existing_codes
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Competencies not found: {', '.join(missing_codes)}"
            )
        
        # Create employee competencies
        added = []
        for competency in competencies:
            # Check if relationship already exists
            existing = db.query(EmployeeCompetency).filter(
                EmployeeCompetency.employee_number == employee_number,
                EmployeeCompetency.competency_code == competency.code
            ).first()
            
            if not existing:
                emp_comp = EmployeeCompetency(
                    employee_number=employee_number,
                    competency_code=competency.code,
                    required_score=competency.required_score,
                    actual_score=0
                )
                db.add(emp_comp)
                added.append(competency.code)
        
        db.commit()
        return {"message": f"Successfully added competencies: {', '.join(added)}"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding competencies: {str(e)}"
        )



@router.delete("/employees/{employee_number}/deletecompetencies")
def remove_competencies_from_employee(
    employee_number: str,
    competency_codes: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Check if current user has permission (HR or same department)
        if current_user["role"] != "HR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this employee's competencies"
            )
        
        # Delete the employee competencies
        deleted_count = db.query(EmployeeCompetency).filter(
            EmployeeCompetency.employee_number == employee_number,
            EmployeeCompetency.competency_code.in_(competency_codes)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        if deleted_count == 0:
            return {"message": "No matching competencies found to remove"}
        
        return {"message": f"Successfully removed {deleted_count} competencies"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing competencies: {str(e)}"
        )
    




@router.get("/employees/{employee_number}/assignedcompetencies", response_model=List[dict])
def get_employee_competencies(
    employee_number: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.employee_number == employee_number).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Check if current user has permission (HR or same department)
        if current_user["role"] != "HR" and employee.department_code != current_user["department_code"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this employee's competencies"
            )
        
        # Query employee competencies with competency details
        employee_competencies = db.query(EmployeeCompetency, Competency)\
            .join(Competency, EmployeeCompetency.competency_code == Competency.code)\
            .filter(EmployeeCompetency.employee_number == employee_number)\
            .all()
        
        # Format the response
        response = []
        for emp_comp, comp in employee_competencies:
            response.append({
                "code": comp.code,
                "name": comp.name,
                "required_score": emp_comp.required_score,
                "actual_score": emp_comp.actual_score
            })
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employee competencies: {str(e)}"
        )