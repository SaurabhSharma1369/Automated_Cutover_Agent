from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Task, User, TaskStatus, AuditLog

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# --- DATA VALIDATION SCHEMAS ---
class TaskImportSchema(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to_email: str
    deadline: datetime

class TaskResponseSchema(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    assigned_to: int
    deadline: datetime

    class Config:
        from_attributes = True

class TaskStatusUpdateSchema(BaseModel):
    status: TaskStatus
    changed_by: str = "MANUAL"
    reason: Optional[str] = None

# --- API ENDPOINTS ---

@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_cutover_tasks(tasks: List[TaskImportSchema], db: Session = Depends(get_db)):
    imported_count = 0
    for task_data in tasks:
        # Check if user exists by looking up their email signature
        user = db.query(User).filter(User.email == task_data.assigned_to_email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {task_data.assigned_to_email} does not exist."
            )
        
        db_task = Task(
            title=task_data.title,
            description=task_data.description,
            assigned_to=user.id,
            deadline=task_data.deadline,
            status=TaskStatus.PENDING
        )
        db.add(db_task)
        imported_count += 1
        
    db.commit()
    return {"message": f"Successfully imported {imported_count} cutover tasks."}

@router.get("/", response_model=List[TaskResponseSchema])
def get_all_tasks(status_filter: Optional[TaskStatus] = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    return query.all()

@router.patch("/{task_id}", response_model=TaskResponseSchema)
def update_task_status(task_id: int, payload: TaskStatusUpdateSchema, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    old_status = task.status
    task.status = payload.status
    
    # Audit trail creation
    audit_entry = AuditLog(
        task_id=task.id,
        previous_status=old_status,
        new_status=payload.status,
        changed_by=payload.changed_by,
        reason_summary=payload.reason
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(task)
    
    return task