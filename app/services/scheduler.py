import logging
from datetime import datetime
from typing import Set

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import EmailLog, Task, TaskStatus, AuditLog, User
from app.services.email import EmailService
from app.services.queries import TaskQueryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CutoverScheduler")

scheduler = BackgroundScheduler()
_processed_inbound_email_ids: Set[int] = set()

def check_and_escalate_deadlines():
    logger.info("⏰ Running background deadline sweep...")
    with SessionLocal() as db:
        try:
            overdue_tasks = TaskQueryService.get_overdue_tasks(db=db)

            for task in overdue_tasks:
                assigned_user = db.query(User).filter(User.id == task.assigned_to).first()
                if not assigned_user:
                    logger.warning("Skipping overdue task %s: assigned user not found.", task.id)
                    continue

                cc_list = []
                if task.secondary_owner_email:
                    cc_list.append(task.secondary_owner_email)

                subject = f"[Cutover Alert] Overdue Task: {task.title}"
                body = (
                    f"Task '{task.title}' is overdue as of {task.deadline.isoformat()} UTC.\n"
                    f"Current status: {task.status.value}.\n"
                    f"Assigned to: {assigned_user.name} <{assigned_user.email}>\n"
                    f"Secondary owner: {task.secondary_owner_email or 'none'}\n"
                    "Please update the task status or confirm recovery actions immediately."
                )

                try:
                    EmailService.send_email(
                        recipient_email=assigned_user.email,
                        subject=subject,
                        body=body,
                        cc_emails=cc_list,
                        db=db,
                    )
                except Exception as err:
                    logger.error("Failed to send escalation email for task %s: %s", task.id, err)

                previous_status = task.status
                if previous_status != TaskStatus.NOTIFIED:
                    task.status = TaskStatus.NOTIFIED

                audit_entry = AuditLog(
                    task_id=task.id,
                    previous_status=previous_status.value if hasattr(previous_status, "value") else str(previous_status),
                    new_status=task.status.value,
                    changed_by="SYSTEM_SCHEDULER",
                    reason_summary="Automated overdue notification sent and status set to NOTIFIED.",
                )
                db.add(audit_entry)

            db.commit()
        except Exception:
            logger.exception("Failed while executing deadline escalation job.")
            db.rollback()


def poll_inbound_email_replies():
    logger.info("📬 Polling inbound email messages...")
    with SessionLocal() as db:
        try:
            inbox = (
                db.query(EmailLog)
                .filter(EmailLog.direction == "INBOUND")
                .order_by(EmailLog.timestamp.asc())
                .all()
            )

            for message in inbox:
                if message.id in _processed_inbound_email_ids:
                    continue

                logger.info(
                    "Inbound email received id=%s sender=%s subject=%s",
                    message.id,
                    message.sender,
                    message.subject,
                )
                _processed_inbound_email_ids.add(message.id)
        except Exception:
            logger.exception("Failed while polling inbound emails.")


def start_scheduler():
    if scheduler.running:
        logger.warning("Scheduler already running; skip start.")
        return

    scheduler.add_job(check_and_escalate_deadlines, 'interval', seconds=60, id='deadline_escalation')
    scheduler.add_job(poll_inbound_email_replies, 'interval', seconds=30, id='inbound_email_polling')
    scheduler.start()
    logger.info("🚀 Background Task Scheduler initialized successfully.")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("🛑 Background Task Scheduler shut down cleanly.")