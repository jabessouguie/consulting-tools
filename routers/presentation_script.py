"""Router: Presentation Script Generator — GET /presentation-script, POST /api/presentation-script/generate"""
import asyncio
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
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


@router.get("/presentation-script", response_class=HTMLResponse)
async def presentation_script_page(request: Request):
    return templates.TemplateResponse(
        "presentation-script.html",
        {"request": request, "active": "presentation-script", "consultant_name": CONSULTANT_NAME},
    )


@router.post("/api/presentation-script/generate")
@limiter.limit("3/minute")
async def api_presentation_script_generate(
    request: Request,
    pptx_file: UploadFile = File(...),
    context: str = Form(""),
):
    """Lance la génération du script de présentation à partir d'un PPTX."""
    filename = pptx_file.filename or ""
    if not filename.lower().endswith(".pptx"):
        return JSONResponse({"error": "Seuls les fichiers PPTX sont acceptés."}, status_code=400)

    content = await pptx_file.read()
    if not content:
        return JSONResponse({"error": "Fichier vide."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    temp_path = BASE_DIR / "output" / f"temp_script_{job_id}.pptx"
    temp_path.parent.mkdir(exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(content)

    jobs[job_id] = {
        "type": "presentation-script",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    threading.Thread(
        target=_run_presentation_script,
        args=(job_id, str(temp_path), context.strip()),
        daemon=True,
    ).start()

    return {"job_id": job_id}


def _run_presentation_script(job_id: str, pptx_path: str, context: str):
    job = jobs[job_id]
    try:
        from agents.presentation_script_generator import PresentationScriptGenerator

        agent = PresentationScriptGenerator()

        job["steps"].append({"step": "extract", "status": "active", "progress": 10})
        result = agent.run(pptx_path, context)
        job["steps"].append({"step": "extract", "status": "done", "progress": 50})
        job["steps"].append({"step": "generate", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "markdown": result.get("markdown", ""),
            "num_slides": result.get("num_slides", 0),
            "estimated_duration": result.get("estimated_duration", ""),
        }

    except Exception as e:
        print(f"Error in presentation script: {safe_traceback()}")
        job["status"] = "error"
        job["error"] = safe_error_message(e)
    finally:
        Path(pptx_path).unlink(missing_ok=True)


@router.get("/api/presentation-script/stream/{job_id}")
async def api_presentation_script_stream(job_id: str):
    """SSE stream pour suivre la génération du script."""

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
