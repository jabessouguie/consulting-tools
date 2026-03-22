import asyncio
import io
import json
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PyPDF2 import PdfReader

from agents.rfp_responder import RFPResponderAgent
from routers.shared import BASE_DIR, CONSULTANT_NAME, jobs, limiter, safe_error_message, templates

router = APIRouter()


@router.get("/rfp", response_class=HTMLResponse)
async def rfp_page(request: Request):
    return templates.TemplateResponse(
        "rfp.html",
        {
            "request": request,
            "active": "rfp",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/rfp/generate")
@limiter.limit("3/minute")
async def api_rfp_generate(
    request: Request,
    rfp_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la génération de réponse au RFP"""
    text = ""

    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        else:
            text = content.decode("utf-8")
    elif rfp_text:
        text = rfp_text
    else:
        return JSONResponse({"error": "Aucun RFP fourni."}, status_code=400)

    if len(text.strip()) < 100:
        return JSONResponse({"error": "Le RFP semble trop court."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "rfp",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(target=_run_rfp_responder, args=(job_id, text), daemon=True)
    thread.start()

    return {"job_id": job_id}


def _run_rfp_responder(job_id: str, rfp_text: str):
    """Execute la génération en background"""
    job = jobs[job_id]

    try:
        agent = RFPResponderAgent()

        # Step 1: Analyze
        job["steps"].append({"step": "analyze", "status": "active", "progress": 20})
        analysis = agent.analyze_rfp(rfp_text)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 40})

        # Step 2: Generate response
        job["steps"].append({"step": "response", "status": "active", "progress": 50})
        result = agent.generate_response(rfp_text, analysis)
        job["steps"].append({"step": "response", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"rfp_response_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Réponse à l'appel d'offres\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("---\n\n")
            f.write(result["response"])

        job["status"] = "done"
        job["result"] = {
            "response": result["response"],
            "analysis": analysis,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/rfp/stream/{job_id}")
async def api_rfp_stream(job_id: str):
    """Streame le progres"""

    async def event_generator():
        while True:
            if job_id not in jobs:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break

            job = jobs[job_id]
            yield f"data: {json.dumps(job)}\n\n"

            if job["status"] in ["done", "error"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/api/rfp/regenerate")
async def api_rfp_regenerate(request: Request):
    """Regenere avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_response = body.get("previous_response", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "rfp",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_rfp_feedback,
        args=(job_id, previous_response, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_rfp_feedback(job_id: str, previous_response: str, feedback: str):
    """Regenere avec feedback"""
    job = jobs[job_id]

    try:
        agent = RFPResponderAgent()

        job["steps"].append({"step": "analyze", "status": "done", "progress": 30})
        job["steps"].append({"step": "response", "status": "active", "progress": 50})

        system_prompt = """Tu es {
            agent.consultant_info['name']}, {
            agent.consultant_info['title']} chez {
            agent.consultant_info['company']}.
Tu corriges une réponse à un appel d'offres selon le retour du consultant."""

        revised_response = agent.llm_client.generate(
            prompt="""Voici une réponse à un RFP générée précédemment:

{previous_response}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reécris cette réponse en intégrant les corrections demandées.
Conserve le format Markdown et la structure en 10 sections.
Ne modifie que ce qui est demandé dans le feedback.""",
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4000,
        )

        job["steps"].append({"step": "response", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"rfp_response_{timestamp}_revised.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(revised_response)

        job["status"] = "done"
        job["result"] = {
            "response": revised_response,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
