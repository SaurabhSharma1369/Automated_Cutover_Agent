import os
from typing import TypedDict, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Task, TaskStatus, AuditLog
from app.workspace.services.email_service import send_email

# =====================================================
# SCHEMAS
# =====================================================

class ReplyClassification(BaseModel):
    status: Literal[
        "COMPLETED",
        "ON_TRACK",
        "AT_RISK",
        "DELAYED"
    ]
    actual_percentage: int  # <-- UNIFIED: Matches Excel and DB schema
    summary: str
    delay_reason: str
    recovery_plan: str
    expected_completion: str


class EmailOutput(BaseModel):
    subject: str
    body: str


# =====================================================
# LLMs (STRUCTURED OUTPUTS)
# =====================================================

# 1. Base Model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)

# 2. Specialized Models bound to Pydantic Schemas
classifier_llm = llm.with_structured_output(ReplyClassification)
email_llm = llm.with_structured_output(EmailOutput)


# =====================================================
# STATE
# =====================================================

class CutoverState(TypedDict):
    task_id: int            
    task_name: str
    assigned_to: str
    secondary_owner: str
    responsible_team: str
    planned_percentage: float
    actual_percentage: float # <-- Input from DB, overwritten by AI Extraction
    variance: float
    reply_text: str
    status: str
    summary: str
    delay_reason: str
    recovery_plan: str
    expected_completion: str
    warning: str


# =====================================================
# CLASSIFIER
# =====================================================

def classify_reply(state: CutoverState):

    prompt = f"""
You are a Cutover Management AI.

Task: {state["task_name"]}
Planned Percentage: {state["planned_percentage"]}%
Current Database Percentage: {state["actual_percentage"]}%

Employee Update:
"{state["reply_text"]}"

Determine:
1. COMPLETED
2. ON_TRACK
3. AT_RISK
4. DELAYED

EXTRACTION RULES:
- actual_percentage: Read the "Employee Update" carefully. If the employee states a new completion percentage (e.g., "90 percent", "50%"), you MUST output that new integer. ONLY if they completely fail to mention a number should you return the Current Database Percentage ({state['actual_percentage']}).
- status: Classify based on the text.
- summary: Summarize the update.
- delay_reason: Extract the reason if delayed.
- recovery_plan: Extract the plan if provided.
- expected_completion: Extract the ETA if provided.
"""

    try:
        result = classifier_llm.invoke(prompt)

        print("\n===== CLASSIFICATION =====")
        print(result)

        return {
            "status": result.status,
            "actual_percentage": result.actual_percentage, # Overwrites old state with new update
            "summary": result.summary,
            "delay_reason": result.delay_reason,
            "recovery_plan": result.recovery_plan,
            "expected_completion": result.expected_completion
        }

    except Exception as e:
        print("LLM/PARSER ERROR:", e)
        return {
            "status": "AT_RISK",
            "actual_percentage": state["actual_percentage"], # Fallback to existing if parsing fails
            "summary": state["reply_text"],
            "delay_reason": "Unable to parse",
            "recovery_plan": "",
            "expected_completion": ""
        }


# =====================================================
# WARNING NODE
# =====================================================

def warning_check(state: CutoverState):

    warning = ""
    # Check gap using the newly extracted actual_percentage
    gap = state["planned_percentage"] - state["actual_percentage"]

    if gap > 20:
        warning = f"Behind planned progress by {gap}%"
        print("WARNING:", warning)

    return {"warning": warning}


# =====================================================
# UPDATE DB
# =====================================================

def update_db(state: CutoverState):

    print("\n===== UPDATE TRACKER =====")
    print(f"Task ID: {state['task_id']} | Status: {state['status']} | Actual: {state['actual_percentage']}%")

    db = SessionLocal()
    
    try:
        task = db.query(Task).filter(Task.id == state["task_id"]).first()

        if task:
            previous_status = task.status

            status_map = {
                "COMPLETED": TaskStatus.DONE,
                "ON_TRACK": TaskStatus.PENDING,
                "AT_RISK": TaskStatus.BLOCKED,
                "DELAYED": TaskStatus.OVERDUE
            }

            # Update the Task record
            task.status = status_map.get(state["status"], task.status)
            task.actual_percentage = state["actual_percentage"] # <-- Saves exactly to your DB field
            
            if state["delay_reason"] and state["delay_reason"].lower() != "none":
                task.delay_reason = state["delay_reason"]
            if state["recovery_plan"] and state["recovery_plan"].lower() != "none":
                task.recovery_plan = state["recovery_plan"]
            if state["warning"]:
                task.warning = state["warning"]

            # Record the change in the AuditLog
            audit_entry = AuditLog(
                task_id=task.id,
                previous_status=previous_status.value if hasattr(previous_status, "value") else str(previous_status),
                new_status=task.status.value,
                changed_by="LangGraph AI",
                reason_summary=f"AI Tracker Update: {state['summary'][:200]}"
            )
            db.add(audit_entry)

            # Commit
            db.commit()
            print(f"✅ Successfully updated Task #{task.id} in PostgreSQL.")
            
        else:
            print(f"⚠️ Task ID #{state['task_id']} not found in the database. Skipping DB update.")

    except Exception as e:
        print(f"❌ Failed to update PostgreSQL: {e}")
        db.rollback()
    finally:
        db.close()

    return state


