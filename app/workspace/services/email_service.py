# services/email_service.py

# =====================================================
# IMPORTS
# =====================================================

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import settings
# Uncomment when using Outlook
# import win32com.client


# =====================================================
# LLM
# =====================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)


# =====================================================
# EMAIL SCHEMA
# =====================================================

class EmailOutput(BaseModel):

    subject: str

    body: str


email_parser = PydanticOutputParser(
    pydantic_object=EmailOutput
)


# =====================================================
# GENERIC EMAIL SENDER
# =====================================================

def send_email(
    to_email,
    subject,
    body,
    cc=None
):

    try:

        print("\n===================================")
        print("EMAIL SENT")
        print("===================================")
        print("TO :", to_email)

        if cc:
            print("CC :", cc)

        print("SUBJECT :", subject)
        print("BODY :")
        print(body)
        print("===================================\n")

        # Uncomment for Outlook

        # outlook = win32com.client.Dispatch(
        #     "Outlook.Application"
        # )

        # mail = outlook.CreateItem(0)

        # mail.To = to_email

        # if cc:
        #     mail.CC = cc

        # mail.Subject = subject
        # mail.Body = body

        # mail.Send()

    except Exception as e:

        print("ERROR SENDING EMAIL")
        print(e)


# =====================================================
# EMAIL GENERATOR USING LLM
# =====================================================

def generate_email(prompt_text):

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
- End the email exactly with:
- Never use employee names even if they appear in the task details.
- Never sign with a person's name.
- Signature must always be:

Regards,
Cutover Agent

Return ONLY valid JSON.

{prompt_text}

{email_parser.get_format_instructions()}
"""

    response = llm.invoke(prompt)

    return email_parser.parse(
        response.content
    )

# =====================================================
# INITIAL TASK ASSIGNMENT EMAIL
# =====================================================

def send_assignment_email(task):

    email = generate_email(
        f"""
Create a professional task assignment email.

Task Name:
{task['task_name']}

Assigned To:
{task['assigned_to']}

Planned Completion:
{task['planned_percentage']}%

End Date:
{task['end_date']}

Description:
{task.get('description', '')}

Inform the user:

- Task ownership is assigned
- Daily updates are required
- Delays must be reported immediately
"""
    )

    send_email(
        to_email=task["assigned_to"],
        cc=task["secondary_owner"],
        subject=email.subject,
        body=email.body
    )


# =====================================================
# DAILY STATUS REQUEST
# =====================================================

def send_daily_status_request(task):

    email = generate_email(
        f"""
Create a professional daily cutover status request email.

Task Name:
{task['task_name']}

Planned Completion:
{task['planned_percentage']}%

Current Completion:
{task['actual_percentage']}%

End Date:
{task['end_date']}

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
        to_email=task["assigned_to"],
        cc=task["secondary_owner"],
        subject=email.subject,
        body=email.body
    )


# =====================================================
# DELAY JUSTIFICATION EMAIL
# =====================================================

def send_delay_email(task):

    email = generate_email(
        f"""
Create a professional delay justification email.

Task Name:
{task['task_name']}

Planned End Date:
{task['end_date']}

Current Completion:
{task['actual_percentage']}%

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
        to_email=task["assigned_to"],
        cc=task["secondary_owner"],
        subject=email.subject,
        body=email.body
    )


# =====================================================
# AT RISK EMAIL
# =====================================================

def send_at_risk_email(task):

    email = generate_email(
        f"""
Create a professional follow-up email.

Task Name:
{task['task_name']}

Status:
AT_RISK

Current Completion:
{task['actual_percentage']}%

Delay Reason:
{task.get('delay_reason', '')}

Ask employee for:

1. Updated ETA
2. Recovery Actions
3. Remaining Risks
4. Escalation Support Needed
"""
    )

    send_email(
        to_email=task["assigned_to"],
        cc=task["secondary_owner"],
        subject=email.subject,
        body=email.body
    )


# =====================================================
# ESCALATION EMAIL
# =====================================================

def send_escalation_email(task):

    email = generate_email(
        f"""
Create a professional escalation email.

Task:
{task['task_name']}

Current Completion:
{task['actual_percentage']}%

Status:
DELAYED

Delay Reason:
{task.get('delay_reason', '')}

Recovery Plan:
{task.get('recovery', '')}

Request assistance from the responsible team.

Provide executive-level summary.

Keep email concise.
"""
    )

    send_email(
        to_email=task["responsible_team"],
        cc=task["secondary_owner"],
        subject=email.subject,
        body=email.body
    )


# =====================================================
# TESTING
# =====================================================

if __name__ == "__main__":

    task = {

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
            "Production database migration"
    }

    send_assignment_email(task)

    send_daily_status_request(task)

    send_delay_email(task)

    send_at_risk_email(task)

    send_escalation_email(task)