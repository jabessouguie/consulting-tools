import asyncio
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from agents.meeting_capture_agent import GEMINI_MODELS as MC_GEMINI_MODELS
from agents.meeting_capture_agent import APIKeyError as MCAPIKeyError
from agents.meeting_capture_agent import (
    DraftCreationError,
    MeetingCaptureAgent,
    MeetingGmailClient,
    VideoProcessingError,
)
from routers.shared import (
    BASE_DIR,
    CONSULTANT_NAME,
    jobs,
    limiter,
    safe_error_message,
    send_sse,
)
from utils.auth import get_current_user
from utils.validation import sanitize_filename, sanitize_text_input

router = APIRouter()


@router.get("/meeting-capture", response_class=HTMLResponse)
async def meeting_capture_page(request: Request):
    """Page Meeting Capture AI"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    from routers.shared import templates

    return templates.TemplateResponse(
        "meeting-capture.html",
        {
            "request": request,
            "active": "meeting-capture",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/meeting-capture/upload")
@limiter.limit("10/minute")
async def api_meeting_capture_upload(
    request: Request,
    video: UploadFile = File(...),
    gemini_model: str = Form(default="gemini-2.0-flash"),
):
    """Upload d'une vidéo de réunion et lancement de l'analyse Gemini"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    # Valider le modèle
    if gemini_model not in MC_GEMINI_MODELS:
        allowed = ", ".join(MC_GEMINI_MODELS.keys())
        return JSONResponse(
            {"detail": "Modèle non supporté. Modèles disponibles : " + allowed},
            status_code=400,
        )

    # Valider l'extension
    allowed_exts = {".webm", ".mp4", ".mov", ".avi", ".mkv"}
    filename = video.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_exts:
        return JSONResponse(
            {
                "detail": "Extension non supportée. Extensions acceptées : "
                + ", ".join(sorted(allowed_exts))
            },
            status_code=400,
        )

    content = await video.read()
    if not content:
        return JSONResponse({"detail": "Le fichier vidéo est vide."}, status_code=400)

    # Sauvegarder dans temp/
    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = sanitize_filename("meeting_" + timestamp + suffix)
    temp_path = temp_dir / safe_name

    with open(str(temp_path), "wb") as f:
        f.write(content)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "meeting-capture",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
        "video_path": str(temp_path),
        "gemini_model": gemini_model,
    }

    thread = threading.Thread(target=_run_meeting_capture, args=(job_id,), daemon=True)
    thread.start()

    return {"job_id": job_id}


def _run_meeting_capture(job_id: str):
    """Exécute l'analyse Meeting Capture en background"""
    job = jobs[job_id]
    video_path = job["video_path"]
    gemini_model = job["gemini_model"]

    try:
        api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        agent = MeetingCaptureAgent(api_key=api_key, model=gemini_model)

        # Étape 1 : Upload
        job["steps"].append(
            {
                "step": "upload",
                "status": "active",
                "progress": 5,
                "message": "Upload de la vidéo vers Gemini…",
            }
        )
        uploaded_file = agent.upload_video(video_path)
        job["steps"].append(
            {"step": "upload", "status": "done", "progress": 20, "message": "Vidéo uploadée"}
        )

        # Étape 2 : Attente traitement
        job["steps"].append(
            {
                "step": "processing",
                "status": "active",
                "progress": 25,
                "message": "Traitement de la vidéo par Gemini…",
            }
        )
        processed_file = agent.wait_for_processing(uploaded_file)
        job["steps"].append(
            {"step": "processing", "status": "done", "progress": 55, "message": "Vidéo traitée"}
        )

        # Étape 3 : Analyse IA
        job["steps"].append(
            {
                "step": "analyze",
                "status": "active",
                "progress": 60,
                "message": "Analyse IA en cours…",
            }
        )
        result = agent.analyze(processed_file)
        job["steps"].append(
            {"step": "analyze", "status": "done", "progress": 95, "message": "Analyse terminée"}
        )

        # Finalisation
        job["steps"].append(
            {"step": "done", "status": "done", "progress": 100, "message": "Résultats prêts"}
        )
        job["result"] = result
        job["status"] = "done"

    except (MCAPIKeyError, VideoProcessingError, TimeoutError) as exc:
        job["status"] = "error"
        job["error"] = safe_error_message(exc)
    except Exception as exc:
        job["status"] = "error"
        job["error"] = safe_error_message(exc)
    finally:
        try:
            Path(video_path).unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/api/meeting-capture/stream/{job_id}")
async def api_meeting_capture_stream(job_id: str):
    """SSE stream pour la progression de l'analyse Meeting Capture"""

    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouvé"})
            return

        last_step_idx = 0
        while True:
            while last_step_idx < len(job["steps"]):
                step = job["steps"][last_step_idx]
                yield send_sse("step", step)
                last_step_idx += 1

            if job["status"] == "done":
                yield send_sse("result", job["result"])
                return
            elif job["status"] == "error":
                yield send_sse("error_msg", {"message": job["error"]})
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/api/meeting-capture/gmail-draft")
@limiter.limit("20/minute")
async def api_meeting_capture_gmail_draft(request: Request):
    """Crée un brouillon Gmail à partir du résultat Meeting Capture"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Corps JSON invalide"}, status_code=400)

    to = sanitize_text_input(body.get("to", ""))
    subject = sanitize_text_input(body.get("subject", "Compte rendu de réunion"))
    email_body = body.get("body", "")
    credentials_path = body.get("credentials_path", "")

    if not credentials_path:
        home_dir = Path.home()
        credentials_path = str(home_dir / ".meetingcapture" / "credentials.json")

    token_path = str(Path(credentials_path).parent / "token.json")

    try:
        client = MeetingGmailClient()
        service = client.authenticate(credentials_path, token_path)
        draft = client.create_draft(service, to, subject, email_body)
        return JSONResponse(draft)
    except DraftCreationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=500)
    except Exception as exc:
        return JSONResponse({"detail": safe_error_message(exc)}, status_code=500)


@router.post("/api/meeting-capture/export-word")
async def export_meeting_word(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON invalide"}, status_code=400)
    minutes = body.get("minutes", "").strip()
    if not minutes:
        return JSONResponse({"error": "minutes requis"}, status_code=400)
    title = body.get("title", "Compte Rendu")
    # Parse markdown ## sections
    sections = []
    current_heading = ""
    current_lines: list = []
    for line in minutes.splitlines():
        if line.startswith("## "):
            if current_lines or current_heading:
                sections.append({"heading": current_heading, "body": "\n".join(current_lines).strip()})
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or current_heading:
        sections.append({"heading": current_heading, "body": "\n".join(current_lines).strip()})
    if not sections:
        sections = [{"heading": "", "body": minutes}]
    import tempfile as _tempfile
    tmp_path = _tempfile.mktemp(suffix=".docx")
    try:
        from utils.word_exporter import export_to_word
        out = export_to_word({"sections": sections}, tmp_path, title=title)
        from fastapi.responses import FileResponse
        return FileResponse(
            out or tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="compte_rendu.docx",
        )
    except Exception as exc:
        return JSONResponse({"error": safe_error_message(exc)}, status_code=500)
