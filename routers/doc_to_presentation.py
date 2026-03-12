"""Router: Doc to Presentation — GET /doc-to-presentation, POST /api/doc-to-presentation/generate"""
import asyncio
import threading
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

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

ALLOWED_EXTENSIONS = {".md", ".pdf", ".docx", ".txt"}


@router.get("/doc-to-presentation", response_class=HTMLResponse)
async def doc_to_presentation_page(request: Request):
    return templates.TemplateResponse(
        "doc-to-presentation.html",
        {"request": request, "active": "doc-to-presentation", "consultant_name": CONSULTANT_NAME},
    )


@router.post("/api/doc-to-presentation/generate")
@limiter.limit("3/minute")
async def api_doc_to_presentation_generate(
    request: Request,
    files: List[UploadFile] = File(...),
    target_audience: str = Form(...),
    objective: str = Form(...),
):
    """Lance la conversion de documents en présentation PPTX."""
    target_audience = target_audience.strip()
    objective = objective.strip()

    if not files:
        return JSONResponse({"error": "Au moins un document requis."}, status_code=400)
    if not target_audience or not objective:
        return JSONResponse({"error": "Public cible et objectif requis."}, status_code=400)

    documents = []
    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                {"error": f"Format non supporté : {upload.filename}. Formats acceptés : MD, PDF, DOCX, TXT"},
                status_code=400,
            )
        content = await upload.read()
        if not content:
            return JSONResponse({"error": f"Fichier vide : {upload.filename}"}, status_code=400)
        documents.append({"filename": upload.filename, "content": content})

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "doc-to-presentation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    threading.Thread(
        target=_run_doc_to_presentation,
        args=(job_id, documents, target_audience, objective),
        daemon=True,
    ).start()

    return {"job_id": job_id}


def _run_doc_to_presentation(
    job_id: str, documents: list, target_audience: str, objective: str
):
    job = jobs[job_id]
    try:
        from agents.doc_to_presentation import DocToPresentationAgent

        agent = DocToPresentationAgent()

        job["steps"].append({"step": "parse", "status": "active", "progress": 10})
        result = agent.run(documents, target_audience, objective)

        if "error" in result:
            job["status"] = "error"
            job["error"] = result["error"]
            return

        job["steps"].append({"step": "parse", "status": "done", "progress": 30})
        job["steps"].append({"step": "structure", "status": "done", "progress": 60})
        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        # Extract just the filename for the download URL
        pptx_path = result.get("pptx_path", "")
        pptx_filename = Path(pptx_path).name if pptx_path else ""

        job["status"] = "done"
        job["result"] = {
            "slide_count": result.get("slide_count", 0),
            "pptx_filename": pptx_filename,
            "generated_at": result.get("generated_at", ""),
        }

    except Exception as e:
        print(f"Error in doc to presentation: {safe_traceback()}")
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/doc-to-presentation/stream/{job_id}")
async def api_doc_to_presentation_stream(job_id: str):
    """SSE stream pour suivre la génération de la présentation."""

    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouvé"})
            return

        last_step_idx = 0
        while True:
            while last_step_idx < len(job["steps"]):
                yield send_sse("step", job["steps"][last_step_idx])
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


@router.get("/api/doc-to-presentation/download/{filename}")
async def api_doc_to_presentation_download(filename: str):
    """Télécharge le fichier PPTX généré."""
    safe_name = Path(filename).name  # prevent path traversal
    if not safe_name.endswith(".pptx"):
        return JSONResponse({"error": "Fichier non trouvé"}, status_code=404)

    file_path = BASE_DIR / "output" / safe_name
    if not file_path.exists():
        return JSONResponse({"error": "Fichier non trouvé"}, status_code=404)

    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=safe_name,
    )
