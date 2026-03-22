import os
import uuid
import threading
import json
import asyncio
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from routers.shared import (
    templates, 
    limiter, 
    jobs, 
    skills_market_db, 
    BASE_DIR, 
    CONSULTANT_NAME, 
    safe_error_message
)
from agents.skills_market import SkillsMarketAgent
from utils.auth import get_current_user
from utils.validation import sanitize_text_input

router = APIRouter()

@router.get("/skills-market", response_class=HTMLResponse)
async def skills_market_page(request: Request):
    return templates.TemplateResponse(
        "skills-market.html",
        {
            "request": request,
            "active": "skills-market",
            "consultant_name": CONSULTANT_NAME,
        },
    )

@router.get("/api/skills-market/import/status")
async def api_skills_market_import_status():
    """Verifie si les donnees ont deja ete importees"""
    return {
        "imported": skills_market_db.is_imported(),
        "count": skills_market_db.get_consultant_count(),
    }

@router.post("/api/skills-market/import")
@limiter.limit("3/minute")
async def api_skills_market_import(request: Request):
    """Importe les consultants depuis le fichier PPTX"""
    pptx_path = str(BASE_DIR / "Biographies - CV All Consulting Tools.pptx")

    if not os.path.exists(pptx_path):
        return JSONResponse(
            {
                "error": "Fichier PPTX non trouve. "
                "Placez 'Biographies - CV All Consulting Tools.pptx' "
                "a la racine du projet."
            },
            status_code=404,
        )

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "skills-import",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_skills_import,
        args=(job_id, pptx_path),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}

def _run_skills_import(job_id: str, pptx_path: str):
    """Execute l'import des consultants en background"""
    job = jobs[job_id]

    try:
        skills_market_db.delete_all()
        agent = SkillsMarketAgent()

        job["steps"].append({"step": "reading", "status": "active", "progress": 5})

        def progress_cb(current, total, name):
            pct = int(10 + (current / max(total, 1)) * 80)
            job["steps"].append(
                {
                    "step": f"parsing_{current}",
                    "status": "active",
                    "progress": pct,
                    "message": (f"Analyse: {name} ({current}/{total})"),
                }
            )

        consultants = agent.import_from_pptx(pptx_path, progress_callback=progress_cb)

        job["steps"].append({"step": "saving", "status": "active", "progress": 90})

        for consultant_data in consultants:
            skills_market_db.save_consultant(consultant_data)

        job["steps"].append({"step": "done", "status": "done", "progress": 100})
        job["status"] = "done"
        job["result"] = {
            "imported": len(consultants),
            "message": (f"{len(consultants)} consultants importes"),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)

