"""Router: TenderScout AI — Scan, analyse et notification d'appels d'offres"""

import asyncio
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse, RedirectResponse

from agents.tender_scout_agent import (
    AnalysisError,
    ScrapingError,
    TenderScoutAgent,
    build_consultant_context,
)
from agents.meeting_capture_agent import DraftCreationError, MeetingGmailClient
from utils.tender_db import TenderDatabase
from utils.validation import sanitize_text_input
from utils.auth import get_current_user

from routers.shared import (
    BASE_DIR,
    jobs,
    limiter,
    templates,
    CONSULTANT_NAME,
    safe_error_message,
    send_sse,
)

router = APIRouter()


@router.get("/tenderscout", response_class=HTMLResponse)
async def tenderscout_page(request: Request):
    """Page TenderScout AI"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "tenderscout.html",
        {
            "request": request,
            "active": "tenderscout",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.post("/api/tenderscout/scan")
@limiter.limit("10/minute")
async def api_tenderscout_scan(request: Request):
    """Lance un scan d'appels d'offres en arrière-plan"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Corps JSON invalide"}, status_code=400)

    keywords = body.get("keywords", [])
    sources = body.get("sources", [])

    if not keywords or not isinstance(keywords, list):
        return JSONResponse(
            {"detail": "Le champ 'keywords' est requis et doit être une liste non vide."},
            status_code=400,
        )
    keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    if not keywords:
        return JSONResponse(
            {"detail": "Aucun mot-clé valide fourni."},
            status_code=400,
        )

    if not sources or not isinstance(sources, list):
        return JSONResponse(
            {"detail": "Le champ 'sources' est requis."},
            status_code=400,
        )

    from agents.tender_scout_agent import VALID_SOURCES

    invalid = [s for s in sources if s not in VALID_SOURCES]
    if invalid:
        return JSONResponse(
            {
                "detail": f"Sources invalides : {invalid}. Valeurs acceptées : {sorted(VALID_SOURCES)}."
            },
            status_code=400,
        )

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "tenderscout",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_tender_scout,
        args=(job_id, keywords, sources),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_tender_scout(job_id: str, keywords: list, sources: list):
    """Exécute le scan TenderScout en arrière-plan"""
    job = jobs[job_id]
    db = TenderDatabase()
    consultant_profile = build_consultant_context()
    agent = TenderScoutAgent(consultant_profile=consultant_profile)
    all_tenders = []

    try:
        # Étape 1 : scraping BOAMP
        if "boamp" in sources:
            job["steps"].append(
                {
                    "step": "scrape_boamp",
                    "status": "active",
                    "progress": 10,
                    "message": "Scraping BOAMP…",
                }
            )
            boamp_tenders = agent.scrape_boamp(keywords)
            all_tenders.extend(boamp_tenders)
            job["steps"].append(
                {
                    "step": "scrape_boamp",
                    "status": "done",
                    "progress": 30,
                    "message": f"{len(boamp_tenders)} AOs trouvés sur BOAMP",
                }
            )

        # Étape 2 : scraping Francemarches
        if "francemarches" in sources:
            job["steps"].append(
                {
                    "step": "scrape_francemarches",
                    "status": "active",
                    "progress": 35,
                    "message": "Scraping Francemarches.com…",
                }
            )
            fm_tenders = agent.scrape_francemarches(keywords)
            all_tenders.extend(fm_tenders)
            job["steps"].append(
                {
                    "step": "scrape_francemarches",
                    "status": "done",
                    "progress": 50,
                    "message": f"{len(fm_tenders)} AOs trouvés sur Francemarches",
                }
            )

        # Étape 3 : sauvegarde idempotente
        job["steps"].append(
            {"step": "save", "status": "active", "progress": 52, "message": "Sauvegarde en base…"}
        )
        new_count = db.save_tenders(all_tenders)
        job["steps"].append(
            {
                "step": "save",
                "status": "done",
                "progress": 55,
                "message": f"{new_count} nouveau(x) AO(s) enregistré(s)",
            }
        )

        # Étape 4 : analyse Gemini des nouveaux AOs
        refs = [t["reference"] for t in all_tenders]
        unanalyzed_refs = set(db.get_unanalyzed_references(refs))
        to_analyze = [t for t in all_tenders if t["reference"] in unanalyzed_refs]

        analyzed_count = 0
        for i, tender in enumerate(to_analyze):
            progress = 55 + int(40 * (i + 1) / max(len(to_analyze), 1))
            job["steps"].append(
                {
                    "step": "analyze",
                    "status": "active",
                    "progress": progress,
                    "tender": tender["titre"][:60],
                    "message": f"Analyse {i + 1}/{len(to_analyze)}",
                }
            )
            try:
                analysis = agent.analyze_tender(tender)
                db.update_analysis(tender["reference"], analysis)
                analyzed_count += 1
                job["steps"][-1]["status"] = "done"
            except AnalysisError:
                job["steps"][-1]["status"] = "done"

        job["steps"].append(
            {"step": "done", "status": "done", "progress": 100, "message": "Analyse terminée"}
        )
        job["status"] = "done"
        job["result"] = {
            "total": len(all_tenders),
            "new": new_count,
            "analyzed": analyzed_count,
        }

    except ScrapingError as exc:
        job["status"] = "error"
        job["error"] = safe_error_message(exc)
    except Exception as exc:
        job["status"] = "error"
        job["error"] = safe_error_message(exc)


