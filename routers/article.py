import asyncio
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from agents.article_to_post import ArticleToPostAgent
from routers.shared import BASE_DIR, CONSULTANT_NAME, jobs, safe_error_message, send_sse, templates

router = APIRouter()


@router.get("/article", response_class=HTMLResponse)
async def article_page(request: Request):
    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "active": "article",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/article/generate")
async def api_article_generate(request: Request):
    """Lance la generation d'un post a partir d'un article"""
    body = await request.json()
    url = body.get("url", "").strip()
    tone = body.get("tone", "expert")

    if not url:
        return JSONResponse({"error": "URL manquante."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "article",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(target=_run_article_to_post, args=(job_id, url, tone), daemon=True)
    thread.start()

    return {"job_id": job_id}


def _run_article_to_post(job_id: str, url: str, tone: str):
    """Execute la generation de post depuis un article en background"""
    job = jobs[job_id]

    try:
        agent = ArticleToPostAgent()

        # Step 1: Fetch
        job["steps"].append({"step": "fetch", "status": "active", "progress": 10})
        article = agent.fetch_article(url)
        job["steps"].append({"step": "fetch", "status": "done", "progress": 30})

        # Step 2: Generate main post
        job["steps"].append({"step": "generate", "status": "active", "progress": 40})
        result = agent.generate_post(article, tone=tone)
        job["steps"].append({"step": "generate", "status": "done", "progress": 80})

        # Step 3: Done (variant already generated inside generate_post)
        job["steps"].append({"step": "variant", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"article_post_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Post LinkedIn - Partage d'article\n\n")
            f.write(f"**Article:** [{article['title']}]({url})\n")
            f.write(f"**Ton:** {tone}\n\n## Post Principal\n\n")
            f.write(result["main_post"])
            f.write("\n\n---\n\n## Version Courte\n\n")
            f.write(result["short_version"])

        job["status"] = "done"
        job["result"] = {
            "main_post": result["main_post"],
            "short_version": result["short_version"],
            "article_title": article["title"],
            "article_url": url,
            "tone": tone,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/article/stream/{job_id}")
async def api_article_stream(job_id: str):
    """SSE stream pour la progression article-to-post"""

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


@router.post("/api/article/regenerate")
async def api_article_regenerate(request: Request):
    """Regenere le post article avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_main = body.get("previous_main", "")
    previous_short = body.get("previous_short", "")
    article_url = body.get("article_url", "")
    tone = body.get("tone", "expert")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "article",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_article_feedback,
        args=(job_id, previous_main, previous_short, feedback, article_url, tone),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_article_feedback(
    job_id: str, previous_main: str, previous_short: str, feedback: str, article_url: str, tone: str
):
    """Regenere le post article en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = ArticleToPostAgent()

        job["steps"].append({"step": "fetch", "status": "done", "progress": 10})
        job["steps"].append({"step": "generate", "status": "active", "progress": 30})

        # Regenerer le post principal
        revised_main = agent.llm_client.generate(
            prompt="""Voici un post LinkedIn genere precedemment pour partager un article:

{previous_main}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce post en integrant les corrections demandees.
Conserve le format LinkedIn (hook, perspective, points cles, appel a l'action, hashtags).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt="""Tu es {
                agent.consultant_info['name']}, {
                agent.consultant_info['title']} chez {
                agent.consultant_info['company']}.
Tu corriges un post LinkedIn selon le retour du consultant.

REGLES IMPERATIVES:
- Base-toi UNIQUEMENT sur le contenu de l'article. Ne fabrique aucun fait, chiffre ou exemple.
- Ne JAMAIS inventer d'anecdotes personnelles ou d'experiences fictives""",
            temperature=0.6,
            max_tokens=1500,
        )

        job["steps"].append({"step": "generate", "status": "done", "progress": 70})
        job["steps"].append({"step": "variant", "status": "active", "progress": 75})

        # Regenerer la version courte
        revised_short = agent.llm_client.generate(
            prompt="""A partir de ce post LinkedIn revise, cree une version courte (400-600 caracteres max) qui va droit au point.

Post revise:
{revised_main}

Garde le hook et la question finale, compresse le milieu.
NE PAS inventer d'anecdotes ou d'exemples.""",
            system_prompt="""Tu es {
                agent.consultant_info['name']}, {
                agent.consultant_info['title']} chez {
                agent.consultant_info['company']}.""",
            temperature=0.6,
            max_tokens=600,
        )

        job["steps"].append({"step": "variant", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "main_post": revised_main,
            "short_version": revised_short,
            "article_url": article_url,
            "tone": tone,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
