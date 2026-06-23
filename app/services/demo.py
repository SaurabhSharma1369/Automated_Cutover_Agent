# dummy.py

import logging
from datetime import datetime, timedelta, timezone
from app.core.database import SessionLocal
from app.models.models import User, Task, TaskStatus, UserRole

# Adjust this import if your TaskQueryService is located somewhere else
from app.services.queries import TaskQueryService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def setup_data(db):
    """Creates a test user and two tasks (one overdue, one future)."""
    test_email = "query.tester@company.com"
    
    user = db.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(name="Query Tester", email=test_email, role=UserRole.EMPLOYEE)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1. Create an Overdue Task
    overdue_task = db.query(Task).filter(Task.title == "Overdue Test Task").first()
    if not overdue_task:
        overdue_task = Task(
            title="Overdue Test Task",
            status=TaskStatus.PENDING,
            assigned_to=user.id,
            deadline=datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=2) # 2 days ago
        )
        db.add(overdue_task)

    # 2. Create a Future Task
    future_task = db.query(Task).filter(Task.title == "Future Test Task").first()
    if not future_task:
        future_task = Task(
            title="Future Test Task",
            status=TaskStatus.PENDING,
            assigned_to=user.id,
            deadline=datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(days=5) # 5 days from now
        )
        db.add(future_task)

    db.commit()
    db.refresh(overdue_task)
    db.refresh(future_task)
    
    return user, overdue_task, future_task


def test_get_overdue_tasks(db):
    print("\n--- TEST 1: get_overdue_tasks ---")
    overdue_tasks = TaskQueryService.get_overdue_tasks(db)
    
    found = False
    for task in overdue_tasks:
        if task.title == "Overdue Test Task":
            found = True
            print(f"✅ SUCCESS: Caught overdue task ID {task.id} ('{task.title}')")
            
    if not found:
        print("❌ FAILED: Did not find the expected overdue task in the query results.")


def test_update_task_status(db, task_id):
    print("\n--- TEST 2: update_task_status ---")
    try:
        updated_task = TaskQueryService.update_task_status(
            task_id=task_id,
            new_status="BLOCKED",
            changed_by="Admin Dashboard",
            reason_summary="Manual override for testing.",
            db=db
        )
        print(f"✅ SUCCESS: Task {updated_task.id} status successfully changed to {updated_task.status.name}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")


def test_update_task_status_by_email(db, user_email, task_id):
    print("\n--- TEST 3: update_task_status_by_email_reply ---")
    
    # Simulating an email reply where the user explicitly mentions the task ID
    email_body = f"Task #{task_id} is completely done. We can close it out."
    
    try:
        updated_task = TaskQueryService.update_task_status_by_email_reply(
            sender_email=user_email,
            text_body=email_body,
            db=db
        )
        print(f"✅ SUCCESS: AI successfully parsed email and set Task {updated_task.id} to {updated_task.status.name}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")


if __name__ == "__main__":
    print("🚀 Initializing QueryService Tests...")
    db_session = SessionLocal()
    
    try:
        user, overdue_task, future_task = setup_data(db_session)
        
        # Test 1
        test_get_overdue_tasks(db_session)
        
        # Test 2
        test_update_task_status(db_session, future_task.id)
        
        # Test 3
        test_update_task_status_by_email(db_session, user.email, overdue_task.id)
        
    finally:
        # Import AuditLog at the top of dummy.py if you haven't already
        from app.models.models import AuditLog 
        
        # Manually delete the connected audit logs first
        db_session.query(AuditLog).filter(AuditLog.task_id.in_([overdue_task.id, future_task.id])).delete()
        
        # Now it is safe to delete the tasks
        db_session.delete(overdue_task)
        db_session.delete(future_task)
        db_session.commit()
        
        db_session.close()
        print("\n🏁 Tests complete. Cleaned up test data.")