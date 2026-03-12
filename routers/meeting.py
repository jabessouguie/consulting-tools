import asyncio
import io
import os
import tempfile
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PyPDF2 import PdfReader

from agents.meeting_summarizer import MeetingSummarizerAgent
from config import get_consultant_info
from routers.shared import (
    BASE_DIR,
    COMPANY_NAME,
    CONSULTANT_NAME,
    jobs,
    limiter,
    safe_error_message,
    safe_traceback,
    send_sse,
    templates,
)

router = APIRouter()


@router.get("/meeting", response_class=HTMLResponse)
async def meeting_page(request: Request):
    return templates.TemplateResponse(
        "meeting.html",
        {
            "request": request,
            "active": "meeting",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/meeting/generate")
async def api_meeting_generate(
    transcript_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la generation d'un compte rendu de reunion"""
    text = ""

    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        else:
            text = content.decode("utf-8")
    elif transcript_text:
        text = transcript_text
    else:
        return JSONResponse({"error": "Aucun transcript fourni."}, status_code=400)

    if len(text.strip()) < 30:
        return JSONResponse({"error": "Le transcript semble trop court."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "meeting",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(target=_run_meeting_summarizer, args=(job_id, text), daemon=True)
    thread.start()

    return {"job_id": job_id}


def _run_meeting_summarizer(job_id: str, transcript: str):
    """Execute la generation de compte rendu en background"""
    job = jobs[job_id]

    try:
        agent = MeetingSummarizerAgent()

        # Step 1: Extraction
        job["steps"].append({"step": "extract", "status": "active", "progress": 10})
        extracted_result = agent.extract_key_info(transcript)
        extracted_info = extracted_result["extracted_info"]
        job["steps"].append({"step": "extract", "status": "done", "progress": 35})

        # Step 2: Compte rendu
        job["steps"].append({"step": "minutes", "status": "active", "progress": 40})
        minutes = agent.generate_minutes(transcript, extracted_info)
        job["steps"].append({"step": "minutes", "status": "done", "progress": 70})

        # Step 3: Email
        job["steps"].append({"step": "email", "status": "active", "progress": 75})
        email_result = agent.generate_email(extracted_info, minutes)
        job["steps"].append({"step": "email", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"meeting_summary_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Compte Rendu de Reunion\n\n")
            f.write(f"**Genere le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n---\n\n")
            f.write(minutes)
            f.write("\n\n---\n\n# Mail de Partage\n\n")
            f.write(f"**Objet:** {email_result['subject']}\n\n")
            f.write(email_result["body"])

        job["status"] = "done"
        job["result"] = {
            "minutes": minutes,
            "email": email_result,
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
        print(f"Error in meeting summarizer: {safe_traceback()}")


@router.get("/api/meeting/stream/{job_id}")
async def api_meeting_stream(job_id: str):
    """SSE stream pour la progression du compte rendu"""

    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouve"})
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


@router.post("/api/meeting/regenerate")
async def api_meeting_regenerate(request: Request):
    """Regenere le compte rendu avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_minutes = body.get("previous_minutes", "")
    previous_email = body.get("previous_email", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "meeting",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_meeting_feedback,
        args=(job_id, previous_minutes, previous_email, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_meeting_feedback(job_id: str, previous_minutes: str, previous_email: str, feedback: str):
    """Regenere le compte rendu en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = MeetingSummarizerAgent()

        job["steps"].append({"step": "extract", "status": "done", "progress": 10})
        job["steps"].append({"step": "minutes", "status": "active", "progress": 30})

        # Regenerer le compte rendu
        revised_minutes = agent.llm_client.generate(
            prompt="""Voici un compte rendu de reunion genere precedemment:

{previous_minutes}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce compte rendu en integrant les corrections demandees.
Conserve la structure professionnelle (contexte, points abordes, decisions, plan d'actions, points en suspens, prochaines etapes).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt="""Tu es {
                agent.consultant_info['name']}, {
                agent.consultant_info['title']} chez {
                agent.consultant_info['company']}.
Tu corriges un compte rendu de reunion selon le retour du consultant.""",
            temperature=0.5,
            max_tokens=3000,
        )

        job["steps"].append({"step": "minutes", "status": "done", "progress": 70})
        job["steps"].append({"step": "email", "status": "active", "progress": 75})

        # Regenerer le mail
        revised_email = agent.llm_client.generate(
            prompt="""Voici un mail de partage de compte rendu genere precedemment:

{previous_email}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce mail en integrant les corrections demandees.
Conserve le format professionnel (objet, resume executif, decisions cles, actions, signature).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt="""Tu es {
                agent.consultant_info['name']}, {
                agent.consultant_info['title']} chez {
                agent.consultant_info['company']}.
Tu corriges un mail professionnel selon le retour du consultant.""",
            temperature=0.5,
            max_tokens=1500,
        )

        job["steps"].append({"step": "email", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "minutes": revised_minutes,
            "email": revised_email,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.post("/api/meeting/share-email")
@limiter.limit("10/minute")
async def api_meeting_share_email(request: Request):
    """Partage le compte rendu de reunion par email avec piece jointe"""
    from utils.gmail_client import GmailClient
    from utils.validation import validate_email

    body = await request.json()
    to_email = body.get("to_email", "").strip()
    meeting_summary = body.get("meeting_summary", "")
    meeting_title = body.get("meeting_title", "Sans titre")

    # Valider email
    if not to_email:
        return JSONResponse({"error": "Email destinataire manquant"}, status_code=400)

    if not validate_email(to_email):
        return JSONResponse({"error": "Email destinataire invalide"}, status_code=400)

    if not meeting_summary:
        return JSONResponse({"error": "Compte rendu manquant"}, status_code=400)

    try:
        # Get consultant info
        consultant_info = get_consultant_info()

        # Creer fichier temporaire pour le compte rendu
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix=f"compte_rendu_{timestamp}_",
            delete=False,
            encoding="utf-8",
        )

        temp_file.write(meeting_summary)
        temp_file.close()

        # Construire email avec les vraies informations du consultant
        consultant_name = consultant_info.get("name", CONSULTANT_NAME)
        consultant_company = consultant_info.get("company", COMPANY_NAME)
        subject = f"Compte rendu de reunion - {meeting_title}"
        email_body = (
            f"Bonjour,\n\nVeuillez trouver ci-joint le compte rendu de notre reunion"
            f" : {meeting_title}.\n\n"
            f"Cordialement,\n{consultant_name}\n{consultant_company}\n"
        )

        # Envoyer email
        gmail = GmailClient()
        result = gmail.send_email(
            to=to_email, subject=subject, body=email_body, attachments=[temp_file.name]
        )

        # Supprimer fichier temporaire
        os.unlink(temp_file.name)

        return JSONResponse({"message": "Email envoye avec succes", "id": result["id"]})

    except FileNotFoundError as e:
        return JSONResponse(
            {"error": f"Fichier non trouve: {safe_error_message(e)}"}, status_code=404
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Erreur lors de l envoi: {safe_error_message(e)}"}, status_code=500
        )
