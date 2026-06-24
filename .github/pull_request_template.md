# Pull Request: Merge feature/ai into main

## Overview
This PR merges the `feature/ai` branch into `main`, bringing AI-powered task classification and email management capabilities to the Cutover Agent system.

## Changes
- **LangGraph AI Agent**: Classifies inbound emails and updates task status automatically
- **Email Service Enhancements**: Integrates with Google Gemini for intelligent email generation
- **Structured Output**: Implements ReplyClassification schema for parsing employee updates
- **Database Updates**: AI-driven task status updates with audit logging
- **Follow-up & Escalation**: Automatic email routing based on task status

## Files Modified
- `app/workspace/workflow/cutover_agent.py`: Main LangGraph workflow
- `app/workspace/services/email_service.py`: Enhanced email generation with LLM
- `app/workspace/services/scheduler_service.py`: Background job scheduling
- `app/core/config.py`: AI configuration (GOOGLE_API_KEY, LANGSMITH settings)
- `requirements.txt`: Added langchain, langgraph, google-generativeai

## Testing
- AI classification tested with sample task data
- Email generation verified with Gemini API
- Database updates logged in audit table
