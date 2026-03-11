import asyncio
import json
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from agents.workshop_planner import WorkshopPlannerAgent
from routers.shared import BASE_DIR, CONSULTANT_NAME, jobs, limiter, safe_error_message, templates

router = APIRouter()


@router.get("/workshop", response_class=HTMLResponse)
async def workshop_page(request: Request):
    return templates.TemplateResponse(
        "workshop.html",
        {
            "request": request,
            "active": "workshop",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/workshop/generate")
@limiter.limit("5/minute")
async def api_workshop_generate(request: Request):
    """Lance la génération d'un plan de workshop"""
    body = await request.json()
    topic = body.get("topic", "").strip()
    duration = body.get("duration", "full_day")
    audience = body.get("audience", "Professionnels").strip()
    objectives = body.get("objectives", "").strip()

    if not topic:
        return JSONResponse({"error": "Le sujet est obligatoire."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "workshop",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_workshop_planner,
        args=(job_id, topic, duration, audience, objectives),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_workshop_planner(job_id: str, topic: str, duration: str, audience: str, objectives: str):
    """Execute la génération de plan en background"""
    job = jobs[job_id]

    try:
        agent = WorkshopPlannerAgent()

        job["steps"].append({"step": "plan", "status": "active", "progress": 30})
        result = agent.generate_workshop_plan(topic, duration, audience, objectives)
        job["steps"].append({"step": "plan", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_")).strip()[:50]
        safe_topic = safe_topic.replace(" ", "_")

        md_path = output_dir / f"workshop_{safe_topic}_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["plan"])

        job["status"] = "done"
        job["result"] = {
            "plan": result["plan"],
            "topic": topic,
            "duration": result["duration"],
            "audience": audience,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/workshop/stream/{job_id}")
async def api_workshop_stream(job_id: str):
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


@router.post("/api/workshop/regenerate")
async def api_workshop_regenerate(request: Request):
    """Regenere avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_plan = body.get("previous_plan", "")
    topic = body.get("topic", "Workshop")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "workshop",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_workshop_feedback,
        args=(job_id, previous_plan, feedback, topic),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_workshop_feedback(job_id: str, previous_plan: str, feedback: str, topic: str):
    """Regenere avec feedback"""
    job = jobs[job_id]

    try:
        agent = WorkshopPlannerAgent()

        job["steps"].append({"step": "plan", "status": "active", "progress": 50})

        system_prompt = """Tu es {
            agent.consultant_info['name']}, {
            agent.consultant_info['title']} chez {
            agent.consultant_info['company']}.
Tu corriges un plan de formation selon le retour du consultant."""

        revised_plan = agent.llm_client.generate(
            prompt="""Voici un plan de workshop généré précédemment:

{previous_plan}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reécris ce plan en intégrant les corrections demandées.
Conserve le format Markdown et la structure.
Ne modifie que ce qui est demandé dans le feedback.""",
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=3500,
        )

        job["steps"].append({"step": "plan", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_")).strip()[:50]
        safe_topic = safe_topic.replace(" ", "_")

        md_path = output_dir / f"workshop_{safe_topic}_{timestamp}_revised.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(revised_plan)

        job["status"] = "done"
        job["result"] = {
            "plan": revised_plan,
            "topic": topic,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
