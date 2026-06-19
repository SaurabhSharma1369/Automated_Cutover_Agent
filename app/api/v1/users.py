from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.models import User, UserRole

router = APIRouter(prefix="/users", tags=["Users"])

# --- DATA VALIDATION SCHEMAS ---
class UserCreateSchema(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.EMPLOYEE
    manager_id: Optional[int] = None

class UserResponseSchema(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    manager_id: Optional[int]

    class Config:
        from_attributes = True

# --- API ENDPOINTS ---

@router.post("/", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateSchema, db: Session = Depends(get_db)):
    """
    Create a new user (Manager or Employee) in the system.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # If a manager_id is provided, verify that the manager actually exists
    if payload.manager_id:
        manager = db.query(User).filter(User.id == payload.manager_id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manager with ID {payload.manager_id} not found."
            )

    db_user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        manager_id=payload.manager_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserResponseSchema])
def get_all_users(db: Session = Depends(get_db)):
    """
    Retrieve all registered users.
    """
    return db.query(User).all()