@router.post("/api/skills-market/upload")
@limiter.limit("10/minute")
async def api_skills_market_upload(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload un CV consultant (PPTX, PDF, ou HTML)"""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    allowed = {".pptx", ".pdf", ".html", ".htm"}

    if ext not in allowed:
        return JSONResponse(
            {"error": f"Format non supporte: {ext}. " f"Formats acceptes: {', '.join(allowed)}"},
            status_code=400,
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        return JSONResponse(
            {"error": "Fichier trop volumineux (max 50 Mo)"},
            status_code=400,
        )

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "skills-upload",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_skills_upload,
        args=(job_id, tmp_path, filename, ext),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}

def _run_skills_upload(job_id: str, file_path: str, filename: str, ext: str):
    """Upload et parse un fichier CV en background"""
    job = jobs[job_id]
    try:
        agent = SkillsMarketAgent()
        job["steps"].append({
            "step": "reading",
            "status": "active",
            "progress": 10,
            "message": f"Lecture de {filename}...",
        })
        consultants = []
        if ext == ".pptx":
            def progress_cb(current, total, name):
                pct = int(10 + (current / max(total, 1)) * 80)
                job["steps"].append({
                    "step": f"parsing_{current}",
                    "status": "active",
                    "progress": pct,
                    "message": (f"Analyse: {name} " f"({current}/{total})"),
                })
            consultants = agent.import_from_pptx(file_path, progress_callback=progress_cb)
        elif ext == ".pdf":
            from utils.document_parser import DocumentParser
            text = DocumentParser.parse_file(file_path) or ""
            if not text.strip():
                raise ValueError("Impossible d'extraire du texte du PDF")
            job["steps"].append({
                "step": "parsing",
                "status": "active",
                "progress": 30,
                "message": "Analyse du contenu PDF...",
            })
            def progress_cb(current, total, name):
                pct = int(30 + (current / max(total, 1)) * 50)
                job["steps"].append({
                    "step": f"parsing_{current}",
                    "status": "active",
                    "progress": pct,
                    "message": name,
                })
            consultants = agent.import_from_text(text, filename, progress_callback=progress_cb)
        elif ext in (".html", ".htm"):
            from bs4 import BeautifulSoup
            raw_html = open(file_path, "r", encoding="utf-8").read()
            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            if not text.strip():
                raise ValueError("Impossible d'extraire du texte du HTML")
            job["steps"].append({
                "step": "parsing",
                "status": "active",
                "progress": 30,
                "message": "Analyse du contenu HTML...",
            })
            def progress_cb(current, total, name):
                pct = int(30 + (current / max(total, 1)) * 50)
                job["steps"].append({
                    "step": f"parsing_{current}",
                    "status": "active",
                    "progress": pct,
                    "message": name,
                })
            consultants = agent.import_from_text(text, filename, progress_callback=progress_cb)

        job["steps"].append({
            "step": "saving",
            "status": "active",
            "progress": 90,
            "message": "Sauvegarde en base...",
        })
        saved = 0
        for consultant_data in consultants:
            skills_market_db.save_consultant(consultant_data)
            saved += 1
        job["steps"].append({"step": "done", "status": "done", "progress": 100})
        job["status"] = "done"
        job["result"] = {
            "imported": saved,
            "message": (f"{saved} consultant(s) ajoute(s) depuis {filename}"),
        }
    except Exception as e:
        job["status"] = "error"
        job["error"] = safe_error_message(e)
    finally:
        try:
            os.unlink(file_path)
        except OSError:
            pass

@router.get("/api/skills-market/stream/{job_id}")
async def api_skills_market_stream(job_id: str):
    """Stream SSE pour l'import"""
    if job_id not in jobs:
        return JSONResponse({"error": "Job non trouve"}, status_code=404)

    async def event_generator():
        last_idx = 0
        while True:
            job = jobs.get(job_id, {})
            steps = job.get("steps", [])
            if len(steps) > last_idx:
                for step in steps[last_idx:]:
                    yield (f"data: {json.dumps(step)}\n\n")
                last_idx = len(steps)
            if job.get("status") in ("done", "error"):
                final = {
                    "status": job["status"],
                    "result": job.get("result"),
                    "error": job.get("error"),
                }
                yield (f"data: {json.dumps(final)}\n\n")
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/api/skills-market/consultants")
async def api_skills_market_list(technical: Optional[str] = None, sector: Optional[str] = None):
    """Liste les consultants avec filtres optionnels"""
    tech_list = [t.strip() for t in technical.split(",") if t.strip()] if technical else None
    sector_list = [s.strip() for s in sector.split(",") if s.strip()] if sector else None
    if tech_list or sector_list:
        consultants = skills_market_db.search_by_skills(technical=tech_list, sector=sector_list)
    else:
        consultants = skills_market_db.get_all_consultants()
    return {"consultants": consultants}

@router.get("/api/skills-market/consultants/{consultant_id}")
async def api_skills_market_detail(consultant_id: int):
    """Recupere le profil complet d'un consultant"""
    consultant = skills_market_db.get_consultant(consultant_id)
    if not consultant:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    return {"consultant": consultant}

@router.delete("/api/skills-market/consultants/{consultant_id}")
async def api_skills_market_delete(consultant_id: int):
    """Supprime un consultant"""
    deleted = skills_market_db.delete_consultant(consultant_id)
    if not deleted:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    return {"message": "Consultant supprime"}

@router.get("/api/skills-market/skills")
async def api_skills_market_skills():
    """Recupere toutes les competences uniques"""
    return skills_market_db.get_all_skills()

@router.post("/api/skills-market/consultants/{consultant_id}/missions")
@limiter.limit("10/minute")
async def api_skills_market_add_mission(request: Request, consultant_id: int):
    """Ajoute une mission et met a jour les competences"""
    body = await request.json()
    client_name = body.get("client_name", "").strip()
    if not client_name:
        return JSONResponse({"error": "Le nom du client est requis"}, status_code=400)
    mission_data = {
        "client_name": client_name,
        "context_and_challenges": body.get("context_and_challenges", "").strip(),
        "deliverables": body.get("deliverables", "").strip(),
        "tasks": body.get("tasks", "").strip(),
        "start_date": body.get("start_date", ""),
        "end_date": body.get("end_date", ""),
        "skills_technical": body.get("skills_technical", []),
        "skills_sector": body.get("skills_sector", []),
    }
    mission_id = skills_market_db.add_mission(consultant_id, mission_data)
    return {"mission_id": mission_id, "message": "Experience ajoutee"}

@router.put("/api/skills-market/consultants/{consultant_id}/info")
@limiter.limit("20/minute")
async def api_skills_market_update_consultant_info(request: Request, consultant_id: int):
    """Met a jour les informations de base d'un consultant"""
    body = await request.json()
    updated = skills_market_db.update_consultant_info(consultant_id, body)
    if not updated:
        return JSONResponse({"error": "Consultant introuvable ou aucune modification"}, status_code=404)
    return {"ok": True, "message": "Profil mis a jour"}

@router.post("/api/skills-market/consultants/{consultant_id}/certifications")
@limiter.limit("10/minute")
async def api_skills_market_add_certification(request: Request, consultant_id: int):
    """Ajoute une certification et met a jour les skills"""
    body = await request.json()
    cert_name = body.get("name", "").strip()
    if not cert_name:
        return JSONResponse({"error": "Le nom de la certification est requis"}, status_code=400)
    cert_data = {
        "name": cert_name,
        "organization": body.get("organization", "").strip(),
        "date_obtained": body.get("date_obtained", "").strip(),
        "description": body.get("description", "").strip(),
        "skills_technical": body.get("skills_technical", []),
        "skills_sector": body.get("skills_sector", []),
    }
    cert_id = skills_market_db.add_certification(consultant_id, cert_data)
    return {"certification_id": cert_id, "message": "Certification ajoutee"}

@router.put("/api/skills-market/consultants/{consultant_id}/interests")
@limiter.limit("10/minute")
async def api_skills_market_update_interests(request: Request, consultant_id: int):
    body = await request.json()
    interests = body.get("interests", [])
    if not isinstance(interests, list):
        return JSONResponse({"error": "interests doit etre une liste"}, status_code=400)
    skills_market_db.update_interests(consultant_id, interests)
    return {"message": "Centres d'interet mis a jour"}

@router.put("/api/skills-market/consultants/{consultant_id}/disinterests")
@limiter.limit("10/minute")
async def api_skills_market_update_disinterests(request: Request, consultant_id: int):
    body = await request.json()
    disinterests = body.get("disinterests", [])
    if not isinstance(disinterests, list):
        return JSONResponse({"error": "disinterests doit etre une liste"}, status_code=400)
    skills_market_db.update_disinterests(consultant_id, disinterests)
    return {"message": "Centres de desinteret mis a jour"}

    return {"results": enriched}

@router.post("/api/skills-market/match")
@limiter.limit("5/minute")
async def api_skills_market_match(request: Request):
    """Match consultants to a mission description"""
    body = await request.json()
    mission_description = body.get("mission_description", "").strip()
    if not mission_description:
        return JSONResponse({"error": "La description de la mission est requise"}, status_code=400)
    
    consultants = skills_market_db.get_all_consultants()
    if not consultants:
        return {"matches": []}
        
    agent = SkillsMarketAgent()
    matches = agent.match_consultants_to_mission(mission_description, consultants)
    
    enriched_matches = []
    for m in matches:
        consultant = next((c for c in consultants if str(c["id"]) == str(m["consultant_id"])), None)
        if consultant:
            enriched_matches.append({
                "consultant": consultant,
                "score": m.get("matching_score", 0),
                "justification": m.get("justification", ""),
                "relevant_skills": m.get("relevant_skills", [])
            })
            
    return {"matches": enriched_matches}

@router.get("/api/skills-market/consultants/{consultant_id}/analysis")
async def api_skills_market_analysis(consultant_id: int):
    consultant = skills_market_db.get_consultant(consultant_id)
    if not consultant:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    agent = SkillsMarketAgent()
    analysis = agent.analyze_strengths(consultant)
    skills_market_db.update_consultant_analysis(
        consultant_id,
        strengths=analysis.get("strengths", []),
        improvement_areas=analysis.get("improvement_areas", []),
        management_suggestions=analysis.get("management_suggestions", ""),
    )
    return {"analysis": analysis}

PHOTOS_DIR = BASE_DIR / "static" / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
_ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/api/skills-market/consultants/{consultant_id}/photo")
@limiter.limit("5/minute")
async def api_skills_market_upload_photo(request: Request, consultant_id: int, photo: UploadFile = File(...)):
    consultant = skills_market_db.get_consultant(consultant_id)
    if not consultant:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    ext = Path(photo.filename).suffix.lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        return JSONResponse({"error": f"Format non supporte. Formats acceptes: {', '.join(_ALLOWED_IMAGE_EXTS)}"}, status_code=400)
    content = await photo.read()
    if len(content) > _MAX_PHOTO_SIZE:
        return JSONResponse({"error": "Fichier trop volumineux (max 5 Mo)"}, status_code=400)
    safe_name = f"consultant_{consultant_id}{ext}"
    photo_path = PHOTOS_DIR / safe_name
    with open(photo_path, "wb") as f:
        f.write(content)
    photo_url = f"/static/photos/{safe_name}"
    updated = skills_market_db.update_photo_url(consultant_id, photo_url)
    if not updated:
        return JSONResponse({"error": "Mise a jour echouee"}, status_code=500)
    return {"photo_url": photo_url, "message": "Photo mise a jour"}

@router.post("/api/skills-market/consultants/{consultant_id}/cv")
@limiter.limit("5/minute")
async def api_skills_market_generate_cv(request: Request, consultant_id: int):
    body = await request.json()
    client_need = body.get("client_need", "").strip()
    output_format = body.get("format", "html").lower()
    consultant = skills_market_db.get_consultant(consultant_id)
    if not consultant:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    agent = SkillsMarketAgent()
    try:
        cv_html = agent.generate_cv(consultant, client_need=client_need)
    except Exception as e:
        return JSONResponse({"error": f"Erreur generation CV: {safe_error_message(e)}"}, status_code=500)
    if output_format == "pdf":
        try:
            from datetime import datetime as _dt
            from utils.pdf_converter import pdf_converter as _pdf_conv
            timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            safe_name_cv = consultant.get("name", "consultant").replace(" ", "_")
            cv_dir = BASE_DIR / "static" / "cvs"
            cv_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = cv_dir / f"cv_{safe_name_cv}_{timestamp}.pdf"
            result = _pdf_conv.html_to_pdf(cv_html, str(pdf_path))
            if not result:
                return JSONResponse({"error": "Conversion PDF indisponible"}, status_code=500)
            return {"format": "pdf", "download_url": f"/static/cvs/{pdf_path.name}"}
        except Exception as e:
            return JSONResponse({"error": f"Erreur export PDF: {safe_error_message(e)}"}, status_code=500)
    return {"format": "html", "cv_html": cv_html}

@router.post("/api/skills-market/consultants/{consultant_id}/cover-letter")
@limiter.limit("5/minute")
async def api_skills_market_cover_letter(request: Request, consultant_id: int):
    body = await request.json()
    job_offer = sanitize_text_input(body.get("job_offer", ""), max_length=5000)
    output_format = body.get("format", "pdf").lower()
    if not job_offer:
        return JSONResponse({"error": "Champ 'job_offer' requis"}, status_code=400)
    consultant = skills_market_db.get_consultant(consultant_id)
    if not consultant:
        return JSONResponse({"error": "Consultant non trouve"}, status_code=404)
    agent = SkillsMarketAgent()
    try:
        letter_html = agent.generate_cover_letter(consultant, job_offer)
    except Exception as e:
        return JSONResponse({"error": f"Erreur generation lettre: {safe_error_message(e)}"}, status_code=500)
    if output_format == "pdf":
        try:
            from datetime import datetime as _dt
            from utils.pdf_converter import pdf_converter as _pdf_conv
            timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            safe_name = consultant.get("name", "consultant").replace(" ", "_")
            cv_dir = BASE_DIR / "static" / "cvs"
            cv_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = cv_dir / f"lettre_{safe_name}_{timestamp}.pdf"
            result = _pdf_conv.html_to_pdf(letter_html, str(pdf_path))
            if not result:
                return JSONResponse({"error": "Conversion PDF indisponible"}, status_code=500)
            return {"format": "pdf", "download_url": f"/static/cvs/{pdf_path.name}"}
        except Exception as e:
            return JSONResponse({"error": f"Erreur export PDF: {safe_error_message(e)}"}, status_code=500)
    return {"format": "html", "letter_html": letter_html}


@router.post("/api/skills-market/search")
@limiter.limit("20/minute")
async def api_skills_market_search(request: Request):
    """Recherche de consultants en langage naturel (NLSearch via LLM)"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "JSON invalide"}, status_code=400)
    query = sanitize_text_input(body.get("query", ""), max_length=500)
    if not query:
        return JSONResponse({"detail": "query requis"}, status_code=400)
    consultants = skills_market_db.get_all_consultants()
    agent = SkillsMarketAgent()
    try:
        nl_results = agent.natural_language_search(query, consultants)
    except Exception as e:
        return JSONResponse({"detail": safe_error_message(e)}, status_code=500)
    # Enrich each result with full consultant data
    consultant_map = {c["id"]: c for c in consultants if "id" in c}
    results = []
    for item in nl_results:
        cid = item.get("id")
        consultant = consultant_map.get(cid, {})
        results.append({
            **consultant,
            "score": item.get("score"),
            "explanation": item.get("explanation"),
        })
    return JSONResponse({"results": results})