@router.get("/api/tenderscout/stream/{job_id}")
async def api_tenderscout_stream(job_id: str):
    """SSE stream pour la progression du scan TenderScout"""

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


@router.get("/api/tenderscout/tenders")
async def api_tenderscout_list(
    request: Request,
    source: Optional[str] = None,
    decision: Optional[str] = None,
    min_cv_match: Optional[int] = None,
):
    """Liste les appels d'offres avec filtres optionnels"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)
    db = TenderDatabase()
    return JSONResponse(
        db.get_tenders(source=source, decision=decision, min_cv_match=min_cv_match)
    )


@router.get("/api/tenderscout/export")
async def api_tenderscout_export(request: Request):
    """Exporte les appels d'offres en Excel"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = str(temp_dir / f"tenders_{timestamp}.xlsx")

    db = TenderDatabase()
    db.export_to_excel(export_path)

    return FileResponse(
        export_path,
        filename=f"tenders_{timestamp}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/api/tenderscout/notify")
@limiter.limit("10/minute")
async def api_tenderscout_notify(request: Request):
    """Envoie un récap Gmail des AOs GO"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Corps JSON invalide"}, status_code=400)

    to = sanitize_text_input(body.get("to", ""))
    credentials_path = body.get("credentials_path", "")

    if not to:
        return JSONResponse({"detail": "Destinataire requis."}, status_code=400)
    if not credentials_path:
        return JSONResponse({"detail": "Chemin credentials.json requis."}, status_code=400)

    # Construire le récap
    db = TenderDatabase()
    go_tenders = db.get_tenders(decision="GO", limit=50)

    if not go_tenders:
        recap_body = "Aucun appel d'offres qualifié GO lors du dernier scan TenderScout."
    else:
        lines = [f"TenderScout AI — Récap des AOs qualifiés GO ({len(go_tenders)} AO(s))\n"]
        for t in go_tenders:
            lines.append(f"• {t['titre']}")
            lines.append(f"  Acheteur : {t.get('acheteur') or '—'}")
            lines.append(f"  Date limite : {t.get('date_limite') or '—'}")
            lines.append(f"  Score : {t.get('score') or '—'}/100")
            lines.append(f"  URL : {t.get('url', '')}")
            lines.append("")
        recap_body = "\n".join(lines)

    subject = f"TenderScout AI — {len(go_tenders)} AO(s) qualifiés GO"
    token_path = str(Path(credentials_path).parent / "tenderscout_token.json")

    try:
        client = MeetingGmailClient()
        service = client.authenticate(credentials_path, token_path)
        draft = client.create_draft(service, to, subject, recap_body)
        return JSONResponse(draft)
    except DraftCreationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=500)
    except Exception as exc:
        return JSONResponse({"detail": safe_error_message(exc)}, status_code=500)
