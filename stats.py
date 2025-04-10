# analytics.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from auth import get_current_user
from database import get_db
from models import Department, Employee, EmployeeCompetency, Competency, RoleCompetency

router = APIRouter()


@router.get("/fetch-all-competency-score-data")
def get_competency_gap_data(db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)):
    role =current_user["role"] 
    if role not in [ "HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    competencies = db.query(Competency).all()
    result = []

    for comp in competencies:
        gap1 = 0
        gap2 = 0
        gap3 = 0

        # Get all employee competencies for this competency
        records = db.query(EmployeeCompetency).filter(
            EmployeeCompetency.competency_code == comp.code
        ).all()

        for record in records:
            if record.required_score is not None and record.actual_score is not None:
                gap = record.required_score - record.actual_score
                if gap == 1:
                    gap1 += 1
                elif gap == 2:
                    gap2 += 1
                elif gap == 3:
                    gap3 += 1

        result.append({
            "competencyCode": comp.code,
            "competencyName": comp.name,
            "gap1": gap1,
            "gap2": gap2,
            "gap3": gap3,
            "totalGapEmployees": gap1 + gap2 + gap3
        })

    return result




@router.get("/employee-competencies/details")
def get_all_employee_competency_details(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role = current_user["role"]
    if role not in ["HOD", "HR"]:
        raise HTTPException(status_code=401, detail="No access")

    results = (
        db.query(
            Employee.employee_number,
            Employee.employee_name,
            Competency.code.label("competency_code"),
            Competency.name.label("competency_name"),
            Competency.description.label("competency_description"),
            EmployeeCompetency.required_score,
            EmployeeCompetency.actual_score
        )
        .join(Employee, Employee.employee_number == EmployeeCompetency.employee_number)
        .join(Competency, Competency.code == EmployeeCompetency.competency_code)
        .all()
    )

    return [
        {
            "employeeNumber": r.employee_number,
            "employeeName": r.employee_name,
            "competencyCode": r.competency_code,
            "competencyName": r.competency_name,
            "competencyDescription": r.competency_description,
            "requiredScore": r.required_score,
            "actualScore": r.actual_score
        }
        for r in results
    ]

@router.get("/score-emp-details/by-competency/{compcode}")
def get_employee_gaps_by_competency(
    compcode: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    role =current_user["role"] 
    if role not in [ "HR"]:
        raise HTTPException(status_code=401, detail="No access")  
   
    records = (
        db.query(EmployeeCompetency, Employee)
        .join(Employee, Employee.employee_number == EmployeeCompetency.employee_number)
        .filter(EmployeeCompetency.competency_code == compcode)
        .all()
    )

    result = []

    for comp, emp in records:
        if comp.required_score is not None and comp.actual_score is not None:
            gap = comp.required_score - comp.actual_score
            if gap > 0:
                result.append({
                    "employeeNumber": comp.employee_number,
                    "employeeName": emp.employee_name,
                    "requiredScore": comp.required_score,
                    "actualScore": comp.actual_score,
                    "gap": gap
                })

    # Sort by descending gap
    result.sort(key=lambda x: x["gap"], reverse=True)

    return result




class DepartmentCompetencyStats(BaseModel):
    department_code: str
    department_name: str
    rank: int
    average_score: float
    fulfillment_rate: float  

class CompetencyPerformance(BaseModel):
    competency_code: str
    competency_name: str
    description: str
    required_score: int
    departments: List[DepartmentCompetencyStats]




    
 
@router.get("/stats/department-performance/{department_code}", response_model=Dict[str, Any])
def get_competency_by_department_stats(
    department_code: str,
    db: Session = Depends(get_db)
):
    """
    Get department performance statistics showing all competencies
    for a specific department with rankings.
    """
    # Verify department exists
    department = db.query(Department).filter(Department.department_code == department_code).first()
    if not department:
        raise HTTPException(status_code=404, detail=f"Department with code {department_code} not found")
    
    result = {}
    
    # Get all competencies with their average scores for this department
    competency_stats = (
        db.query(
            Competency.code,
            Competency.name,
            Competency.description,
            Competency.required_score,
            func.avg(EmployeeCompetency.actual_score).label("average_score"),
            func.sum(
                case(
                    (EmployeeCompetency.actual_score >= EmployeeCompetency.required_score, 1),
                    else_=0
                )
            ).label("meeting_required"),
            func.count(EmployeeCompetency.id).label("total_evaluations"),
        )
        .join(
            EmployeeCompetency,
            EmployeeCompetency.competency_code == Competency.code
        )
        .join(
            Employee,
            Employee.employee_number == EmployeeCompetency.employee_number
        )
        .filter(Employee.department_code == department_code)  # Filter by department code
        .group_by(Competency.code)
        .all()
    )
    
    # Format department competency stats
    competencies_list = []
    
    for comp_stat in competency_stats:
        fulfillment_rate = (comp_stat.meeting_required / comp_stat.total_evaluations * 100) if comp_stat.total_evaluations > 0 else 0
        
        competencies_list.append({
            "competency_code": comp_stat.code,
            "competency_name": comp_stat.name,
            "description": comp_stat.description,
            "required_score": comp_stat.required_score,
            "average_score": round(comp_stat.average_score, 2),
            "fulfillment_rate": round(fulfillment_rate, 2),
            "employees_evaluated": comp_stat.total_evaluations,
            "employees_meeting_required": comp_stat.meeting_required
        })
    
    # Sort competencies by average score (best to worst performing)
    competencies_list = sorted(competencies_list, key=lambda x: x["average_score"], reverse=True)
    
    # Add ranking
    for i, comp in enumerate(competencies_list, 1):
        comp["rank"] = i
    
    # Calculate overall department performance
    if competencies_list:
        avg_score = sum(comp["average_score"] for comp in competencies_list) / len(competencies_list)
        avg_fulfillment = sum(comp["fulfillment_rate"] for comp in competencies_list) / len(competencies_list)
    else:
        avg_score = 0
        avg_fulfillment = 0
        
    result[department.department_code] = {
        "department_name": department.name,
        "overall_average_score": round(avg_score, 2),
        "overall_fulfillment_rate": round(avg_fulfillment, 2),
        "competencies": competencies_list
    }
    
    return result





class OverallCompetencyPerformance(BaseModel):
    rank: int
    competency_code: str
    competency_name: str
    description: str
    required_score: int
    average_score: float
    fulfillment_rate: float  # Percentage of employees meeting required score
    total_evaluations: int
    employees_meeting_required: int
    performance_gap: float  # Difference between average and required score



@router.get("/stats/overall-competency-performance", response_model=List[OverallCompetencyPerformance])
def get_overall_competency_performance(db: Session = Depends(get_db)):
    """
    Get overall competency performance statistics ranked from best to worst performing
    across the entire organization.
    """
    # Query to calculate statistics for each competency across all departments
    competency_stats = (
        db.query(
            Competency.code,
            Competency.name,
            Competency.description,
            Competency.required_score,
            func.avg(EmployeeCompetency.actual_score).label("average_score"),
            func.count(EmployeeCompetency.id).label("total_evaluations"),
            func.sum(
                case(
                    (EmployeeCompetency.actual_score >= EmployeeCompetency.required_score, 1),
                    else_=0
                )
            ).label("meeting_required")
        )
        .join(
            EmployeeCompetency,
            EmployeeCompetency.competency_code == Competency.code
        )
        .join(
            Employee,
            Employee.employee_number == EmployeeCompetency.employee_number
        )
        .group_by(Competency.code, Competency.name, Competency.description, Competency.required_score)
        .all()
    )
    
    # Process and rank the results 
    result = []
    
    for comp_stat in competency_stats:
        avg_score = comp_stat.average_score or 0
        fulfillment_rate = (comp_stat.meeting_required / comp_stat.total_evaluations * 100) if comp_stat.total_evaluations > 0 else 0
        performance_gap = avg_score - comp_stat.required_score
        
        result.append({
            "competency_code": comp_stat.code,
            "competency_name": comp_stat.name,
            "description": comp_stat.description,
            "required_score": comp_stat.required_score,
            "average_score": round(avg_score, 2),
            "fulfillment_rate": round(fulfillment_rate, 2),
            "total_evaluations": comp_stat.total_evaluations,
            "employees_meeting_required": comp_stat.meeting_required,
            "performance_gap": round(performance_gap, 2)
        })
    
    # Rank the competencies by fulfillment rate (alternative: could use average_score)
    # You can change the sorting key as needed
    result = sorted(result, key=lambda x: (x["fulfillment_rate"], x["average_score"]), reverse=True)
    
    # Add ranking
    ranked_result = []
    for i, comp in enumerate(result, 1):
        ranked_result.append(
            OverallCompetencyPerformance(
                rank=i,
                competency_code=comp["competency_code"],
                competency_name=comp["competency_name"],
                description=comp["description"],
                required_score=comp["required_score"],
                average_score=comp["average_score"],
                fulfillment_rate=comp["fulfillment_rate"],
                total_evaluations=comp["total_evaluations"],
                employees_meeting_required=comp["employees_meeting_required"],
                performance_gap=comp["performance_gap"]
            )
        )
    
    
    return ranked_result
