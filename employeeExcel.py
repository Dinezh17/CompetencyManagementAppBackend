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



#below this is not stable yet need to be tested soo remember that


# def process_excel_content(excel_content: bytes) -> List[dict]:

#     xls = pd.ExcelFile(BytesIO(excel_content))
#     csv_content = []
    
#     for sheet_name in xls.sheet_names:
#         csv_content.append(f"--- Sheet: {sheet_name} ---,\n")
#         df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
#         for row in df.values:
#             clean_row = [str(cell).strip().replace(',', '/') if pd.notna(cell) else "" for cell in row]
            
#             cleaned = []
#             prev_empty = False
#             for cell in clean_row:
#                 if cell == "":
#                     if not prev_empty:
#                         cleaned.append(cell)
#                     prev_empty = True
#                 else:
#                     cleaned.append(cell)
#                     prev_empty = False
            
#             csv_line = ",".join([cell for cell in cleaned if cell != ""]) + ","
#             csv_line = re.sub(r',,+', ',', csv_line)
            
#             if csv_line.strip(','):
#                 csv_content.append(csv_line + "\n")
        
#         csv_content.append(",\n") 
    
#     employees = []
#     current_employee = None
#     current_sheet = ""
#     words = []
    
#     for line in csv_content:
#         line = line.strip()
#         if not line:
#             continue
        
#         raw_parts = line.split(',')

#         line_words = []

#         for part in raw_parts:
#              stripped_word = part.strip()
    
#              if stripped_word:
#                   line_words.append(stripped_word)

#         words.extend(line_words)

#     i = 0
#     while i < len(words):
#         word = words[i]
        
#         if word.startswith('--- Sheet:'):
#             if current_employee is not None:
#                 employees.append(current_employee)
#             current_employee = {
#                 "EmployeeNumber": "",
#                 "EmployeeName": "",
#                 "JobCode": "",
#                 "ReportingEmployeeName": "",
#                 "RoleCode": "",
#                 "Department": ""
#             }
#             current_sheet = word.replace('--- Sheet:', '').replace('---', '').strip()
#             i += 1
#             continue
        
#         if word == "Employee Number" and i+1 < len(words):
#             current_employee["EmployeeNumber"] = words[i+1]
#             i += 2
#         elif word == "Employee Name" and i+1 < len(words):
#             current_employee["EmployeeName"] = words[i+1]
#             i += 2
#         elif word == "Job Code" and i+1 < len(words):
#             current_employee["JobCode"] = words[i+1]
#             i += 2
#         elif word == "Reporting Employee Name" and i+1 < len(words):
#             current_employee["ReportingEmployeeName"] = words[i+1]
#             i += 2
#         elif word == "Role Code" and i+1 < len(words):
#             current_employee["RoleCode"] = words[i+1]
#             i += 2
#         elif word == "Department & Cost Centre" and i+1 < len(words):
#             current_employee["Department"] = words[i+1]
#             i += 2
#         else:
#             i += 1
    
#     if current_employee is not None:
#         employees.append(current_employee)
    
#     return employees
def process_excel_content(excel_content: bytes) -> List[dict]:
    xls = pd.ExcelFile(BytesIO(excel_content))
    csv_content = []
    
    for sheet_name in xls.sheet_names:
        csv_content.append(f"--- Sheet: {sheet_name} ---,\n")
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        for row in df.values:
            clean_row = [str(cell).strip().replace(',', '/') if pd.notna(cell) else "" for cell in row]
            
            cleaned = []
            prev_empty = False
            for cell in clean_row:
                if cell == "":
                    if not prev_empty:
                        cleaned.append(cell)
                    prev_empty = True
                else:
                    cleaned.append(cell)
                    prev_empty = False
            
            csv_line = ",".join([cell for cell in cleaned if cell != ""]) + ","
            csv_line = re.sub(r',,+', ',', csv_line)
            
            if csv_line.strip(','):
                csv_content.append(csv_line + "\n")
        
        csv_content.append(",\n")
    
    employees = []
    current_employee = None
    current_sheet = ""
    words = []
    in_competencies = False
    rpl_apl_count = 0
    
    for line in csv_content:
        line = line.strip()
        if not line:
            continue
        
        raw_parts = line.split(',')
        line_words = []
        
        for part in raw_parts:
            stripped_word = part.strip()
            if stripped_word:
                line_words.append(stripped_word)
        
        words.extend(line_words)

    i = 0
    while i < len(words):
        word = words[i]
        
        if word.startswith('--- Sheet:'):
            if current_employee is not None:
                employees.append(current_employee)
            current_employee = {
                "EmployeeNumber": "",
                "EmployeeName": "",
                "JobCode": "",
                "ReportingEmployeeName": "",
                "RoleCode": "",
                "Department": "",
                "Competencies": []
            }
            in_competencies = False
            rpl_apl_count = 0
            current_sheet = word.replace('--- Sheet:', '').replace('---', '').strip()
            i += 1
            continue
        
        if not in_competencies:
            if word == "Employee Number" and i+1 < len(words):
                current_employee["EmployeeNumber"] = words[i+1]
                i += 2
            elif word == "Employee Name" and i+1 < len(words):
                current_employee["EmployeeName"] = words[i+1]
                i += 2
            elif word == "Job Code" and i+1 < len(words):
                current_employee["JobCode"] = words[i+1]
                i += 2
            elif word == "Reporting Employee Name" and i+1 < len(words):
                current_employee["ReportingEmployeeName"] = words[i+1]
                i += 2
            elif word == "Role Code" and i+1 < len(words):
                current_employee["RoleCode"] = words[i+1]
                i += 2
            elif word == "Department & Cost Centre" and i+1 < len(words):
                current_employee["Department"] = words[i+1]
                i += 2
            elif word == "RPL/APL":
                rpl_apl_count += 1
                if rpl_apl_count == 2:  # Second occurrence starts competencies
                    in_competencies = True
                i += 1
            else:
                i += 1
        else:
            # Competency parsing logic
            if i + 2 < len(words):
                # Skip headers
                if words[i] in ["Functional competencies", "Behavioral competencies"]:
                    i += 1
                    continue
                
                # Get score part before slash and convert to integer
                raw_score = words[i+2]
                score = int(raw_score.split('/')[0]) if raw_score else 0
                
                current_employee["Competencies"].append({
                    "Code": words[i+1],
                    "Score": score
                })
                i += 3
            else:
                i += 1
    
    if current_employee is not None:
        employees.append(current_employee)
    
    return employees


