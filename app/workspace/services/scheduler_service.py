import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session

# <-- CHANGED: Back to BackgroundScheduler for FastAPI integration
from apscheduler.schedulers.background import BackgroundScheduler 

# =========================================================
# IMPORTS
# =========================================================
from app.core.database import SessionLocal
from app.models.models import Task, TaskStatus

from app.workspace.services.email_service import (
    send_daily_status_request,
    send_delay_email
)
from app.services.email import EmailService
from app.workspace.workflow.cutover_agent import graph 

# =========================================================
# LOGGING SETUP
# =========================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SchedulerApp")

# Initialize the Background Scheduler globally
scheduler = BackgroundScheduler()

# ==========================================
# 1. AGENT DISPATCHER
# ==========================================
class CutoverAgentService:
    @staticmethod
    def dispatch_email_to_agent(sender_email: str, subject: str, text_body: str, db: Session):
        task_id = CutoverAgentService._extract_task_id(subject)
        
        if not task_id:
            logger.warning(f"No Task ID found in subject: '{subject}'. Skipping.")
            return

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} extracted, but not found in database.")
            return
        
        # Calculate variance safely
        planned_raw = getattr(task, 'planned_percentage', 100)
        actual_raw = getattr(task, 'actual_percentage', 0)

        planned = 100 if planned_raw is None else planned_raw
        actual = 0 if actual_raw is None else actual_raw

        initial_state = {
            "task_id": task.id,
            "task_name": getattr(task, 'title', 'Unknown Task'),
            "assigned_to": sender_email,
            "secondary_owner": getattr(task, 'secondary_owner_email', ''),
            "responsible_team": getattr(task, 'responsible_team', ''),
            "planned_percentage": planned,
            "actual_percentage": actual,
            "variance": planned - actual,
            "reply_text": text_body.strip(),
            
            "status": "",
            "summary": "",
            "delay_reason": "",
            "recovery_plan": "",
            "expected_completion": "",
            "warning": ""
        }

        logger.info(f"==> Invoking Cutover Agent for Task {task.id}...")
        try:
            result = graph.invoke(initial_state) 
            logger.info(f"==> Agent successfully processed Task {task.id}.")
        except Exception as e:
            logger.error(f"==> Agent failed to process Task {task.id}: {str(e)}", exc_info=True)

    @staticmethod
    def _extract_task_id(subject: str) -> int | None:
        matches = re.findall(r"(?:task\s*#?|task\s*id\s*|\[task\s*)(\d+)", subject, flags=re.IGNORECASE)
        if matches:
            return int(matches[0])
        
        numeric = re.findall(r"\b(\d{1,6})\b", subject)
        if numeric:
            return int(numeric[0])
            
        return None

# ==========================================
# 2. SCHEDULER JOBS
# ==========================================
def outbound_email_job():
    logger.info("Starting OUTBOUND email job...")
    try:
        now = datetime.utcnow()
        with SessionLocal() as db:
            pending_tasks = db.query(Task).filter(
                Task.status.in_([TaskStatus.PENDING, TaskStatus.NOTIFIED])
            ).all()

            for task in pending_tasks:
                if task.deadline and task.deadline < now:
                    logger.info(f"Sending DELAY email for Task {task.id}")
                    send_delay_email(task)
                else:
                    logger.info(f"Sending DAILY STATUS request for Task {task.id}")
                    send_daily_status_request(task)
                    
        logger.info("Outbound job complete.")
    except Exception as e:
        logger.error("Outbound job failed", exc_info=True)

def inbound_listener_job():
    logger.info("Starting INBOUND listener job...")
    try:
        new_emails = EmailService.fetch_unread_emails()
        
        if not new_emails:
            logger.info("No new emails to process.")
            return
            
        with SessionLocal() as db:
            for msg in new_emails:
                logger.info(f"Processing reply from {msg['sender']} - Subject: '{msg['subject']}'")
                
                CutoverAgentService.dispatch_email_to_agent(
                    sender_email=msg["sender"],
                    subject=msg["subject"],
                    text_body=msg["text_body"],
                    db=db
                )
    except Exception as e:
        logger.error("Inbound listener job failed", exc_info=True)

# ==========================================
# 3. FASTAPI INTEGRATION FUNCTIONS
# ==========================================
def start_scheduler():
    """Called by FastAPI lifespan on startup to configure and start the background jobs."""
    if scheduler.running:
        logger.warning("Scheduler already running; skip start.")
        return

    # Runs the outbound sender every morning exactly at 9:00 AM
    scheduler.add_job(
        outbound_email_job, 
        trigger="cron", 
        hour=9,       
        minute=0,     
        id="outbound_job", 
        replace_existing=True
    )
    
    # Runs the inbound inbox checker every 30 seconds
    scheduler.add_job(
        inbound_listener_job, 
        trigger="interval", 
        seconds=30, 
        id="inbound_job", 
        replace_existing=True
    )

    scheduler.start()
    logger.info("🚀 Background Task Scheduler initialized successfully.")

def shutdown_scheduler():
    """Called by FastAPI lifespan on shutdown to gracefully stop the jobs."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("🛑 Background Task Scheduler shut down cleanly.")