# =====================================================
# FOLLOWUP
# =====================================================

def followup(state: CutoverState):

    prompt = f"""
You are an Enterprise Cutover Management Assistant.

Write a professional follow-up email.

Rules:
- Do NOT mention any employee name.
- Do NOT use personal greetings.
- Start the email with exactly:
  Hello,
- Keep the tone professional and concise.
- Include a bolded note at the bottom (just before the signature) saying: "**IMPORTANT: When replying, please keep the exact subject line intact. The [Task #{state['task_id']}] tag is required to automatically log your update.**"
- End the email exactly with:

Regards,
Cutover Agent

Task: {state["task_name"]}
Current Actual Percentage: {state["actual_percentage"]}%
Issue: {state["delay_reason"]}
Recovery Plan: {state["recovery_plan"]}

Request:
1. Updated ETA
2. Remaining blockers
3. Recovery actions
4. Current actual percentage
"""

    try:
        email = email_llm.invoke(prompt)
        send_email(
            to_email=state["assigned_to"],
            subject=f"{email.subject} [Task #{state['task_id']}]", 
            body=email.body,
            cc=state["secondary_owner"]
        )
        print(f"📧 Follow-up email sent for task ID #{state['task_id']}")
    except Exception as e:
        print("FOLLOWUP EMAIL ERROR:", e)

    return state


# =====================================================
# ESCALATION
# =====================================================

def escalate(state: CutoverState):

    prompt = f"""
You are an Enterprise Cutover Management Assistant.

Write a professional escalation email.

Rules:
- Do NOT mention any employee name.
- Do NOT use personal greetings.
- Start the email with exactly:
  Hello,
- Keep the email concise and executive-friendly.
- Include a bolded note at the bottom (just before the signature) saying: "**IMPORTANT: When replying, please keep the exact subject line intact. The [Task #{state['task_id']}] tag is required to automatically log your update.**"
- End the email exactly with:

Regards,
Cutover Agent

Task: {state["task_name"]}
Status: {state["status"]}
Actual Percentage: {state["actual_percentage"]}%
Delay Reason: {state["delay_reason"]}
Recovery Plan: {state["recovery_plan"]}

Provide:
1. Executive summary
2. Current risk
3. Impact to cutover timeline
4. Recovery actions underway
5. Support required from responsible team
"""

    try:
        email = email_llm.invoke(prompt)
        send_email(
            to_email=state["responsible_team"],
            subject=f"{email.subject} [Task #{state['task_id']}]",
            body=email.body,
            cc=state["secondary_owner"]
        )
        print(f"🚨 Escalation email sent for task ID #{state['task_id']}")
    except Exception as e:
        print("ESCALATION EMAIL ERROR:", e)

    return state


# =====================================================
# ROUTER
# =====================================================

def route_after_update(state: CutoverState):
    """
    Decides the next step ONLY AFTER the database has been updated.
    """
    status = state["status"]

    if status == "AT_RISK":
        return "followup"

    if status == "DELAYED":
        return "escalate"

    # For COMPLETED or ON_TRACK, we do nothing else and end the graph.
    return "end"


# =====================================================
# GRAPH
# =====================================================

builder = StateGraph(CutoverState)

builder.add_node("classify", classify_reply)
builder.add_node("warning_check", warning_check)
builder.add_node("update", update_db)
builder.add_node("followup", followup)
builder.add_node("escalate", escalate)

builder.set_entry_point("classify")

# The Linear Flow (Executes for EVERY task)
builder.add_edge("classify", "warning_check")
builder.add_edge("warning_check", "update")

# The Branching Flow (Executes AFTER the database is saved)
builder.add_conditional_edges(
    "update",
    route_after_update,
    {
        "end": END,
        "followup": "followup",
        "escalate": "escalate"
    }
)

# Both email nodes terminate the graph once they finish sending
builder.add_edge("followup", END)
builder.add_edge("escalate", END)

graph = builder.compile()


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    initial_state = {
        "task_id": 42,
        "task_name": "Database Migration",
        "assigned_to": "jitendra@company.com",
        "secondary_owner": "backup.owner@company.com",
        "responsible_team": "database-team@company.com",
        "planned_percentage": 100,
        "actual_percentage": 75, # Starts at 75 from DB
        "variance": 25,
        "reply_text": """
    Task is 85% complete.

    Waiting for security approval.

    Expected completion by 5 PM.

    Recovery plan:
    Dedicated review call at 2 PM.
    """,
        "status": "",
        "summary": "",
        "delay_reason": "",
        "recovery_plan": "",
        "expected_completion": "",
        "warning": ""
    }

    result = graph.invoke(initial_state)

    print("\n===== FINAL STATE =====")
    for k, v in result.items():
        print(f"{k}: {v}")