from fastapi import Depends
from sqlalchemy.orm import Session
from models import User
from database import SessionLocal, get_db
from auth import get_password_hash  # your bcrypt password hash function


db: Session = SessionLocal()

admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    new_admin = User(
        username="admin",
        email = "admin@123.com",
        hashed_password=get_password_hash("admin@123.com"),
        role="ADMIN",
        department_code = "admin"

    )
    db.add(new_admin)
    db.commit()
    print("Admin user created.")
else:
    print("Admin already exists.")
