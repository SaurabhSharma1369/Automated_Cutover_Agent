# =====================================================
# IMPORTS
# =====================================================

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.email import EmailService
# Uncomment when using Outlook
# import win32com.client


# =====================================================
# EMAIL SCHEMA
# =====================================================

class EmailOutput(BaseModel):
    subject: str
    body: str


# =====================================================
# LLM
# =====================================================

# Initialize the base model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)

# Bind the Pydantic schema directly to the model
# Gemini will natively return an instance of EmailOutput
structured_llm = llm.with_structured_output(EmailOutput)


# =====================================================
# GENERIC EMAIL SENDER
# =====================================================

def send_email(
    to_email,
    subject,
    body,
    cc=None
):
    # Optional: Open database session if you want to test EmailLog tracking
    db = SessionLocal()
    
    try:
        EmailService.send_email(
            recipient_email=to_email,
            subject=subject,
            body=body,
            cc_emails=cc if cc else ["secondary_owner@gmail.com"],
            db=db
        )
        print("✅ Email sent successfully! Check your inbox (and spam folder).")
    except Exception as e:
        print(f"❌ Email dispatch failed: {str(e)}")
    finally:
        db.close()


# =====================================================
# EMAIL GENERATOR USING LLM
# =====================================================

def generate_email(prompt_text) -> EmailOutput:
    prompt = f"""
You are an Enterprise Cutover Management Assistant.

Generate a professional corporate email.

Rules:
- Do NOT mention any employee name.
- Do NOT personalize the email.
- Start the email with exactly:
  Hello,

- Use professional enterprise language.
- Keep the content concise and action-oriented.
- Never use employee names even if they appear in the task details.
- Never sign with a person's name.
- Include a bolded note at the bottom (just before the signature) saying: "**IMPORTANT: When replying, please keep the exact subject line intact. The [Task #ID] tag is required to automatically log your update.**"
- Signature must always be:

Regards,
Cutover Agent

{prompt_text}
"""

    # structured_llm automatically parses the JSON and returns the Pydantic object
    response = structured_llm.invoke(prompt)

    return response

# =====================================================
# INITIAL TASK ASSIGNMENT EMAIL
# =====================================================

def send_assignment_email(task):
    # 👈 FIX: Navigate through the relationship to get the string email
    recipient_email = task.assigned_user.email if getattr(task, 'assigned_user', None) else None
    
    if not recipient_email:
        print(f"⚠️ Skipping assignment email: No assigned user email for Task {getattr(task, 'id', 'Unknown')}")
        return

    email = generate_email(
        f"""
Create a professional task assignment email.

Task Name:
{task.title}

Assigned To:
{recipient_email}

Planned Completion:
{task.planned_percentage}%

End Date:
{task.deadline}

Description:
{getattr(task, 'description', '')}

Inform the user:

- Task ownership is assigned
- Daily updates are required
- Delays must be reported immediately
"""
    )

    send_email(
        to_email=recipient_email,
        cc=getattr(task, 'secondary_owner_email', None),
        subject=f"{email.subject} [Task #{task.id}]",
        body=email.body
    )


# =====================================================
# DAILY STATUS REQUEST
# =====================================================

def send_daily_status_request(task):
    # 👈 FIX: Navigate through the relationship to get the string email
    recipient_email = task.assigned_user.email if getattr(task, 'assigned_user', None) else None
    
    if not recipient_email:
        print(f"⚠️ Skipping status request email: No assigned user email for Task {getattr(task, 'id', 'Unknown')}")
        return

    email = generate_email(
        f"""
Create a professional daily cutover status request email.

Task Name:
{task.title}

Planned Completion:
{task.planned_percentage}%

Current Completion:
{getattr(task, 'actual_percentage', 0)}%

End Date:
{task.deadline}

Ask the employee to provide:

1. Completion Percentage
2. Current Status
3. Delay Reason
4. Recovery Plan
5. Expected Completion Date

Keep the email concise.
"""
    )

    send_email(
        to_email=recipient_email,
        cc=getattr(task, 'secondary_owner_email', None),
        subject=f"{email.subject} [Task #{task.id}]",
        body=email.body
    )