# @router.post("/employees/upload-excel")
# async def upload_excel_employees(
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     # current_user: dict = Depends(get_current_user)
# ):

#     try:
#         # Read and process Excel file using your exact method
#         excel_content = await file.read()
#         employee_data = process_excel_content(excel_content)
        
#         results = []
        
#         for emp in employee_data:
#             try:
#                 # Check if employee exists
#                 if db.query(Employee).filter_by(employee_number=emp["EmployeeNumber"]).first():
#                     results.append({
#                         "employee_number": emp["EmployeeNumber"],
#                         "status": "error",
#                         # "Employee_name":emp["EmployeeName"],
#                         "message": "Employee already exists"
#                     })
#                     continue
                
#                 # Create new employee
#                 new_employee = Employee(
#                     employee_number=emp["EmployeeNumber"],
#                     employee_name=emp["EmployeeName"],
#                     job_code=emp["JobCode"],
#                     reporting_employee_name=emp["ReportingEmployeeName"],
#                     role_code=emp["RoleCode"],
#                     department_id=1,  # You'll need to map department names to IDs
#                     evaluation_status=False,
#                     evaluation_by=None,
#                     last_evaluated_date=None
#                 )
#                 db.add(new_employee)
#                 db.flush()
                
#                 # Add competencies
#                 competencies = db.query(RoleCompetency).filter_by(
#                     role_code=emp["RoleCode"]
#                 ).all()
                
#                 for comp in competencies:
#                     db.add(EmployeeCompetency(
#                         employee_number=new_employee.employee_number,
#                         competency_code=comp.competency_code,
#                         required_score=comp.required_score,
#                         actual_score=None
#                     ))
                
#                 db.commit()
                
#                 results.append({
#                     "employee_number": emp["EmployeeNumber"],
#                     "status": "success",
#                     "message": "Employee created successfully"
#                 })
                
#             except Exception as e:
#                 db.rollback()
#                 results.append({
#                     "employee_number": emp.get("EmployeeNumber", "UNKNOWN"),
#                     "status": "error",
#                     "message": str(e)
#                 })
        
#         return JSONResponse(content={
#             "results": results,
#             "total_processed": len(employee_data),
#             "success_count": len([r for r in results if r["status"] == "success"]),
#             "error_count": len([r for r in results if r["status"] == "error"])
#         })
    
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Error processing file: {str(e)}"
#         )
    

@router.post("/employees/upload-excel")
async def upload_excel_employees(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):  
    role =current_user["role"] 
    if role not in ["HR"]:
        raise HTTPException(status_code=401, detail="No access")  
    try:
        excel_content = await file.read()
        employee_data = process_excel_content(excel_content)
        
        results = []
        
        for emp in employee_data:
            try:
                # Check if employee exists
                if db.query(Employee).filter_by(employee_number=emp["EmployeeNumber"]).first():
                    results.append({
                        "employee_number": emp["EmployeeNumber"],
                        "status": "error",
                        "message": "Employee already exists"
                    })
                    continue
                
                # Verify department exists
                department = db.query(Department).filter(
                    (
                        Department.department_code == emp["Department"]
                    )
                ).first()
                
                if not department:
                    results.append({
                        "employee_number": emp["EmployeeNumber"],
                        "status": "error",
                        "message": f"Department '{emp['Department']}' not found"
                    })
                    continue
                
                # Create new employee
                new_employee = Employee(
                    employee_number=emp["EmployeeNumber"],
                    employee_name=emp["EmployeeName"],
                    job_code=emp["JobCode"],
                    reporting_employee_name=emp["ReportingEmployeeName"],
                    role_code=emp["RoleCode"],
                    department_code=department.department_code,
                    evaluation_status=False,
                    evaluation_by=None,
                    last_evaluated_date=None
                )
                db.add(new_employee)
                db.flush()
                
                if "Competencies" in emp:
                    for comp in emp["Competencies"]:
                        competency = db.query(Competency).filter_by(
                            code=comp["Code"]
                        ).first()
                        
                        if competency:
                            score = int(comp["Score"])
                            db.add(EmployeeCompetency(
                                employee_number=new_employee.employee_number,
                                competency_code=comp["Code"],
                                required_score=score,  
                                actual_score=0  
                            ))
                        else:
                            print(f"Competency {comp['Code']} not found for employee {emp['EmployeeNumber']}")
                
                db.commit()
                
                results.append({
                    "employee_number": emp["EmployeeNumber"],
                    "status": "success",
                    "message": "Employee created successfully"
                })
                
            except Exception as e:
                db.rollback()
                results.append({
                    "employee_number": emp.get("EmployeeNumber", "UNKNOWN"),
                    "status": "error",
                    "message": str(e)
                })
        
        return JSONResponse(content={
            "results": results,
            "total_processed": len(employee_data),
            "success_count": len([r for r in results if r["status"] == "success"]),
            "error_count": len([r for r in results if r["status"] == "error"])
        })
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {str(e)}"
        )
