import asyncio
import json
import re
import threading
import uuid
from typing import List, Optional

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


@router.get("/training-slides", response_class=HTMLResponse)
async def training_slides_page(request: Request):
    return templates.TemplateResponse(
        "training-slides.html",
        {
            "request": request,
            "active": "training-slides",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/training-slides/generate")
@limiter.limit("3/minute")
async def api_training_slides_generate(
    request: Request,
    programme_text: str = Form(None),
    file: Optional[UploadFile] = File(None),
    files: List[UploadFile] = File(default=[]),
):
    """
    Lance la génération des slides de formation.

    Entrées acceptées (par priorité) :
    - files : plusieurs fichiers (TXT, MD, DOCX, PDF) — leur contenu est concaténé
    - file  : un seul fichier (compatibilité ascendante)
    - programme_text : texte brut du programme
    """
    from utils.document_parser import document_parser

    # Fusionner file (ancien) et files (nouveau) en une seule liste
    all_files: List[UploadFile] = []
    if files:
        all_files.extend(files)
    if file:
        all_files.append(file)

    text_parts: List[str] = []

    for upload in all_files:
        temp_file = BASE_DIR / "output" / f"temp_{upload.filename}"
        temp_file.parent.mkdir(exist_ok=True)
        try:
            content = await upload.read()
            with open(temp_file, "wb") as fp:
                fp.write(content)
            extracted = document_parser.parse_file(str(temp_file))
            temp_file.unlink()
            if extracted:
                text_parts.append(extracted)
            else:
                return JSONResponse(
                    {
                        "error": (
                            f"Impossible d'extraire le texte du fichier {upload.filename}. "
                            "Formats supportés : TXT, MD, DOCX, PDF"
                        )
                    },
                    status_code=400,
                )
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            return JSONResponse(
                {"error": f"Erreur lecture fichier '{upload.filename}' : {safe_error_message(e)}"},
                status_code=400,
            )

    if text_parts:
        text = "\n\n---\n\n".join(text_parts)
    elif programme_text:
        text = programme_text.strip()
    else:
        text = ""

    if not text or len(text) < 50:
        return JSONResponse(
            {"error": "Le programme est trop court (minimum 50 caractères)."}, status_code=400
        )

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "training-slides",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_training_slides_generator,
        args=(job_id, text),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_training_slides_generator(job_id: str, programme_text: str):
    """Génère les slides de formation en background"""
    job = jobs[job_id]

    try:
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent

        agent = TrainingSlidesGeneratorAgent()

        job["steps"].append({"step": "parse", "status": "active", "progress": 10})

        result = agent.generate_all_slides(programme_text)

        job["steps"].append({"step": "parse", "status": "done", "progress": 30})
        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "pptx", "status": "active", "progress": 85})

        # Générer les PPTX par module
        pptx_paths = {}
        for module_name, module_slides in result["modules_slides"].items():
            if module_slides:
                pptx_path = agent.generate_module_pptx(module_slides, module_name)
                pptx_paths[module_name] = pptx_path

        # Générer le PPTX complet
        all_pptx_path = agent.generate_module_pptx(result["all_slides"], "Complet")

        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "programme_data": result["programme_data"],
            "modules_slides": {k: v for k, v in result["modules_slides"].items()},
            "all_slides": result["all_slides"],
            "total_slides": result["total_slides"],
            "pptx_paths": pptx_paths,
            "all_pptx_path": all_pptx_path,
        }

    except Exception as e:
        print(f"Error in training slides: {safe_traceback()}")
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/training-slides/stream/{job_id}")
async def api_training_slides_stream(job_id: str):
    """SSE stream pour la progression des slides de formation"""

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


@router.post("/api/training-slides/export-slides")
@limiter.limit("3/minute")
async def api_training_slides_export(
    request: Request,
    slides_data: str = Form(...),
    title: str = Form("Support de Formation"),
):
    """Exporte les slides de formation vers Google Slides"""
    try:
        # Sanitize pour éviter les erreurs JSON
        sanitized = slides_data.strip()
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

        slides = json.loads(sanitized)

        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            presentation_id = google_client.export_pptx_to_slides(slides_data=slides, title=title)

            if presentation_id:
                presentation_url = (
                    f"https://docs.google.com/presentation/d/{presentation_id}/edit"
                )
                return JSONResponse(
                    {
                        "presentation_id": presentation_id,
                        "presentation_url": presentation_url,
                        "message": "Présentation Google Slides créée avec succès",
                    }
                )
            else:
                return JSONResponse(
                    {"error": "Échec de la création de la présentation"}, status_code=500
                )

        except Exception as e:
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse(
                    {"error": "Google API non configurée.", "setup_required": True},
                    status_code=400,
                )
            else:
                raise

    except Exception as e:
        print(f"Error in training slides export: {safe_traceback()}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)