# =====================================================
# DELAY JUSTIFICATION EMAIL
# =====================================================

def send_delay_email(task):
    # 👈 FIX: Navigate through the relationship to get the string email
    recipient_email = task.assigned_user.email if getattr(task, 'assigned_user', None) else None
    
    if not recipient_email:
        print(f"⚠️ Skipping delay email: No assigned user email for Task {getattr(task, 'id', 'Unknown')}")
        return

    email = generate_email(
        f"""
Create a professional delay justification email.

Task Name:
{task.title}

Planned End Date:
{task.deadline}

Current Completion:
{getattr(task, 'actual_percentage', 0)}%

The planned completion date has already passed.

Ask employee to provide:

1. Delay Reason
2. Current Blockers
3. Recovery Plan
4. Revised Completion Date
5. Impact To Dependent Tasks

Tone:
Professional and action-oriented.
"""
    )

    send_email(
        to_email=recipient_email,
        cc=getattr(task, 'secondary_owner_email', None),
        subject=f"{email.subject} [Task #{task.id}]",
        body=email.body
    )


# =====================================================
# AT RISK EMAIL
# =====================================================

def send_at_risk_email(task):
    # 👈 FIX: Navigate through the relationship to get the string email
    recipient_email = task.assigned_user.email if getattr(task, 'assigned_user', None) else None
    
    if not recipient_email:
        print(f"⚠️ Skipping AT_RISK email: No assigned user email for Task {getattr(task, 'id', 'Unknown')}")
        return

    email = generate_email(
        f"""
Create a professional follow-up email.

Task Name:
{task.title}

Status:
AT_RISK

Current Completion:
{getattr(task, 'actual_percentage', 0)}%

Delay Reason:
{getattr(task, 'delay_reason', 'None provided')}

Ask employee for:

1. Updated ETA
2. Recovery Actions
3. Remaining Risks
4. Escalation Support Needed
"""
    )

    send_email(
        to_email=recipient_email,
        cc=getattr(task, 'secondary_owner_email', None),
        subject=f"{email.subject} [Task #{task.id}]",
        body=email.body
    )


# =====================================================
# ESCALATION EMAIL
# =====================================================

def send_escalation_email(task):
    recipient_email = getattr(task, 'responsible_team', None)
    if not recipient_email:
        print(f"⚠️ Skipping escalation email: No responsible_team email for Task {getattr(task, 'id', 'Unknown')}")
        return

    email = generate_email(
        f"""
Create a professional escalation email.

Task:
{task.title}

Current Completion:
{getattr(task, 'actual_percentage', 0)}%

Status:
DELAYED

Delay Reason:
{getattr(task, 'delay_reason', 'None provided')}

Recovery Plan:
{getattr(task, 'recovery_plan', 'None provided')}

Request assistance from the responsible team.

Provide executive-level summary.

Keep email concise.
"""
    )

    send_email(
        to_email=recipient_email,
        cc=getattr(task, 'secondary_owner_email', None),
        subject=f"{email.subject} [Task #{task.id}]",
        body=email.body
    )

# =====================================================
# TESTING
# =====================================================

if __name__ == "__main__":
    # To test locally, we simulate the SQLAlchemy Object structure using a simple class
    class MockUser:
        def __init__(self, email):
            self.email = email

    class MockTask:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    task = MockTask(
        id=42,
        title="Database Migration",
        assigned_to=1,
        # 👈 FIX: Mocking the relationship so the test doesn't fail
        assigned_user=MockUser(email="saurabhsh.ug23.cs@nitp.ac.in"), 
        secondary_owner_email="backup.owner@company.com",
        responsible_team="database-team@company.com",
        planned_percentage=100,
        actual_percentage=75,
        deadline="2026-06-25",
        delay_reason="Waiting for firewall approval",
        recovery_plan="Dedicated security review call",
        description="Production database migration"
    )
    
    # Testing the updated method
    send_assignment_email(task)