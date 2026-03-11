import asyncio
import json
import os
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from agents.dataset_analyzer import DatasetAnalyzerAgent
from routers.shared import BASE_DIR, jobs, limiter, safe_error_message, templates, CONSULTANT_NAME
from utils.validation import sanitize_filename, validate_file_upload

router = APIRouter()


@router.get("/dataset")
async def dataset_page(request: Request):
    from fastapi.responses import HTMLResponse
    return templates.TemplateResponse(
        "dataset.html",
        {
            "request": request,
            "active": "dataset",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/dataset/analyze")
@limiter.limit("5/minute")
async def api_dataset_analyze(request: Request, file: UploadFile = File(...)):
    """Lance l'analyse d'un dataset"""

    # Valider le fichier (taille, type)
    allowed_exts = {".csv", ".xlsx", ".xls"}
    content = await validate_file_upload(file, allowed_extensions=allowed_exts)
    filename = sanitize_filename(file.filename or "dataset.csv")

    # Sauvegarder temporairement le fichier
    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = temp_dir / f"upload_{timestamp}_{filename}"

    with open(temp_path, "wb") as f:
        f.write(content)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "dataset",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
        "temp_file": str(temp_path),
    }

    thread = threading.Thread(
        target=_run_dataset_analyzer, args=(job_id, str(temp_path), filename), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_dataset_analyzer(job_id: str, file_path: str, filename: str):
    """Execute l'analyse de dataset en background"""
    job = jobs[job_id]

    try:
        agent = DatasetAnalyzerAgent()

        # Step 1: Load
        job["steps"].append({"step": "load", "status": "active", "progress": 10})
        df = agent.load_dataset(file_path)
        job["steps"].append({"step": "load", "status": "done", "progress": 25})

        # Step 2: Structure
        job["steps"].append({"step": "structure", "status": "active", "progress": 30})
        structure = agent.analyze_structure(df)
        job["steps"].append({"step": "structure", "status": "done", "progress": 45})

        # Step 3: Quality
        job["steps"].append({"step": "quality", "status": "active", "progress": 50})
        quality = agent.analyze_quality(df)
        job["steps"].append({"step": "quality", "status": "done", "progress": 65})

        # Step 4: Stats
        job["steps"].append({"step": "stats", "status": "active", "progress": 70})
        stats = agent.analyze_statistics(df, structure)
        job["steps"].append({"step": "stats", "status": "done", "progress": 85})

        # Step 5: Report
        job["steps"].append({"step": "report", "status": "active", "progress": 90})
        result = agent.generate_report(df, structure, quality, stats, filename)
        job["steps"].append({"step": "report", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"dataset_analysis_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["report"])

        job["status"] = "done"
        job["result"] = {
            "report": result["report"],
            "filename": filename,
            "num_rows": structure["num_rows"],
            "num_columns": structure["num_columns"],
            "memory_mb": round(structure["memory_usage"], 2),
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

        # Nettoyer le fichier temporaire
        try:
            os.remove(file_path)
        except BaseException:
            pass

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
        # Nettoyer le fichier temporaire en cas d'erreur
        try:
            if "temp_file" in job:
                os.remove(job["temp_file"])
        except BaseException:
            pass


@router.get("/api/dataset/stream/{job_id}")
async def api_dataset_stream(job_id: str):
    """Streame le progres de l'analyse"""

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


@router.post("/api/dataset/regenerate")
async def api_dataset_regenerate(request: Request):
    """Regenere le rapport avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_report = body.get("previous_report", "")
    filename = body.get("filename", "dataset")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "dataset",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_dataset_feedback,
        args=(job_id, previous_report, feedback, filename),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_dataset_feedback(job_id: str, previous_report: str, feedback: str, filename: str):
    """Regenere le rapport en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = DatasetAnalyzerAgent()

        # Skip aux étapes finales
        job["steps"].append({"step": "load", "status": "done", "progress": 20})
        job["steps"].append({"step": "structure", "status": "done", "progress": 40})
        job["steps"].append({"step": "quality", "status": "done", "progress": 60})
        job["steps"].append({"step": "stats", "status": "done", "progress": 70})
        job["steps"].append({"step": "report", "status": "active", "progress": 80})

        system_prompt = """Tu es {
            agent.consultant_info['name']}, {
            agent.consultant_info['title']} chez {
            agent.consultant_info['company']}.
Tu corriges un rapport d'analyse de dataset selon le retour du consultant."""

        # Regenerer le rapport
        revised_report = agent.llm_client.generate(
            prompt="""Voici un rapport d'analyse de dataset généré précédemment:

{previous_report}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reécris ce rapport en intégrant les corrections demandées.
Conserve le format Markdown avec emojis et la structure (Vue d'ensemble, Structure, Qualité, Insights, Recommandations).
Ne modifie que ce qui est demandé dans le feedback.""",
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=2000,
        )

        job["steps"].append({"step": "report", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"dataset_analysis_{timestamp}_revised.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(revised_report)

        job["status"] = "done"
        job["result"] = {
            "report": revised_report,
            "filename": filename,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
