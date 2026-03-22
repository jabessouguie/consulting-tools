import asyncio
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agents.linkedin_monitor import LinkedInMonitorAgent
from routers.shared import BASE_DIR, jobs, limiter, safe_error_message, send_sse

router = APIRouter()


@router.post("/api/linkedin/generate")
@limiter.limit("5/minute")
async def api_linkedin_generate(request: Request):
    """Lance la veille et generation de posts LinkedIn"""
    body = await request.json()
    post_type = body.get("post_type", "insight")
    num_posts = min(body.get("num_posts", 3), 5)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "linkedin",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_linkedin, args=(job_id, post_type, num_posts), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_linkedin(job_id: str, post_type: str, num_posts: int):
    """Execute la veille LinkedIn en background"""
    job = jobs[job_id]

    try:
        agent = LinkedInMonitorAgent()

        # Step 1: RSS
        job["steps"].append({"step": "rss", "status": "active", "progress": 5})
        monitoring_data = agent.collect_monitoring_data()
        job["steps"].append({"step": "rss", "status": "done", "progress": 30})
        job["steps"].append({"step": "web", "status": "done", "progress": 40})

        # Step 2: Trends
        job["steps"].append({"step": "trends", "status": "active", "progress": 45})
        trends = agent.analyze_trends(monitoring_data["articles"])
        job["steps"].append({"step": "trends", "status": "done", "progress": 60})

        # Step 3: Posts
        job["steps"].append({"step": "posts", "status": "active", "progress": 65})

        if num_posts == 1:
            posts = [agent.generate_linkedin_post(trends, monitoring_data["articles"], post_type)]
        else:
            posts = agent.generate_multiple_posts(trends, monitoring_data["articles"], num_posts)

        job["steps"].append({"step": "posts", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        for i, post in enumerate(posts, 1):
            md_path = output_dir / f"linkedin_post_{timestamp}_{i}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Post LinkedIn - {post['post_type'].title()}\n\n")
                f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
                f.write("## Post Principal\n\n")
                f.write(post["main_post"])

        job["status"] = "done"
        job["result"] = {
            "posts": [
                {
                    "main_post": p["main_post"],
                    "post_type": p["post_type"],
                    "source_articles": p.get("source_articles", []),
                }
                for p in posts
            ],
            "articles": [
                {
                    "title": a.get("title", ""),
                    "link": a.get("link", ""),
                    "source": a.get("source", a.get("source_type", "")),
                    "relevance_score": a.get("relevance_score", 0),
                }
                for a in monitoring_data["articles"][:20]
            ],
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/linkedin/stream/{job_id}")
async def api_linkedin_stream(job_id: str):
    """SSE stream pour la progression LinkedIn"""

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


@router.post("/api/linkedin/regenerate")
async def api_linkedin_regenerate(request: Request):
    """Regenere les posts LinkedIn avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_posts = body.get("previous_posts", [])

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "linkedin",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_linkedin_feedback,
        args=(job_id, previous_posts, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_linkedin_feedback(job_id: str, previous_posts: list, feedback: str):
    """Regenere les posts LinkedIn en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = LinkedInMonitorAgent()

        job["steps"].append({"step": "rss", "status": "done", "progress": 10})
        job["steps"].append({"step": "web", "status": "done", "progress": 20})
        job["steps"].append({"step": "trends", "status": "done", "progress": 30})
        job["steps"].append({"step": "posts", "status": "active", "progress": 40})

        revised_posts = []
        for i, post in enumerate(previous_posts):
            revised = agent.llm_client.generate(
                prompt="""Voici un post LinkedIn genere precedemment:

{
                    post.get(
                        'main_post',
                        '')}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce post en integrant les corrections demandees.
Conserve le format LinkedIn (hook, contenu, question d'engagement, hashtags).
Ne modifie que ce qui est demande dans le feedback.""",
                system_prompt="""Tu es {
                    agent.consultant_info['name']}, {
                    agent.consultant_info['title']} chez {
                        agent.consultant_info['company']}.
Tu corriges un post LinkedIn selon le retour du consultant.

REGLES IMPERATIVES:
- Ne JAMAIS inventer d'anecdotes, d'exemples fictifs ou d'experiences personnelles
- Ne JAMAIS fabriquer de chiffres, statistiques ou citations""",
                temperature=0.6,
                max_tokens=1500,
            )
            revised_posts.append(
                {
                    "main_post": revised,
                    "post_type": post.get("post_type", "insight"),
                    "source_articles": post.get("source_articles", []),
                }
            )

        job["steps"].append({"step": "posts", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "posts": revised_posts,
            "articles": [],
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.post("/api/linkedin/publish")
@limiter.limit("5/minute")
async def api_linkedin_publish(request: Request):
    """Publie un post directement sur LinkedIn"""
    from utils.linkedin_client import LinkedInClient, has_linkedin_access_token
    from utils.validation import sanitize_text_input

    # Check if LinkedIn is configured
    if not has_linkedin_access_token():
        return JSONResponse(
            {"error": "LinkedIn non configure. Completez le flux OAuth via /auth/linkedin"},
            status_code=400,
        )

    body = await request.json()
    text = body.get("text", "").strip()
    visibility = body.get("visibility", "PUBLIC")

    # Validate
    if not text:
        return JSONResponse({"error": "Texte du post manquant"}, status_code=400)

    # Sanitize and validate length
    try:
        text = sanitize_text_input(text, max_length=3000, field_name="post")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    if visibility not in ["PUBLIC", "CONNECTIONS"]:
        visibility = "PUBLIC"

    try:
        client = LinkedInClient()
        result = client.publish_post(text=text, visibility=visibility)

        return JSONResponse(
            {
                "message": "Post publie avec succes sur LinkedIn",
                "id": result.get("id"),
                "url": result.get("url"),
                "status": result.get("status"),
            }
        )

    except ValueError as e:
        return JSONResponse(
            {"error": f"Erreur de configuration: {safe_error_message(e)}"}, status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Erreur lors de la publication: {safe_error_message(e)}"}, status_code=500
        )


@router.get("/api/linkedin/status")
async def api_linkedin_status():
    """Verifie le status de connexion LinkedIn"""
    from utils.linkedin_client import has_linkedin_access_token

    return JSONResponse({"connected": has_linkedin_access_token()})
