from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.workspace.services.email_service import (
    send_delay_email,
    send_daily_status_request
)

# from database import get_tasks_from_db
# Replace with your actual import


app = FastAPI()

scheduler = BackgroundScheduler()


def get_tasks_from_db():
    return [
         {

        "task_name": "Database Migration",

        "assigned_to":
            "jitendra@company.com",

        "secondary_owner":
            "backup.owner@company.com",

        "responsible_team":
            "database-team@company.com",

        "planned_percentage":
            100,

        "actual_percentage":
            75,

        "end_date":
            "2026-06-25",

        "delay_reason":
            "Waiting for firewall approval",

        "recovery":
            "Dedicated security review call",

        "description":
            "Production database migration",
        
        "status": "IN_PROGRESS"
    }
,
         {

        "task_name": "AI Migration",

        "assigned_to":
            "saurabh@company.com",

        "secondary_owner":
            "backup.owner@company.com",

        "responsible_team":
            "database-team@company.com",

        "planned_percentage":
            100,

        "actual_percentage":
            75,

        "end_date":
            "2026-06-25",

        "delay_reason":
            "Waiting for firewall approval",

        "recovery":
            "Dedicated security review call",

        "description":
            "Production database migration",

        "status": "IN_PROGRESS"
    }
    ]

def daily_scheduler_job():
    print(f"\nScheduler started at {datetime.now()}")

    try:
        tasks = get_tasks_from_db()

        today = datetime.now().date()

        for task in tasks:

            print(f"Processing: {task['task_name']}")

            if task["status"] == "COMPLETED":
                continue

            end_date = datetime.strptime(
                task["end_date"],
                "%Y-%m-%d"
            ).date()

            if today > end_date:
                print("Sending delay email")
                send_delay_email(task)

            else:
                print("Sending status request")
                send_daily_status_request(task)

        print("Scheduler completed successfully")

    except Exception as e:
        print(f"Scheduler Error: {e}")


@app.on_event("startup")
async def startup_event():

    # # TESTING: runs every 30 seconds
    # scheduler.add_job(
    #     daily_scheduler_job,
    #     trigger="interval",
    #     seconds=30,
    #     id="daily_status_job",
    #     replace_existing=True
    # )

    # PRODUCTION: runs every day at 9 AM
    scheduler.add_job(
        daily_scheduler_job,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_status_job",
        replace_existing=True
    )

    scheduler.start()

    print("Scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("Scheduler stopped")


@app.get("/")
def home():
    return {"message": "FastAPI Scheduler Running"}