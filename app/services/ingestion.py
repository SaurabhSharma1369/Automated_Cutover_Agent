import logging
import re
from datetime import datetime, time, timezone
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import Task, User, TaskStatus, UserRole
from app.workspace.services.email_service import send_assignment_email

logger = logging.getLogger("IngestionService")

class IngestionService:
    @staticmethod
    def import_tasks_from_excel(file_path: str, db: Session):
        """
        Reads the master cutover Excel spreadsheet and creates Task records.
        The spreadsheet is the source of truth for task details and progress.
        """
        if db is None:
            raise ValueError("A SQLAlchemy Session is required.")

        try:
            df = pd.read_excel(file_path)
            df.columns = [str(col).strip() for col in df.columns]
            imported_count = 0

            for index, row in df.iterrows():
                # ADDED: "Task Name"
                title = IngestionService._get_str(row, ["Task Name", "task_name", "Task", "Name"])
                cancel_flag = IngestionService._get_str(row, ["Cancel Flag", "cancel_flag", "Canceled"])
                if not title or str(cancel_flag).strip().lower() in {"true", "yes", "1", "y"}:
                    continue

                # ADDED: "Assigned To"
                assigned_email = IngestionService._get_str(row, ["Assigned To", "assigned_to", "Owner Email", "Owner"])
                if not assigned_email or "@" not in assigned_email:
                    logger.warning("Skipping row %s: invalid or missing Assigned To.", index)
                    continue

                assigned_email = assigned_email.lower()
                user = db.query(User).filter(User.email == assigned_email).first()
                if not user:
                    user = User(
                        name=IngestionService._default_name_from_email(assigned_email),
                        email=assigned_email,
                        role=UserRole.EMPLOYEE,
                    )
                    db.add(user)
                    db.flush()

                # ADDED: Specific Excel Column Names to all keys
                secondary_owner_email = IngestionService._get_str(row, ["Secondary Owner", "secondary_owner", "Backup"])
                responsible_team = IngestionService._get_str(row, ["Responsible Team", "responsible_team", "Team"])
                
                planned_percentage = IngestionService._parse_int(row, ["Planned % Complete", "Planned Percentage", "planned_percentage"])
                actual_percentage = IngestionService._parse_int(row, ["Actual % Complete", "Actual Percentage", "actual_percentage"])
                variance = IngestionService._parse_int(row, ["Variance", "variance", "Gap"])
                completion_percentage = IngestionService._parse_int(row, ["Completion Percentage", "completion_percentage"])

                if variance is None and planned_percentage is not None and actual_percentage is not None:
                    variance = planned_percentage - actual_percentage

                reply_text = IngestionService._get_str(row, ["Reply Text", "reply_text"])
                summary = IngestionService._get_str(row, ["Summary", "summary"])
                delay_reason = IngestionService._get_str(row, ["Delay Reason", "delay_reason"])
                recovery_plan = IngestionService._get_str(row, ["Recovery", "Recovery Plan", "recovery_plan"])
                warning_text = IngestionService._get_str(row, ["At Risk", "Warning", "warning"])
                description = IngestionService._get_str(row, ["Description", "description"])

                expected_completion = IngestionService._parse_datetime(row, ["End Date", "Expected Completion", "expected_completion", "Deadline"])
                deadline = expected_completion or datetime.utcnow().replace(tzinfo=timezone.utc)

                status = IngestionService._normalize_status(
                    IngestionService._get_str(row, ["Status", "status"])
                )

                task = Task(
                    title=title,
                    description=description,
                    status=status,
                    assigned_to=user.id,
                    assigned_user=user, # 👈 FIX 1: Explicitly pass the SQLAlchemy relationship 
                    secondary_owner_email=secondary_owner_email,
                    responsible_team=responsible_team,
                    planned_percentage=planned_percentage,
                    actual_percentage=actual_percentage,
                    variance=variance,
                    reply_text=reply_text,
                    completion_percentage=completion_percentage,
                    summary=summary,
                    delay_reason=delay_reason,
                    recovery_plan=recovery_plan,
                    expected_completion=expected_completion,
                    warning=warning_text,
                    deadline=deadline,
                )
                db.add(task)
                
                # 👈 FIX 2: Flush to the database immediately to generate the Task ID
                db.flush() 
                
                # The email service will now correctly see task.id and task.assigned_user.email
                send_assignment_email(task) 
                
                imported_count += 1

            db.commit()
            return {"imported": imported_count}

        except Exception:
            logger.exception("Failed to import tasks from Excel.")
            db.rollback()
            raise

    @staticmethod
    def _get_str(row, keys):
        for key in keys:
            if key in row and pd.notna(row[key]):
                return str(row[key]).strip()
        return None

    @staticmethod
    def _parse_int(row, keys):
        value = IngestionService._get_str(row, keys)
        if value is None:
            return None
        try:
            # Safely strip percentage signs (e.g., "85%" -> "85")
            if isinstance(value, str):
                value = value.replace("%", "").strip()
            
            return int(float(value))
        except (ValueError, TypeError):
            logger.warning("Unable to parse integer value '%s' for keys %s.", value, keys)
            return None

    @staticmethod
    def _parse_datetime(row, keys) -> Optional[datetime]:
        for key in keys:
            if key in row and pd.notna(row[key]):
                parsed = pd.to_datetime(row[key], errors="coerce")
                if pd.notna(parsed):
                    return parsed.to_pydatetime()
        return None

    @staticmethod
    def _normalize_status(status_value: Optional[str]) -> TaskStatus:
        if not status_value:
            return TaskStatus.PENDING
        normalized = str(status_value).strip().upper()
        if normalized in TaskStatus.__members__:
            return TaskStatus[normalized]
        return TaskStatus.PENDING

    @staticmethod
    def _default_name_from_email(email_address: str) -> str:
        prefix = email_address.split("@", 1)[0].strip()
        default_name = re.sub(r"[._]+", " ", prefix).title()
        return default_name or email_address