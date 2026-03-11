import asyncio
import json
import threading
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.responses import RedirectResponse

from agents.tech_monitor import TechMonitorAgent
from routers.shared import BASE_DIR, jobs, limiter, safe_error_message

router = APIRouter()


@router.get("/techwatch")
async def techwatch_page():
    """Redirection vers la nouvelle page veille"""
    return RedirectResponse(url="/veille", status_code=301)


@router.post("/api/techwatch/generate")
@limiter.limit("3/minute")
async def api_techwatch_generate(request: Request):
    """Lance la génération d'un digest de veille tech"""
    body = await request.json()
    keywords_str = body.get("keywords", "").strip()
    keywords = [k.strip() for k in keywords_str.split(",")] if keywords_str else None
    days = int(body.get("days", 7))
    period_type = body.get("period_type", "weekly")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "techwatch",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_tech_monitor, args=(job_id, keywords, days, period_type), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_tech_monitor(job_id: str, keywords: List[str], days: int, period_type: str):
    """Execute la génération de digest en background"""
    job = jobs[job_id]

    try:
        agent = TechMonitorAgent()

        # Step 1: Collecte
        job["steps"].append({"step": "collect", "status": "active", "progress": 10})
        articles = agent.collect_articles(keywords=keywords, days=days)
        job["steps"].append({"step": "collect", "status": "done", "progress": 40})

        if not articles:
            job["status"] = "done"
            job["result"] = {
                "digest": "# ⚠️ Aucun article trouvé\n\nAucun article correspondant aux critères n'a été trouvé pour cette période.",
                "num_articles": 0,
                "period": period_type,
                "md_path": None,
            }
            job["steps"].append({"step": "analyze", "status": "done", "progress": 60})
            job["steps"].append({"step": "generate", "status": "done", "progress": 100})
            return

        # Step 2: Analyse
        job["steps"].append({"step": "analyze", "status": "active", "progress": 45})
        trends = agent.analyze_trends(articles)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 60})

        # Step 3: Generation
        job["steps"].append({"step": "generate", "status": "active", "progress": 65})
        result = agent.generate_digest(articles, trends, period=period_type)
        job["steps"].append({"step": "generate", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"tech_digest_{period_type}_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Veille Technologique {period_type.capitalize()}\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"**Période:** {days} derniers jours\n")
            f.write(f"**Articles:** {len(articles)}\n\n")
            f.write("---\n\n")
            f.write(result["content"])

        job["status"] = "done"
        job["result"] = {
            "digest": result["content"],
            "num_articles": len(articles),
            "period": period_type,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/techwatch/stream/{job_id}")
async def api_techwatch_stream(job_id: str):
    """Streame le progres de la génération de digest"""

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


@router.post("/api/techwatch/regenerate")
async def api_techwatch_regenerate(request: Request):
    """Regenere le digest avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_digest = body.get("previous_digest", "")
    num_articles = body.get("num_articles", 0)
    period = body.get("period", "weekly")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "techwatch",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_techwatch_feedback,
        args=(job_id, previous_digest, feedback, num_articles, period),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_techwatch_feedback(
    job_id: str, previous_digest: str, feedback: str, num_articles: int, period: str
):
    """Regenere le digest en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = TechMonitorAgent()

        job["steps"].append({"step": "collect", "status": "done", "progress": 20})
        job["steps"].append({"step": "analyze", "status": "done", "progress": 40})
        job["steps"].append({"step": "generate", "status": "active", "progress": 50})

        system_prompt = """Tu es {
            agent.consultant_info['name']}, {
            agent.consultant_info['title']} chez {
            agent.consultant_info['company']}.
Tu corriges un digest de veille technologique selon le retour du consultant."""

        # Regenerer le digest
        revised_digest = agent.llm_client.generate(
            prompt="""Voici un digest de veille technologique généré précédemment:

{previous_digest}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reécris ce digest en intégrant les corrections demandées.
Conserve le format Markdown avec emojis et la structure (Tendances, Articles clés, Insights, Sources).
Ne modifie que ce qui est demandé dans le feedback.""",
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=3000,
        )

        job["steps"].append({"step": "generate", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"tech_digest_{period}_{timestamp}_revised.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Veille Technologique {period.capitalize()} (Révisé)\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("---\n\n")
            f.write(revised_digest)

        job["status"] = "done"
        job["result"] = {
            "digest": revised_digest,
            "num_articles": num_articles,
            "period": period,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
