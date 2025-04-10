from sqlalchemy import Boolean, Column, Date, Integer, String, ForeignKey
from database import Base






class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # HR or HOD
    department_code = Column(Integer, ForeignKey("departments.department_code"))



    
class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    department_code=Column(String ,unique=True,index=True)
    name = Column(String, unique=True, index=True)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String, unique=True, index=True)
    name = Column(String, unique=True, index=True)

class Competency(Base):
    __tablename__ = "competencies"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    description = Column(String)
    required_score = Column(Integer)
    


class RoleCompetency(Base):
    __tablename__ = "role_competencies"
    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String, ForeignKey("roles.role_code"))
    competency_code = Column(String, ForeignKey("competencies.code"))
    required_score = Column(Integer)


class Employee(Base):
    __tablename__ = "employees"
    employee_number = Column(String, primary_key=True, index=True)
    employee_name = Column(String)
    job_code = Column(String)
    reporting_employee_name = Column(String)
    role_code = Column(String, ForeignKey("roles.role_code"))
    department_code = Column(String, ForeignKey("departments.department_code"))
    evaluation_status = Column(Boolean, default=False)
    evaluation_by = Column(String, nullable=True)  # Explicitly nullable
    last_evaluated_date = Column(Date, nullable=True)  # Explicitly nullable



class EmployeeCompetency(Base):
    __tablename__ = "employee_competencies"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True,)
    employee_number = Column(String, ForeignKey("employees.employee_number"))
    competency_code = Column(String, ForeignKey("competencies.code"))
    required_score = Column(Integer)
    actual_score = Column(Integer,default=0)









