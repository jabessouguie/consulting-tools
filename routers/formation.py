import asyncio
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from routers.shared import (
    BASE_DIR,
    CONSULTANT_NAME,
    jobs,
    limiter,
    safe_error_message,
    safe_traceback,
    send_sse,
    templates,
)

router = APIRouter()


@router.get("/formation", response_class=HTMLResponse)
async def formation_page(request: Request):
    return templates.TemplateResponse(
        "formation.html",
        {
            "request": request,
            "active": "formation",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/formation/generate")
@limiter.limit("5/minute")
async def api_formation_generate(
    request: Request,
    client_needs: str = Form(...),
):
    """Lance la génération d'un programme de formation"""
    if len(client_needs.strip()) < 20:
        return JSONResponse(
            {"error": "Le besoin est trop court (minimum 20 caractères)."}, status_code=400
        )

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "formation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_formation_generator,
        args=(job_id, client_needs),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_formation_generator(job_id: str, client_needs: str):
    """Génère le programme de formation en background"""
    job = jobs[job_id]

    try:
        from agents.formation_generator import FormationGeneratorAgent

        agent = FormationGeneratorAgent()

        job["steps"].append({"step": "analyze", "status": "active", "progress": 10})
        job["steps"].append({"step": "analyze", "status": "done", "progress": 20})
        job["steps"].append({"step": "generate", "status": "active", "progress": 30})

        result = agent.generate_programme(client_needs)

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "format", "status": "active", "progress": 85})

        # Sauvegarder le markdown
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        title = result["metadata"].get("title", "Programme_Formation")
        safe_title = title.replace(" ", "_").replace("/", "-")[:50]
        md_path = output_dir / f"formation_{safe_title}_{timestamp}.md"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        job["steps"].append({"step": "format", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "content": result["markdown"],
            "metadata": result["metadata"],
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/formation/stream/{job_id}")
async def api_formation_stream(job_id: str):
    """SSE stream pour la progression de la génération de formation"""

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


@router.post("/api/formation/regenerate")
async def api_formation_regenerate(request: Request):
    """Régénère le programme avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_content = body.get("previous_content", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "formation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_formation_regenerate,
        args=(job_id, previous_content, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_formation_regenerate(job_id: str, previous_content: str, feedback: str):
    """Régénère le programme en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        from agents.formation_generator import FormationGeneratorAgent

        agent = FormationGeneratorAgent()

        job["steps"].append({"step": "generate", "status": "active", "progress": 20})

        result = agent.regenerate_with_feedback(previous_content, feedback)

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "format", "status": "active", "progress": 85})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"formation_revised_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        job["steps"].append({"step": "format", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "content": result["markdown"],
            "metadata": result["metadata"],
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.post("/api/formation/export-gdocs")
@limiter.limit("5/minute")
async def api_formation_export_gdocs(
    request: Request,
    content: str = Form(...),
    title: str = Form("Programme de Formation"),
):
    """Exporte le programme de formation vers Google Docs"""
    try:
        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            doc_url = google_client.export_markdown_to_docs(content, title)

            if doc_url:
                return JSONResponse(
                    {"doc_url": doc_url, "message": "Document Google Docs créé avec succès"}
                )
            else:
                return JSONResponse(
                    {"error": "Échec de la création du document Google Docs"}, status_code=500
                )

        except Exception as e:
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse(
                    {
                        "error": "Google API non configurée. Configurez vos credentials dans config/google_credentials.json",
                        "setup_required": True,
                    },
                    status_code=400,
                )
            else:
                raise

    except Exception as e:
        print(f"Error in export to Google Docs: {safe_traceback()}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)
