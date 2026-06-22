import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog, Task, TaskStatus, User

logger = logging.getLogger("QueryService")

class TaskQueryService:
    @staticmethod
    def get_overdue_tasks(db: Session):
        """
        Returns Task records where the deadline is in the past and status is PENDING or NOTIFIED.
        """
        if db is None:
            raise ValueError("A SQLAlchemy Session is required.")

        try:
            now = datetime.utcnow()
            return (
                db.query(Task)
                .filter(
                    Task.deadline < now,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.NOTIFIED]),
                )
                .all()
            )
        except Exception:
            logger.exception("Failed to query overdue tasks.")
            raise

    @staticmethod
    def update_task_status(task_id: int, new_status: str, changed_by: str, reason_summary: str, db: Session):
        """
        Updates a Task status and writes a corresponding AuditLog record.
        """
        if db is None:
            raise ValueError("A SQLAlchemy Session is required.")

        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be a positive integer.")

        if not new_status or not new_status.strip():
            raise ValueError("new_status is required.")

        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Task with id={task_id} not found.")

            previous_status = task.status
            normalized_new_status = str(new_status).strip().upper()

            if normalized_new_status in TaskStatus.__members__:
                task.status = TaskStatus[normalized_new_status]
            else:
                task.status = TaskStatus(normalized_new_status)

            audit_entry = AuditLog(
                task_id=task.id,
                previous_status=previous_status.value if hasattr(previous_status, "value") else str(previous_status),
                new_status=task.status.value,
                changed_by=changed_by,
                reason_summary=reason_summary,
            )
            db.add(audit_entry)
            db.commit()
            return task
        except Exception:
            logger.exception("Failed to update task status for task_id=%s.", task_id)
            db.rollback()
            raise

    @staticmethod
    def update_task_status_by_email_reply(sender_email: str, text_body: str, db: Session):
        """
        Processes an inbound email to update the linked task status and record an AuditLog.
        """
        if db is None:
            raise ValueError("A SQLAlchemy Session is required.")

        sender_email_normalized = sender_email.strip().lower()
        if not sender_email_normalized:
            raise ValueError("sender_email is required.")

        if not text_body or not text_body.strip():
            raise ValueError("text_body is required.")

        try:
            user = db.query(User).filter(User.email == sender_email_normalized).first()
            if user is None:
                raise ValueError(f"No user found for sender email '{sender_email_normalized}'.")

            task_id = TaskQueryService._extract_task_id(text_body)
            task = None
            if task_id is not None:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task and task.assigned_to != user.id and task.secondary_owner_email != sender_email_normalized:
                    logger.warning(
                        "User %s attempted to update task %s but is not assigned or secondary owner.",
                        sender_email_normalized,
                        task_id,
                    )
                    task = None

            if task is None:
                task = (
                    db.query(Task)
                    .filter(
                        Task.assigned_to == user.id,
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.NOTIFIED, TaskStatus.BLOCKED, TaskStatus.NEEDS_INFO]),
                    )
                    .order_by(Task.deadline.asc())
                    .first()
                )

            if task is None:
                raise ValueError("Unable to identify a task for this inbound status update.")

            desired_status = TaskQueryService._extract_status(text_body)
            if desired_status is None:
                raise ValueError("No valid task status was found in the inbound message.")

            previous_status = task.status
            task.status = desired_status

            audit_entry = AuditLog(
                task_id=task.id,
                previous_status=previous_status.value if hasattr(previous_status, "value") else str(previous_status),
                new_status=desired_status.value,
                changed_by="AI",
                reason_summary=TaskQueryService._build_reason_summary(text_body),
            )
            db.add(audit_entry)
            db.commit()

            return task
        except Exception:
            logger.exception("Failed to process inbound email status update.")
            db.rollback()
            raise

    @staticmethod
    def _extract_task_id(text: str) -> Optional[int]:
        matches = re.findall(r"(?:task\s*#?|task\s*id\s*)(\d+)", text, flags=re.IGNORECASE)
        if matches:
            return int(matches[0])

        numeric_matches = re.findall(r"\b(\d{2,6})\b", text)
        if numeric_matches:
            return int(numeric_matches[0])

        return None

    @staticmethod
    def _extract_status(text: str) -> Optional[TaskStatus]:
        normalized_text = text.lower()
        status_map = {
            "done": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
            "complete": TaskStatus.DONE,
            "blocked": TaskStatus.BLOCKED,
            "need info": TaskStatus.NEEDS_INFO,
            "needs info": TaskStatus.NEEDS_INFO,
            "awaiting info": TaskStatus.NEEDS_INFO,
            "overdue": TaskStatus.OVERDUE,
            "escalated": TaskStatus.ESCALATED,
            "pending": TaskStatus.PENDING,
            "notified": TaskStatus.NOTIFIED,
            "at risk": TaskStatus.BLOCKED,
            "delayed": TaskStatus.OVERDUE,
        }

        for token, status in status_map.items():
            if token in normalized_text:
                return status

        return None

    @staticmethod
    def _build_reason_summary(text_body: str) -> str:
        cleaned = re.sub(r"\s+", " ", text_body.strip())
        return f"Inbound reply processed by AI. Message excerpt: {cleaned[:500]}"
