from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import Department, Employee, User
from schemas import UserCreate, UserLogin, TokenData,RefreshTokenRequest
from database import get_db
from security import create_refresh_token, get_password_hash, verify_password, create_access_token
from datetime import timedelta
from jose import JWTError, jwt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/loginSwagger/")

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"




@router.post("/register/")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    emp  = db.query(Employee).filter(
    Employee.employee_number == user.username).first()
    if not emp:
        raise HTTPException(status_code=400, detail="employee doesnt exist registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    db_user1 = db.query(User).filter(User.username == user.username).first()
    if db_user1:
        raise HTTPException(status_code=400, detail="user already registered")
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    role = ""
    hashed_password = get_password_hash(user.password)
    if ("hr"==emp.role_code.lower()):
        role ="HR"
        
    elif ("hod"==emp.role_code.lower()):
        role ="HOD"
    else:
        role ="EMPLOYEE" 


    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role,
        department_code=emp.department_code
    ) 

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}



@router.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role, "department_code": db_user.department_code},
        expires_delta=timedelta(minutes=30)  
    )

    refresh_token = create_refresh_token(
        data={"sub": db_user.username}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": db_user.username,
        "role": db_user.role,
        "department_code": db_user.department_code
    }
from fastapi import Form

@router.post("/loginSwagger/")
def loginSwaggerUI(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.email == username).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role, "department_code": db_user.department_code},
        expires_delta=timedelta(minutes=30)
    )

    refresh_token = create_refresh_token(data={"sub": db_user.username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": db_user.username,
        "role": db_user.role,
        "department_code": db_user.department_code
    }



@router.post("/refresh_token")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Optional: Verify user still exists in DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new access token
    new_access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "department_code": user.department_code
        },expires_delta=timedelta(minutes=30) 
    )

    return {"access_token": new_access_token, "token_type": "bearer"}






def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        department_code: int = payload.get("department_code")

        if username is None or role is None or department_code is None:
            raise HTTPException(status_code=401, detail="Invalid token data")

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
       
        return {"username": username, "role": role, "department_code": department_code}

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )