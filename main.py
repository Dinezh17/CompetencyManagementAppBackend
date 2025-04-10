from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import auth
import competency
from database import engine, Base
import department
from sqlalchemy.orm import Session
import stats
import roleassign
import employeeSetEvaluation
import employee
import role
import employeeCompetencyAssign
import competecnyScore,employeeExcel


app = FastAPI()
origins = [
    "http://localhost:5173",  # React app running on Vite
    "http://127.0.0.1:5173",  # Alternative localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows frontend domain
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Create tables
Base.metadata.create_all(bind=engine)

# Include authentication routes
app.include_router(auth.router)
app.include_router(role.router)
app.include_router(department.router)
app.include_router(competency.router)
app.include_router(employee.router)
app.include_router(stats.router)
app.include_router(roleassign.router)
app.include_router(employeeCompetencyAssign.router)


app.include_router(employeeSetEvaluation.router)
app.include_router(competecnyScore.router)
app.include_router(employeeExcel.router)







    