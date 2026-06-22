from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import EmailLog

router = APIRouter(prefix="/emails", tags=["Email Simulator"])

class InboundEmailSimulationSchema(BaseModel):
    sender_email: EmailStr
    recipient_email: EmailStr
    subject: str
    body_content: str


class EmailLogSchema(BaseModel):
    id: int
    task_id: Optional[int]
    direction: str
    sender: str
    recipient: str
    subject: Optional[str]
    body_content: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


@router.post("/simulate-inbound", status_code=status.HTTP_201_CREATED)
def simulate_inbound_email(payload: InboundEmailSimulationSchema, db: Session = Depends(get_db)):
    """Insert a simulated inbound email message and preserve raw email content."""
    email_entry = EmailLog(
        task_id=None,
        direction="INBOUND",
        sender=payload.sender_email,
        recipient=payload.recipient_email,
        subject=payload.subject,
        body_content=payload.body_content,
    )
    db.add(email_entry)
    db.commit()
    db.refresh(email_entry)
    return {"message": "Inbound email simulated successfully.", "email_id": email_entry.id}


@router.get("/inbound", response_model=List[EmailLogSchema])
def list_inbound_emails(db: Session = Depends(get_db)):
    """Return raw inbound emails for AI consumption."""
    return (
        db.query(EmailLog)
        .filter(EmailLog.direction == "INBOUND")
        .order_by(EmailLog.timestamp.desc())
        .all()
    )

