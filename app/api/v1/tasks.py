import shutil
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

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