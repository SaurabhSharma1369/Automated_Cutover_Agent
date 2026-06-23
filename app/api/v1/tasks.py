import shutil
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.services.ingestion import IngestionService
from app.models.models import Task  # <-- Added missing Task model import

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# =====================================================
# PYDANTIC SCHEMAS
# =====================================================

class TaskResponse(BaseModel):
    """
    Pydantic schema to safely serialize the SQLAlchemy Task object into JSON.
    """
    id: int
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: Optional[int] = None
    secondary_owner_email: Optional[str] = None
    responsible_team: Optional[str] = None
    planned_percentage: Optional[int] = None
    actual_percentage: Optional[int] = None
    variance: Optional[int] = None
    reply_text: Optional[str] = None
    completion_percentage: Optional[int] = None
    summary: Optional[str] = None
    delay_reason: Optional[str] = None
    recovery_plan: Optional[str] = None
    expected_completion: Optional[datetime] = None
    warning: Optional[str] = None
    deadline: Optional[datetime] = None

    # This tells Pydantic to read data automatically from the SQLAlchemy ORM object
    model_config = ConfigDict(from_attributes=True)


# =====================================================
# ROUTES
# =====================================================

@router.post("/upload-schedule/", status_code=status.HTTP_201_CREATED)
def upload_cutover_schedule(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload an Excel schedule file. Saves it locally and triggers the 
    PostgreSQL Ingestion Engine automatically.
    """
    # 1. Validate file extension
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a valid Excel spreadsheet (.xlsx)"
        )
    
    # 2. Define standard target save location
    target_path = "cutover_master.xlsx"
    
    try:
        # 3. Save the incoming uploaded file stream directly to disk
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 4. Trigger your ingestion engine automatically using the current DB session
        result = IngestionService.import_tasks_from_excel(file_path=target_path, db=db)
        
        return {
            "message": "Excel schedule uploaded and parsed automatically!",
            "tasks_imported": result["imported"]
        }
        
    except Exception as e:
        # Clean up file copy if ingestion completely failed
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automated processing failed: {str(e)}"
        )


# Bind the response_model here so FastAPI knows how to convert the ORM objects to JSON
@router.get("/", response_model=List[TaskResponse], status_code=status.HTTP_200_OK)
def get_tasks(db: Session = Depends(get_db)):
    """
    Retrieve all tasks from the database.
    """
    try:
        # FastAPI will take this list of ORM objects and run them through TaskResponse
        return db.query(Task).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tasks: {str(e)}"
        )