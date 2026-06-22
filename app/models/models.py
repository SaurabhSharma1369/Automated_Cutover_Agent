import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    NOTIFIED = "NOTIFIED"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    NEEDS_INFO = "NEEDS_INFO"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"

class UserRole(str, enum.Enum):
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    
    # Self-referencing relationship for team escalation hierarchies
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    tasks = relationship("Task", back_populates="assigned_user")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 👈 Added to capture the secondary owner email string from Excel
    secondary_owner_email = Column(String(255), nullable=True)
    responsible_team = Column(String(255), nullable=True)
    planned_percentage = Column(Integer, nullable=True)
    actual_percentage = Column(Integer, nullable=True)
    variance = Column(Integer, nullable=True)
    reply_text = Column(Text, nullable=True)
    completion_percentage = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    delay_reason = Column(Text, nullable=True)
    recovery_plan = Column(Text, nullable=True)
    expected_completion = Column(DateTime, nullable=True)
    warning = Column(Text, nullable=True)

    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_user = relationship("User", back_populates="tasks")
    email_logs = relationship("EmailLog", back_populates="task")
    audit_logs = relationship("AuditLog", back_populates="task")

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # 👈 Changed to nullable=True so standalone general system alerts don't crash the logger
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True) 
    
    direction = Column(String(50), nullable=False)  # "INBOUND" or "OUTBOUND"
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    body_content = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="email_logs")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(String(100), default="SYSTEM")  # SYSTEM, AI, or MANUAL
    reason_summary = Column(Text, nullable=True)         # Captures LLM justification logs
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="audit_logs")