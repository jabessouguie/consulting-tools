import asyncio
import json
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from agents.linkedin_commenter import LinkedInCommenterAgent
from routers.shared import BASE_DIR, CONSULTANT_NAME, jobs, limiter, safe_error_message, templates

router = APIRouter()


@router.get("/comment", response_class=HTMLResponse)
async def comment_page(request: Request):
    return templates.TemplateResponse(
        "comment.html",
        {
            "request": request,
            "active": "comment",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/comment/generate")
@limiter.limit("10/minute")
async def api_comment_generate(request: Request):
    """Lance la generation de commentaires LinkedIn"""
    body = await request.json()
    post_input = body.get("post_input", "").strip()
    style = body.get("style", "insightful")

    if not post_input:
        return JSONResponse({"error": "Post LinkedIn manquant."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "comment",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_comment_generator, args=(job_id, post_input, style), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_comment_generator(job_id: str, post_input: str, style: str):
    """Execute la generation de commentaires en background"""
    job = jobs[job_id]

    try:
        agent = LinkedInCommenterAgent()

        # Step 1: Extraction
        job["steps"].append({"step": "extract", "status": "active", "progress": 10})
        post_content = agent.extract_post_content(post_input)
        job["steps"].append({"step": "extract", "status": "done", "progress": 35})

        # Step 2: Generation
        job["steps"].append({"step": "generate", "status": "active", "progress": 40})
        result = agent.generate_comments(post_content, style=style)
        job["steps"].append({"step": "generate", "status": "done", "progress": 90})

        # Step 3: Sauvegarde
        job["steps"].append({"step": "save", "status": "active", "progress": 95})
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"linkedin_comment_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Commentaires LinkedIn\n\n")
            f.write(f"**Style:** {style}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("## Post original (extrait)\n\n")
            f.write(f"> {result['post_preview']}\n\n")
            f.write("---\n\n")
            f.write("## Commentaire Court\n\n")
            f.write(result["short"])
            f.write("\n\n---\n\n## Commentaire Moyen\n\n")
            f.write(result["medium"])
            f.write("\n\n---\n\n## Commentaire Long\n\n")
            f.write(result["long"])
            f.write("\n")

        job["steps"].append({"step": "save", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "short": result["short"],
            "medium": result["medium"],
            "long": result["long"],
            "post_preview": result["post_preview"],
            "style": style,
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/comment/stream/{job_id}")
async def api_comment_stream(job_id: str):
    """Streame le progres de la generation de commentaires"""

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


@router.post("/api/comment/regenerate")
async def api_comment_regenerate(request: Request):
    """Regenere les commentaires avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_short = body.get("previous_short", "")
    previous_medium = body.get("previous_medium", "")
    previous_long = body.get("previous_long", "")
    post_preview = body.get("post_preview", "")
    style = body.get("style", "insightful")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "comment",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_comment_feedback,
        args=(
            job_id,
            previous_short,
            previous_medium,
            previous_long,
            feedback,
            post_preview,
            style,
        ),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_comment_feedback(
    job_id: str,
    previous_short: str,
    previous_medium: str,
    previous_long: str,
    feedback: str,
    post_preview: str,
    style: str,
):
    """Regenere les commentaires en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = LinkedInCommenterAgent()

        job["steps"].append({"step": "extract", "status": "done", "progress": 10})
        job["steps"].append({"step": "generate", "status": "active", "progress": 30})

        # Charger le persona
        persona_path = BASE_DIR / "data" / "linkedin_persona.md"
        persona_style = ""
        if persona_path.exists():
            persona_content = persona_path.read_text(encoding="utf-8")
            start_idx = persona_content.find("### ✨ Ton & Style")
            end_idx = persona_content.find("### 📝 Structure de posts")
            if start_idx != -1 and end_idx != -1:
                persona_style = (
                    "\n\nSTYLE 'PARISIEN GENZ' A APPLIQUER:\n" + persona_content[start_idx:end_idx]
                )

        system_prompt = """Tu es {
            agent.consultant_info['name']}, {
            agent.consultant_info['title']} chez {
            agent.consultant_info['company']}.
Base : Paris | Génération Z assumée
{persona_style}

Tu corriges des commentaires LinkedIn selon le feedback de l'utilisateur."""

        # Regenerer commentaire court
        revised_short = agent.llm_client.generate(
            prompt="""Voici un commentaire court genere precedemment pour ce post:

POST ORIGINAL:
{post_preview}

COMMENTAIRE COURT PRECEDENT:
{previous_short}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce commentaire court (50-150 caracteres) en integrant les corrections demandees.
Reste specifique au post. Apporte de la valeur. Ton Parisien GenZ.""",
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200,
        )

        # Regenerer commentaire moyen
        revised_medium = agent.llm_client.generate(
            prompt="""Voici un commentaire moyen genere precedemment pour ce post:

POST ORIGINAL:
{post_preview}

COMMENTAIRE MOYEN PRECEDENT:
{previous_medium}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce commentaire moyen (150-300 caracteres) en integrant les corrections demandees.
Reste specifique au post. Apporte de la valeur. Ton Parisien GenZ.""",
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=400,
        )

        # Regenerer commentaire long
        revised_long = agent.llm_client.generate(
            prompt="""Voici un commentaire long genere precedemment pour ce post:

POST ORIGINAL:
{post_preview}

COMMENTAIRE LONG PRECEDENT:
{previous_long}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce commentaire long (300-500 caracteres) en integrant les corrections demandees.
Reste specifique au post. Apporte de la valeur. Ton Parisien GenZ.""",
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=600,
        )

        job["steps"].append({"step": "generate", "status": "done", "progress": 90})

        # Sauvegarde
        job["steps"].append({"step": "save", "status": "active", "progress": 95})
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"linkedin_comment_{timestamp}_revised.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Commentaires LinkedIn (Révisés)\n\n")
            f.write(f"**Style:** {style}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("## Post original (extrait)\n\n")
            f.write(f"> {post_preview}\n\n")
            f.write("---\n\n")
            f.write("## Commentaire Court\n\n")
            f.write(revised_short)
            f.write("\n\n---\n\n## Commentaire Moyen\n\n")
            f.write(revised_medium)
            f.write("\n\n---\n\n## Commentaire Long\n\n")
            f.write(revised_long)
            f.write("\n")

        job["steps"].append({"step": "save", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "short": revised_short,
            "medium": revised_medium,
            "long": revised_long,
            "post_preview": post_preview,
            "style": style,
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
