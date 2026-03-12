"""Router: Microsoft 365 — POST /api/microsoft/test-connection, POST /api/teams/analyze-meeting"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from routers.shared import safe_error_message

router = APIRouter()


@router.post("/api/microsoft/test-connection")
async def microsoft_test_connection():
    try:
        from utils.microsoft_client import MicrosoftAuthError, MicrosoftAPIError, MicrosoftClient
        client = MicrosoftClient()
        client.test_connection()
        return JSONResponse({"ok": True})
    except Exception as e:
        from utils.microsoft_client import MicrosoftAuthError, MicrosoftAPIError
        if isinstance(e, (MicrosoftAuthError, MicrosoftAPIError)):
            return JSONResponse({"ok": False, "error": str(e)}, status_code=422)
        return JSONResponse({"ok": False, "error": safe_error_message(e)}, status_code=500)


@router.post("/api/teams/analyze-meeting")
async def teams_analyze_meeting(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON invalide"}, status_code=400)
    meeting_id = body.get("meeting_id", "").strip()
    if not meeting_id:
        return JSONResponse({"error": "meeting_id requis"}, status_code=400)
    try:
        from utils.microsoft_client import MicrosoftAuthError, MicrosoftAPIError
        from agents.teams_meeting_agent import TeamsMeetingAgent
        agent = TeamsMeetingAgent()
        result = agent.analyze_meeting(meeting_id)
        return JSONResponse(result)
    except Exception as e:
        from utils.microsoft_client import MicrosoftAuthError, MicrosoftAPIError
        if isinstance(e, (MicrosoftAuthError, MicrosoftAPIError)):
            return JSONResponse({"error": str(e)}, status_code=422)
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)
