"""Router: Document Editor, Veille Technologique et Bug Reports"""

import asyncio
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from routers.shared import (
    BASE_DIR,
    jobs,
    limiter,
    templates,
    CONSULTANT_NAME,
    safe_error_message,
    send_sse,
)
from utils.validation import sanitize_text_input

router = APIRouter()

BUG_REPORTS_FILE = Path("data/bug_reports.json")


def _load_bug_reports():
    if BUG_REPORTS_FILE.exists():
        with open(BUG_REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_bug_reports(reports):
    BUG_REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BUG_REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)


# === DOCUMENT EDITOR ===


@router.get("/document-editor", response_class=HTMLResponse)
async def document_editor_page(request: Request):
    return templates.TemplateResponse(
        "document-editor.html",
        {
            "request": request,
            "active": "document-editor",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.get("/veille", response_class=HTMLResponse)
async def veille_page(request: Request):
    return templates.TemplateResponse(
        "veille.html",
        {
            "request": request,
            "active": "veille",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/document-editor/start-generate")
@limiter.limit("10/minute")
async def api_document_editor_start_generate(request: Request):
    """Demarre la generation de document en arriere-plan"""
    data = await request.json()
    doc_type = data.get("type", "formation")

    # Valider et sanitizer les inputs texte
    topic = sanitize_text_input(data.get("topic", ""), max_length=1000, field_name="topic")
    document_text = sanitize_text_input(
        data.get("document_text", ""), max_length=50000, field_name="document_text"
    )
    audience = sanitize_text_input(data.get("audience", ""), max_length=500, field_name="audience")
    feedback = sanitize_text_input(data.get("feedback", ""), max_length=5000, field_name="feedback")
    previous_content = sanitize_text_input(
        data.get("previous_content", ""), max_length=50000, field_name="previous_content"
    )

    length = data.get("length", "medium")
    model = data.get("model", "")
    use_context = data.get("use_context", False)

    _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _uid = id(data) % 10000
    job_id = f"doc_{_ts}_{_uid}"

    jobs[job_id] = {
        "type": "document-editor",
        "status": "running",
        "steps": [],
        "chunks": [],
        "result": None,
        "error": None,
    }

    def run_doc_generation():
        job = jobs[job_id]
        try:
            job["steps"].append({"message": "Initialisation du modele..."})

            from utils.llm_client import LLMClient

            llm_kwargs = {"max_tokens": 8192}
            if model:
                llm_kwargs["model"] = model
                llm_kwargs["provider"] = "gemini"

            result = {"markdown": "", "linkedin_post": ""}

            if feedback and previous_content:
                # Regeneration with feedback
                job["steps"].append({"message": "Application du feedback..."})

                if doc_type == "formation":
                    from agents.formation_generator import FormationGeneratorAgent

                    agent = FormationGeneratorAgent()
                    if model:
                        agent.llm = LLMClient(**llm_kwargs)
                    gen_result = agent.regenerate_with_feedback(previous_content, feedback)
                    result["markdown"] = gen_result.get("markdown", "")
                else:
                    # Article or REX text: generic LLM regeneration
                    llm = LLMClient(**llm_kwargs)
                    system_prompt = "Tu es un expert en redaction chez Consulting Tools. Tu dois modifier un document existant en tenant compte du feedback utilisateur. Conserve la structure markdown et ameliore le contenu."
                    prompt = f"""Voici le document actuel :
---
{previous_content[:6000]}
---

Feedback utilisateur :
---
{feedback}
---

Modifie le document en tenant compte du feedback. Retourne UNIQUEMENT le document markdown modifie, sans explication."""

                    # Stream response progressively
                    buffer = ""
                    try:
                        for chunk in llm.generate_stream(
                            prompt=prompt, system_prompt=system_prompt, temperature=0.7
                        ):
                            buffer += chunk
                            job["chunks"].append(chunk)
                    except Exception:
                        buffer = llm.generate(
                            prompt=prompt, system_prompt=system_prompt, temperature=0.7
                        )
                        job["chunks"].append(buffer)

                    response = buffer.strip()
                    if response.startswith("```markdown"):
                        response = response[len("```markdown"):]
                    if response.startswith("```"):
                        response = response[3:]
                    if response.endswith("```"):
                        response = response[:-3]
                    result["markdown"] = response.strip()

            elif doc_type == "formation":
                job["steps"].append({"message": "Generation du programme de formation..."})
                from agents.formation_generator import FormationGeneratorAgent

                agent = FormationGeneratorAgent()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)
                input_text = topic
                if document_text:
                    input_text += f"\n\nDocument source :\n{document_text[:6000]}"
                if audience:
                    input_text += f"\n\nPublic cible : {audience}"
                gen_result = agent.generate_programme(input_text)
                result["markdown"] = gen_result.get("markdown", "")

            elif doc_type == "article":
                job["steps"].append({"message": "Generation de l'article..."})
                from agents.article_generator import ArticleGeneratorAgent

                agent = ArticleGeneratorAgent()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)
                idea = topic
                if document_text:
                    idea += f"\n\nDocument source :\n{document_text[:4000]}"
                gen_result = agent.run(idea, target_length=length, use_context=use_context)
                result["markdown"] = gen_result.get("article", "")
                result["linkedin_post"] = gen_result.get("linkedin_post", "")

            elif doc_type == "rex_text":
                job["steps"].append({"message": "Generation du REX..."})
                llm = LLMClient(**llm_kwargs)

                company_name = os.getenv("COMPANY_NAME", "Consulting Tools")
                system_prompt = f"""Tu es un consultant senior chez {company_name} qui redige un Retour d Experience (REX) de mission.

TON STYLE :
- Factuel et professionnel, oriente resultats
- Chiffres concrets (KPIs, delais, gains, ROI)
- Structure claire en sections markdown
- Pragmatique et pedagogique

FORMAT MARKDOWN :
- # pour le titre principal
- ## pour les sections
- ### pour les sous-sections
- **Gras** pour les points cles
- Listes a puces pour les enumerations
- > Citations pour les temoignages clients
- Tableaux pour les KPIs et les plannings"""

                doc_section = ""
                if document_text:
                    doc_section = f"\n\nDocument source :\n{document_text[:6000]}"

                prompt = f"""Redige un Retour d Experience (REX) complet de mission en markdown.

MISSION : {topic or 'Mission basee sur le document fourni'}
CLIENT / CONTEXTE : {audience or 'Client entreprise'}
{doc_section}

### STRUCTURE OBLIGATOIRE :
1. **Titre** (H1) : REX Mission - [Nom]
2. **Contexte** (H2) : client, secteur, contexte de la mission
3. **Enjeux & Objectifs** (H2) : problematique, objectifs mesurables
4. **Demarche** (H2) : phases, methodologie, planning
5. **Realisations** (H2) : livrables, actions menees
6. **Resultats** (H2) : KPIs, metriques, gains (utilise un tableau)
7. **Apprentissages** (H2) : ce qui a marche, axes d amelioration
8. **Recommandations** (H2) : prochaines etapes, conseils
9. **Conclusion** (H2) : synthese

Retourne UNIQUEMENT le document markdown, sans preambule."""

                # Stream response progressively
                buffer = ""
                try:
                    for chunk in llm.generate_stream(
                        prompt=prompt, system_prompt=system_prompt, temperature=0.7
                    ):
                        buffer += chunk
                        job["chunks"].append(chunk)
                except Exception:
                    buffer = llm.generate(
                        prompt=prompt, system_prompt=system_prompt, temperature=0.7
                    )
                    job["chunks"].append(buffer)

                response = buffer.strip()
                if response.startswith("```markdown"):
                    response = response[len("```markdown"):]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                result["markdown"] = response.strip()

            elif doc_type == "linkedin":
                job["steps"].append({"message": "Generation du post LinkedIn..."})
                llm = LLMClient(**llm_kwargs)
                consultant_name = os.getenv("CONSULTANT_NAME", "Jean-Sebastien Abessouguie Bayiha")
                company_name = os.getenv("COMPANY_NAME", "Consulting Tools")

                system_prompt = f"""Tu es {consultant_name}, consultant en strategie data et IA chez {company_name}.
Tu rediges des posts LinkedIn engageants, pragmatiques, orientes resultats, avec une vision critique et constructive.
Style : gen z parisien, oriente resultats, a contre-courant des buzzwords.

STRUCTURE DU POST :
1. Accroche percutante (question provocatrice ou constat surprenant)
2. Corps : 2-3 phrases claires resumant ton point de vue
3. Call to action : question ouverte pour les commentaires
4. 5 hashtags strategiques

REGLES :
- Maximum 1300 caracteres
- Paragraphes courts (1-2 phrases max)
- Pas de emojis excessifs (max 2-3)
- Ton direct et authentique"""

                doc_section = ""
                if document_text:
                    doc_section = f"\n\nContenu source :\n{document_text[:4000]}"

                prompt = f"""Redige un post LinkedIn sur le sujet suivant :

{topic or 'Sujet base sur le document fourni'}
{doc_section}

Retourne UNIQUEMENT le texte du post, sans explication."""

                # Stream response progressively
                buffer = ""
                try:
                    for chunk in llm.generate_stream(
                        prompt=prompt, system_prompt=system_prompt, temperature=0.7
                    ):
                        buffer += chunk
                        job["chunks"].append(chunk)
                except Exception:
                    buffer = llm.generate(
                        prompt=prompt, system_prompt=system_prompt, temperature=0.7
                    )
                    job["chunks"].append(buffer)

                response = buffer.strip()
                if response.startswith("```"):
                    response = response.split("```", 1)[1]
                    if response.startswith("\n"):
                        response = response[1:]
                    if "```" in response:
                        response = response.rsplit("```", 1)[0]
                result["markdown"] = response.strip()

            elif doc_type == "compte_rendu":
                job["steps"].append({"message": "Analyse du transcript..."})
                from agents.meeting_summarizer import MeetingSummarizerAgent

                agent = MeetingSummarizerAgent()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)

                transcript = topic
                if document_text:
                    transcript += f"\n\n{document_text}"

                # Extract key info
                info_result = agent.extract_key_info(transcript)
                extracted_info = info_result.get("extracted_info", "")

                job["steps"].append({"message": "Generation du compte rendu..."})
                minutes = agent.generate_minutes(transcript, extracted_info)

                job["steps"].append({"message": "Generation de l'email de partage..."})
                email_result = agent.generate_email(extracted_info, minutes)

                result["markdown"] = minutes
                result["email"] = email_result

            elif doc_type == "cv_reference":
                job["steps"].append({"message": "Adaptation du CV/Reference..."})

                from agents.cv_reference_adapter import CVReferenceAdapterAgent

                agent = CVReferenceAdapterAgent()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)

                # Detecter automatiquement si c est un CV ou une reference
                is_cv = any(
                    kw in document_text.lower()
                    for kw in [
                        "experience",
                        "competences",
                        "formation",
                        "cv",
                        "consultant",
                        "diplome",
                        "certification",
                        "parcours professionnel",
                    ]
                )
                type_label = "CV" if is_cv else "Reference"

                job["steps"].append({"message": f"Generation des slides {type_label}..."})

                gen_result = agent.run(
                    document_text=document_text,
                    mission_brief=topic,  # Le "topic" = l appel d offre
                    doc_type=type_label,
                )

                # Retourner slides au lieu de markdown
                job["slides"] = gen_result.get("slides", [])
                result["slides"] = gen_result.get("slides", [])
                result["doc_type"] = type_label

            elif doc_type == "presentation_script":
                job["steps"].append({"message": "Extraction du contenu PPTX..."})

                # document_text contient le chemin vers le fichier PPTX temporaire
                if not document_text or not document_text.endswith(".pptx"):
                    raise ValueError(
                        "Fichier PPTX obligatoire pour generer un script de presentation"
                    )

                from agents.presentation_script_generator import PresentationScriptGenerator

                agent = PresentationScriptGenerator()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)

                job["steps"].append({"message": "Analyse des slides..."})

                # Stream chunks si possible
                gen_result = agent.run(pptx_path=document_text, presentation_context=topic or "")

                result["markdown"] = gen_result.get("markdown", "")
                result["num_slides"] = gen_result.get("num_slides", 0)
                result["estimated_duration"] = gen_result.get("estimated_duration", "")

            job["result"] = result
            job["status"] = "done"
            job["steps"].append({"message": "Generation terminee !"})

        except Exception as e:
            print(f"Erreur document-editor generate: {e}")
            import traceback

            traceback.print_exc()
            job["error"] = safe_error_message(e)
            job["status"] = "error"

    threading.Thread(target=run_doc_generation, daemon=True).start()

    return {"job_id": job_id}


