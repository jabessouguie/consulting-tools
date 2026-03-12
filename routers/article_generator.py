import asyncio
import re
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from routers.shared import (
    BASE_DIR,
    COMPANY_NAME,
    CONSULTANT_NAME,
    jobs,
    limiter,
    safe_error_message,
    send_sse,
    templates,
)

router = APIRouter()


@router.get("/article-generator", response_class=HTMLResponse)
async def article_generator_page(request: Request):
    return templates.TemplateResponse(
        "article-generator.html",
        {
            "request": request,
            "active": "article-generator",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/article-generator/generate")
@limiter.limit("5/minute")
async def api_article_generator_generate(
    request: Request,
    idea_text: str = Form(...),
    use_context: bool = Form(False),
):
    """Lance la génération d'un article de blog"""
    if len(idea_text.strip()) < 20:
        return JSONResponse(
            {"error": "L'idée est trop courte (minimum 20 caractères)."}, status_code=400
        )

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "article-generator",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_article_generator,
        args=(job_id, idea_text, use_context),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_article_generator(job_id: str, idea: str, use_context: bool = False):
    """Execute la generation d'article en background (4 etapes)"""
    job = jobs[job_id]

    try:
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()

        job["steps"].append({"step": "article", "status": "active", "progress": 10})

        # Pipeline complet (article + linkedin + image + sources)
        result = agent.run(idea, target_length="medium", use_context=use_context)

        job["steps"].append({"step": "article", "status": "done", "progress": 100})

        word_count = len(result["article"].split())

        job["status"] = "done"
        job["result"] = {
            "content": result["article"],
            "word_count": word_count,
            "md_path": result["article_path"],
            "illustration_prompt": result.get("illustration_prompt", ""),
            "linkedin_post": result.get("linkedin_post", ""),
            "image_path": result.get("image_path"),
            "sources": result.get("sources", []),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.get("/api/article-generator/stream/{job_id}")
async def api_article_generator_stream(job_id: str):
    """SSE stream pour la progression de la génération d'article"""

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


@router.post("/api/article-generator/regenerate")
async def api_article_generator_regenerate(request: Request):
    """Régénère l'article avec le feedback utilisateur"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_content = body.get("previous_content", "")
    previous_idea = body.get("previous_idea", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "article-generator",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_article_generator_feedback,
        args=(job_id, previous_content, feedback, previous_idea),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_article_generator_feedback(
    job_id: str, previous_content: str, feedback: str, previous_idea: str
):
    """Régénère l'article en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()

        job["steps"].append({"step": "generate", "status": "active", "progress": 20})

        revised_prompt = (
            previous_idea
            + "\n\nCONTEXTE : Voici l'article précédent que tu as généré:\n\n"
            + previous_content
            + "\n\nFEEDBACK de l'utilisateur:\n"
            + feedback
            + "\n\nRégénère l'article en tenant compte du feedback. Applique les modifications"
            " demandées tout en gardant le style et la qualité Consulting Tools."
        )

        revised_content = agent.generate_article(revised_prompt, target_length="medium")

        # Générer le nouveau prompt d'illustration
        illustration_prompt = agent.generate_illustration_prompt(revised_content)

        job["steps"].append({"step": "generate", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        slug = re.sub(r"[^\w\s-]", "", previous_idea.lower())
        slug = re.sub(r"[-\s]+", "-", slug)[:50]

        md_path = output_dir / f"article_{slug}_revised_{timestamp}.md"

        full_article = (
            "---\n"
            "title: " + previous_idea + "\n"
            "author: " + CONSULTANT_NAME + "\n"
            "company: " + COMPANY_NAME + "\n"
            "date: " + datetime.now().strftime("%Y-%m-%d") + "\n"
            "revised: true\n"
            "illustration_prompt: |\n"
            "  " + illustration_prompt + "\n"
            "---\n\n"
            + revised_content
            + "\n"
        )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_article)

        job["status"] = "done"
        job["result"] = {
            "content": revised_content,
            "word_count": len(revised_content.split()),
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "illustration_prompt": illustration_prompt,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)


@router.post("/api/article-generator/export-gdocs")
@limiter.limit("5/minute")
async def api_article_generator_export_gdocs(
    request: Request,
    content: str = Form(...),
    title: str = Form("Article de Blog"),
):
    """Exporte un article genere vers Google Docs avec formatage markdown"""
    try:
        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            doc_url = google_client.export_markdown_to_docs(content, title)

            if doc_url:
                return JSONResponse(
                    {"doc_url": doc_url, "message": "Article exporte vers Google Docs"}
                )
            else:
                return JSONResponse(
                    {"error": "Echec de la creation du document Google Docs"},
                    status_code=500,
                )

        except Exception as e:
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse(
                    {
                        "error": "Google API non configuree. Configurez vos credentials.",
                        "setup_required": True,
                    },
                    status_code=400,
                )
            else:
                raise

    except Exception as e:
        print(f"Erreur export article GDocs: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)
