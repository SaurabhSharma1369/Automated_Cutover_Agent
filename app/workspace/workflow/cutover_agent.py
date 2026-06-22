import os
from typing import TypedDict, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings


# =====================================================
# EMAIL SERVICE
# =====================================================

def send_email(to_email, subject, body, cc=None):

    print("\n==============================")
    print("EMAIL SENT")
    print("==============================")
    print("TO :", to_email)

    if cc:
        print("CC :", cc)

    print("SUBJECT :", subject)

    print("BODY :")
    print(body)

    print("==============================\n")


# =====================================================
# LLM
# =====================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)


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

    completion_percentage: int

    summary: str

    delay_reason: str

    recovery_plan: str

    expected_completion: str


class EmailOutput(BaseModel):

    subject: str

    body: str


classifier_parser = PydanticOutputParser(
    pydantic_object=ReplyClassification
)

email_parser = PydanticOutputParser(
    pydantic_object=EmailOutput
)


# =====================================================
# STATE
# =====================================================

class CutoverState(TypedDict):

    task_name: str

    assigned_to: str

    secondary_owner: str

    responsible_team: str

    planned_percentage: float

    actual_percentage: float

    variance: float

    reply_text: str

    status: str

    completion_percentage: int

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

Task:
{state["task_name"]}

Planned Completion:
{state["planned_percentage"]}%

Current Completion:
{state["actual_percentage"]}%

Variance:
{state["variance"]}

Employee Update:
{state["reply_text"]}

Determine:

1. COMPLETED
2. ON_TRACK
3. AT_RISK
4. DELAYED

Extract:

status
completion_percentage
summary
delay_reason
recovery_plan
expected_completion

{classifier_parser.get_format_instructions()}
"""

    response = llm.invoke(prompt)

    try:

        result = classifier_parser.parse(
            response.content
        )

        print("\n===== CLASSIFICATION =====")
        print(result)

        return {
            "status": result.status,
            "completion_percentage": result.completion_percentage,
            "summary": result.summary,
            "delay_reason": result.delay_reason,
            "recovery_plan": result.recovery_plan,
            "expected_completion": result.expected_completion
        }

    except Exception as e:

        print("PARSER ERROR:", e)

        return {
            "status": "AT_RISK",
            "completion_percentage": state["actual_percentage"],
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

    gap = (
        state["planned_percentage"]
        - state["completion_percentage"]
    )

    if gap > 20:

        warning = (
            f"Behind planned progress by {gap}%"
        )

        print("WARNING:", warning)

    return {
        "warning": warning
    }


# =====================================================
# UPDATE DB
# =====================================================

def update_db(state: CutoverState):

    print("\n===== UPDATE TRACKER =====")

    print(
        f"""
Task: {state["task_name"]}

Status: {state["status"]}

Completion: {state["completion_percentage"]}%

ETA: {state["expected_completion"]}

Delay Reason:
{state["delay_reason"]}

Recovery Plan:
{state["recovery_plan"]}

Warning:
{state["warning"]}
"""
    )

    # TODO
    # PostgreSQL update
    # Excel update
    # Dashboard update

    return state


# =====================================================
# FOLLOWUP
# =====================================================

def followup(state: CutoverState):

    employee_email = state["assigned_to"]

    cc_email = state["secondary_owner"]

    prompt = f"""
You are an Enterprise Cutover Management Assistant.

Write a professional follow-up email.

Rules:
- Do NOT mention any employee name.
- Do NOT use personal greetings.
- Start the email with exactly:
  Hello,
- Keep the tone professional and concise.
- Ask for the required information clearly.
- End the email exactly with:

Regards,
Cutover Agent

Task:
{state["task_name"]}

Current Completion:
{state["completion_percentage"]}%

Issue:
{state["delay_reason"]}

Recovery Plan:
{state["recovery_plan"]}

Request the following:

1. Updated ETA
2. Remaining blockers
3. Recovery actions
4. Current completion percentage
5. Any support required from dependent teams

{email_parser.get_format_instructions()}
"""

    response = llm.invoke(prompt)

    try:

        email = email_parser.parse(
            response.content
        )

        send_email(
            to_email=employee_email,
            subject=email.subject,
            body=email.body,
            cc=cc_email
        )

        print(
            f"Follow-up email sent for task: "
            f"{state['task_name']}"
        )

    except Exception as e:
        print("FOLLOWUP EMAIL ERROR:", e)

    return state
# =====================================================
# ESCALATION
# =====================================================

def escalate(state: CutoverState):

    team_dl = state["responsible_team"]

    prompt = f"""
You are an Enterprise Cutover Management Assistant.

Write a professional escalation email.

Rules:
- Do NOT mention any employee name.
- Do NOT use personal greetings.
- Start the email with exactly:
  Hello,
- Keep the email concise and executive-friendly.
- Clearly highlight the risk, impact, and required action.
- End the email exactly with:

Regards,
Cutover Agent

Task:
{state["task_name"]}

Current Status:
{state["status"]}

Completion Percentage:
{state["completion_percentage"]}%

Delay Reason:
{state["delay_reason"]}

Recovery Plan:
{state["recovery_plan"]}

Expected Completion:
{state["expected_completion"]}

Provide:
1. Executive summary
2. Current risk
3. Impact to cutover timeline
4. Recovery actions underway
5. Support required from responsible team

{email_parser.get_format_instructions()}
"""

    response = llm.invoke(prompt)

    try:

        email = email_parser.parse(
            response.content
        )

        send_email(
            to_email=team_dl,
            subject=email.subject,
            body=email.body,
            cc=state["secondary_owner"]
        )

        print(
            f"Escalation email sent for task: "
            f"{state['task_name']}"
        )

    except Exception as e:

        print("ESCALATION EMAIL ERROR:", e)

    return state
# =====================================================
# ROUTER
# =====================================================

def route(state: CutoverState):

    status = state["status"]

    if status == "COMPLETED":
        return "update"

    if status == "ON_TRACK":
        return "update"

    if status == "AT_RISK":
        return "followup"

    if status == "DELAYED":
        return "escalate"

    return "update"


# =====================================================
# GRAPH
# =====================================================

builder = StateGraph(CutoverState)

builder.add_node(
    "classify",
    classify_reply
)

builder.add_node(
    "warning_check",
    warning_check
)

builder.add_node(
    "update",
    update_db
)

builder.add_node(
    "followup",
    followup
)

builder.add_node(
    "escalate",
    escalate
)

builder.set_entry_point(
    "classify"
)

builder.add_edge(
    "classify",
    "warning_check"
)

builder.add_conditional_edges(
    "warning_check",
    route,
    {
        "update": "update",
        "followup": "followup",
        "escalate": "escalate"
    }
)

builder.add_edge("update", END)
builder.add_edge("followup", END)
builder.add_edge("escalate", END)

graph = builder.compile()


# =====================================================
# TEST
# =====================================================

initial_state = {

    "task_name": "Database Migration",

    "assigned_to": "jitendra@company.com",

    "secondary_owner": "backup.owner@company.com",

    "responsible_team": "database-team@company.com",

    "planned_percentage": 100,

    "actual_percentage": 75,

    "variance": 25,

    "reply_text": """
Task is 75% complete.

Waiting for security approval.

Expected completion by 5 PM.

Recovery plan:
Dedicated review call at 2 PM.
""",

    "status": "",

    "completion_percentage": 0,

    "summary": "",

    "delay_reason": "",

    "recovery_plan": "",

    "expected_completion": "",

    "warning": ""
}

result = graph.invoke(initial_state)

print("\n===== FINAL STATE =====")

for k, v in result.items():
    print(k, ":", v)