@router.get("/api/document-editor/stream/{job_id}")
async def api_document_editor_stream(job_id: str):
    """SSE stream pour la progression de generation de document"""

    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouve"})
            return

        last_step_idx = 0
        last_chunk_idx = 0

        while True:
            # Send new steps
            while last_step_idx < len(job["steps"]):
                step = job["steps"][last_step_idx]
                yield send_sse("status", step)
                last_step_idx += 1

            # Send new chunks progressively
            chunks = job.get("chunks", [])
            while last_chunk_idx < len(chunks):
                yield send_sse("chunk", {"text": chunks[last_chunk_idx]})
                last_chunk_idx += 1

            if job["status"] == "done":
                yield send_sse("result", job["result"])
                return

            if job["status"] == "error":
                yield send_sse("error_msg", {"message": job["error"]})
                return

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/document-editor/export-gdocs")
async def api_document_editor_export_gdocs(request: Request):
    """Exporte le markdown vers Google Docs"""
    try:
        data = await request.json()
        markdown = data.get("markdown", "")
        title = data.get("title", "Document Consulting Tools")

        if not markdown:
            return JSONResponse({"error": "Pas de contenu a exporter"}, status_code=400)

        from utils.google_api import GoogleAPIClient

        client = GoogleAPIClient()
        url = client.export_markdown_to_docs(markdown, title)

        return {"url": url}
    except Exception as e:
        print(f"Erreur export Google Docs: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


# ===== VEILLE TECHNOLOGIQUE =====


@router.get("/api/veille/articles")
async def api_veille_get_articles(
    limit: int = 50,
    offset: int = 0,
    source: str = None,
    keyword: str = None,
    days: int = None,
):
    """Liste les articles de veille avec filtres"""
    try:
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()

        articles = db.get_articles(
            limit=limit, offset=offset, source=source, keyword=keyword, days=days
        )

        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        print(f"Erreur lecture articles: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


@router.get("/api/veille/stats")
async def api_veille_stats():
    """Statistiques sur les articles stockes"""
    try:
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()
        stats = db.get_article_stats()
        return stats
    except Exception as e:
        print(f"Erreur stats: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


@router.post("/api/veille/generate-digest")
async def api_veille_generate_digest(request: Request):
    """Genere un nouveau digest de veille"""
    try:
        data = await request.json()
        period = data.get("period", "daily")
        days = data.get("days", 1 if period == "daily" else 7)
        keywords = data.get("keywords", [])

        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()

        result = agent.run(keywords=keywords if keywords else None, days=days, period=period)

        return {
            "success": True,
            "digest": result.get("content", result.get("digest", "")),
            "num_articles": result.get("num_articles", 0),
            "digest_id": result.get("digest_id"),
            "md_path": result.get("md_path"),
        }
    except Exception as e:
        print(f"Erreur generation digest: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


@router.get("/api/veille/digests")
async def api_veille_get_digests(period: str = "daily"):
    """Liste les digests generes"""
    try:
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()

        # Recuperer le dernier digest de cette periode
        latest = db.get_latest_digest(period=period)

        return {"latest_digest": latest}
    except Exception as e:
        print(f"Erreur lecture digests: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


@router.post("/api/veille/articles/{article_id}/mark-read")
async def api_veille_mark_read(article_id: int):
    """Marque un article comme lu"""
    try:
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()
        db.mark_as_read(article_id)
        return {"success": True}
    except Exception as e:
        print(f"Erreur mark read: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


@router.post("/api/veille/articles/{article_id}/toggle-favorite")
async def api_veille_toggle_favorite(article_id: int):
    """Toggle favori sur un article"""
    try:
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()
        db.toggle_favorite(article_id)
        return {"success": True}
    except Exception as e:
        print(f"Erreur toggle favorite: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)


# === BUG REPORTS ===


@router.post("/api/bug-report")
async def api_bug_report(request: Request):
    """Enregistre un signalement de bug"""
    try:
        data = await request.json()
        description = data.get("description", "").strip()
        if not description:
            return JSONResponse({"error": "La description est requise"}, status_code=400)

        severity = data.get("severity", "medium")
        if severity not in ("low", "medium", "high", "critical"):
            severity = "medium"

        page_url = data.get("page_url", "")
        user_agent = data.get("user_agent", "")
        screenshot = data.get("screenshot", "")

        # Generate title with LLM
        title = description[:80]
        try:
            from utils.llm_client import LLMClient

            llm = LLMClient(model="gemini-2.0-flash", provider="gemini", max_tokens=100)
            title = (
                llm.generate_with_context(
                    f"Genere un titre court (max 10 mots) pour ce bug: {description}",
                    system_prompt=(
                        "Tu generes des titres de bug concis en francais. "
                        "Reponds uniquement avec le titre, sans guillemets."
                    ),
                )
                .strip()
                .strip('"')
                .strip("'")
            )
        except Exception:
            pass

        report_id = str(uuid.uuid4())[:8]
        report = {
            "id": report_id,
            "title": title,
            "description": description,
            "severity": severity,
            "page_url": page_url,
            "user_agent": user_agent,
            "screenshot": screenshot[:100] if screenshot else "",
            "has_screenshot": bool(screenshot),
            "created_at": datetime.now().isoformat(),
        }

        reports = _load_bug_reports()
        reports.append(report)
        _save_bug_reports(reports)

        return {"success": True, "id": report_id, "title": title}

    except Exception as e:
        print(f"Erreur bug report: {e}")
        return JSONResponse({"error": safe_error_message(e)}, status_code=500)
