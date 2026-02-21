"""
WEnvision Agents - Application Web
FastAPI server exposant les agents de propositions commerciales et veille LinkedIn
"""
import os
import sys
import uuid
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

# Charger l'environnement
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

import io
from PyPDF2 import PdfReader
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Ajouter le repertoire au path pour les imports
sys.path.insert(0, str(BASE_DIR))

from agents.proposal_generator import ProposalGeneratorAgent
from agents.linkedin_monitor import LinkedInMonitorAgent
from agents.article_to_post import ArticleToPostAgent
from agents.meeting_summarizer import MeetingSummarizerAgent
from agents.linkedin_commenter import LinkedInCommenterAgent
from agents.tech_monitor import TechMonitorAgent
from agents.dataset_analyzer import DatasetAnalyzerAgent
from agents.workshop_planner import WorkshopPlannerAgent
from agents.rfp_responder import RFPResponderAgent
from utils.auth import authenticate_user, get_current_user, get_session_secret

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# === APP SETUP ===

app = FastAPI(title="WEnvision Agents", version="1.0.0")

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Templates and static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# === AUTHENTICATION MIDDLEWARE ===

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware pour vérifier l'authentification"""

    async def dispatch(self, request: Request, call_next):
        # Routes publiques (pas besoin d'auth)
        public_paths = ["/login", "/static"]

        # Si la route est publique, passer
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Vérifier l'authentification
        if not get_current_user(request):
            # Si c'est une requête API, renvoyer 401
            if request.url.path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Non authentifié"},
                    status_code=401
                )
            # Sinon, rediriger vers /login
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)


# Ajouter les middlewares dans l'ordre correct
# L'ordre d'ajout est inversé : le dernier ajouté s'exécute en premier
# app.add_middleware(AuthMiddleware)  # DESACTIVE - Pas de login requis
app.add_middleware(SessionMiddleware, secret_key=get_session_secret())  # S'exécute en premier

# Consultant info
CONSULTANT_NAME = os.getenv("CONSULTANT_NAME", "Jean-Sébastien Abessouguie Bayiha")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Wenvision")

# Job store (in-memory)
jobs = {}

# Global model settings (in-memory, persists per session)
AVAILABLE_GEMINI_MODELS = {
    "gemini-2.5-pro": "Gemini 2.5 Pro (Stable)",
    "gemini-2.5-flash": "Gemini 2.5 Flash (Rapide)",
    "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview",
    "gemini-2.0-flash": "Gemini 2.0 Flash",
}
SELECTED_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
IMAGE_MODEL = "gemini-3-pro-image-preview"  # Nano Banana Pro for images

# Settings persistence
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

def load_settings():
    """Charge les settings depuis le fichier JSON"""
    global SELECTED_GEMINI_MODEL
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            SELECTED_GEMINI_MODEL = settings.get("gemini_model", SELECTED_GEMINI_MODEL)
        except Exception:
            pass

def save_settings():
    """Sauvegarde les settings dans le fichier JSON"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = {"gemini_model": SELECTED_GEMINI_MODEL}
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

load_settings()


# === HELPERS ===

def get_stats():
    """Calcule les statistiques du dashboard"""
    output_dir = BASE_DIR / "output"
    monitoring_dir = BASE_DIR / "data" / "monitoring"

    proposals = len(list(output_dir.glob("proposal_*.md"))) if output_dir.exists() else 0
    posts = len(list(output_dir.glob("linkedin_post_*.md"))) if output_dir.exists() else 0

    articles = 0
    if monitoring_dir.exists():
        for f in monitoring_dir.glob("veille_*.json"):
            try:
                data = json.loads(f.read_text())
                articles += data.get("total_relevant", 0)
            except Exception:
                pass

    return {"proposals": proposals, "posts": posts, "articles": articles}


def get_recent_files(limit=8):
    """Liste les fichiers recemment generes"""
    output_dir = BASE_DIR / "output"
    if not output_dir.exists():
        return []

    files = []
    for f in sorted(output_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        files.append({
            "name": f.name,
            "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
            "path": str(f)
        })
    return files


def send_sse(event: str, data: dict) -> str:
    """Formate un message SSE"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# === AUTHENTICATION ROUTES ===

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Page de connexion"""
    # Si déjà connecté, rediriger vers le dashboard
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authentification"""
    if authenticate_user(username, password):
        request.session["user"] = username
        return {"success": True, "redirect": "/"}
    else:
        return JSONResponse(
            {"detail": "Nom d'utilisateur ou mot de passe incorrect"},
            status_code=401
        )


@app.get("/logout")
async def logout(request: Request):
    """Déconnexion"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# === SETTINGS API ===

@app.get("/api/settings/model")
async def get_model_settings():
    """Retourne le modele Gemini selectionne et la liste des modeles disponibles"""
    return {
        "current_model": SELECTED_GEMINI_MODEL,
        "available_models": AVAILABLE_GEMINI_MODELS,
        "image_model": IMAGE_MODEL,
    }

@app.post("/api/settings/model")
async def set_model_settings(request: Request):
    """Met a jour le modele Gemini selectionne"""
    global SELECTED_GEMINI_MODEL
    data = await request.json()
    model = data.get("model")
    if model not in AVAILABLE_GEMINI_MODELS:
        return JSONResponse({"error": "Modele inconnu"}, status_code=400)
    SELECTED_GEMINI_MODEL = model
    save_settings()
    return {"success": True, "model": model}


# === PAGE ROUTES ===

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active": "dashboard",
        "consultant_name": CONSULTANT_NAME,
        "stats": get_stats(),
        "recent_files": get_recent_files(),
    })


@app.get("/proposal", response_class=HTMLResponse)
async def proposal_page(request: Request):
    return templates.TemplateResponse("proposal.html", {
        "request": request,
        "active": "proposal",
        "consultant_name": CONSULTANT_NAME,
    })


@app.get("/proposal-modular", response_class=HTMLResponse)
async def proposal_modular_page(request: Request):
    return templates.TemplateResponse("proposal-modular.html", {
        "request": request,
        "active": "proposal",
        "consultant_name": CONSULTANT_NAME,
    })


@app.get("/linkedin", response_class=HTMLResponse)
async def linkedin_page(request: Request):
    return templates.TemplateResponse("linkedin.html", {
        "request": request,
        "active": "linkedin",
        "consultant_name": CONSULTANT_NAME,
    })


# === API: PROPOSAL ===

@app.post("/api/proposal/generate")
@limiter.limit("5/minute")
async def api_proposal_generate(
    request: Request,
    tender_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la generation d'une proposition commerciale"""
    text = ""

    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            # Extraire le texte du PDF
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(
                page.extract_text() or "" for page in pdf_reader.pages
            )
        else:
            text = content.decode("utf-8")
    elif tender_text:
        text = tender_text
    else:
        return JSONResponse({"error": "Aucun appel d'offre fourni."}, status_code=400)

    if len(text.strip()) < 50:
        return JSONResponse({"error": "L'appel d'offre semble trop court (min 50 caracteres)."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "proposal",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
        "tender_text": text,
    }

    # Lancer en background
    thread = threading.Thread(target=_run_proposal, args=(job_id, text), daemon=True)
    thread.start()

    return {"job_id": job_id}


def _run_proposal(job_id: str, tender_text: str):
    """Execute la generation de proposition en background"""
    job = jobs[job_id]

    try:
        agent = ProposalGeneratorAgent()

        # Step 1: Analyse
        job["steps"].append({"step": "analyze", "status": "active", "progress": 5})
        tender_analysis = agent.analyze_tender(tender_text)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 15})

        # Step 2: Template
        job["steps"].append({"step": "template", "status": "active", "progress": 18})
        template = agent.load_template()
        job["steps"].append({"step": "template", "status": "done", "progress": 25})

        # Step 3: References
        job["steps"].append({"step": "references", "status": "active", "progress": 28})
        references = agent.match_references(tender_analysis)
        job["steps"].append({"step": "references", "status": "done", "progress": 45})

        # Step 4: CVs
        job["steps"].append({"step": "generate", "status": "active", "progress": 48})
        cvs = agent.load_cvs()
        adapted_cvs = agent.adapt_cvs(cvs, tender_analysis) if cvs else []

        # Step 5: Generate slides structure + markdown content
        slides = agent.generate_slides_structure(
            tender_analysis, references, template, adapted_cvs
        )
        proposal = agent.generate_proposal_content(tender_analysis, references, template)
        job["steps"].append({"step": "generate", "status": "done", "progress": 85})

        # Sauvegarder les fichiers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_name = tender_analysis.get("client_name", "client").replace(" ", "_")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        json_path = output_dir / f"proposal_{client_name}_{timestamp}.json"
        md_path = output_dir / f"proposal_{client_name}_{timestamp}.md"
        pptx_path = output_dir / f"proposal_{client_name}_{timestamp}.pptx"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Proposition Commerciale - {tender_analysis.get('project_title', 'Projet')}\n\n")
            f.write(f"**Client:** {tender_analysis.get('client_name', 'N/A')}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y')}\n\n---\n\n")
            f.write(proposal["content"])

        # Generer le PPTX
        try:
            from utils.pptx_generator import build_proposal_pptx
            build_proposal_pptx(
                template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
                slides_data=slides,
                output_path=str(pptx_path),
                consultant_info={
                    "name": os.getenv("CONSULTANT_NAME", "Jean-Sébastien Abessouguie Bayiha"),
                    "company": os.getenv("COMPANY_NAME", "Wenvision"),
                },
            )
        except Exception as e:
            print(f"   ⚠️  Erreur PPTX: {e}")
            pptx_path = None

        job["status"] = "done"
        job["result"] = {
            "content": proposal["content"],
            "client_name": tender_analysis.get("client_name", "Projet"),
            "project_title": tender_analysis.get("project_title", ""),
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "json_path": str(json_path.relative_to(BASE_DIR)),
            "pptx_path": str(pptx_path.relative_to(BASE_DIR)) if pptx_path else None,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/proposal/stream/{job_id}")
async def api_proposal_stream(job_id: str):
    """SSE stream pour la progression de la proposition"""

    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouve"})
            return

        last_step_idx = 0
        while True:
            # Envoyer les nouvelles etapes
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


# === API: PROPOSAL FEEDBACK ===

@app.post("/api/proposal/regenerate")
async def api_proposal_regenerate(request: Request):
    """Regenere la proposition avec le feedback utilisateur"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_content = body.get("previous_content", "")
    job_id_ref = body.get("job_id", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    # Recuperer le tender_text du job original si possible
    tender_text = ""
    if job_id_ref and job_id_ref in jobs:
        tender_text = jobs[job_id_ref].get("tender_text", "")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "proposal",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
        "tender_text": tender_text,
    }

    thread = threading.Thread(
        target=_run_proposal_feedback,
        args=(job_id, previous_content, feedback, tender_text),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


# === API: PROPOSAL MODULAR GENERATION ===

@app.post("/api/proposal/generate-section")
@limiter.limit("10/minute")
async def api_proposal_generate_section(
    request: Request,
    section: str = Form(...),
    tender_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Génère une section spécifique de la proposition"""
    # Récupérer le texte de l'appel d'offre
    text = ""
    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        else:
            text = content.decode("utf-8")
    elif tender_text:
        text = tender_text
    else:
        return JSONResponse({"error": "Aucun appel d'offre fourni."}, status_code=400)

    if len(text.strip()) < 50:
        return JSONResponse({"error": "L'appel d'offre semble trop court."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "proposal_section",
        "section": section,
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_proposal_section,
        args=(job_id, text, section),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_proposal_section(job_id: str, tender_text: str, section: str):
    """Génère une section spécifique de la proposition"""
    job = jobs[job_id]

    try:
        agent = ProposalGeneratorAgent()

        # Analyser l'appel d'offre
        job["steps"].append({"step": "analyze", "status": "active", "progress": 10})
        tender_analysis = agent.analyze_tender(tender_text)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 30})

        # Générer la section demandée
        job["steps"].append({"step": "generate", "status": "active", "progress": 40})

        slides = []
        section_name = ""

        if section == "agenda":
            slides = agent.generate_agenda_slide(tender_analysis)
            section_name = "Agenda"
        elif section == "context":
            slides = agent.generate_context_slides(tender_analysis)
            section_name = "Contexte"
        elif section == "approach":
            references = agent.match_references(tender_analysis)
            slides = agent.generate_approach_slides(tender_analysis, references)
            section_name = "Approche"
        elif section == "planning":
            slides = agent.generate_planning_slide(tender_analysis)
            section_name = "Planning"
        elif section == "budget":
            slides = agent.generate_budget_slide(tender_analysis)
            section_name = "Chiffrage"
        elif section == "references":
            references = agent.load_references()
            slides = agent.generate_references_slides(tender_analysis, {"all_references": references})
            section_name = "Références"
        elif section == "cvs":
            slides = agent.generate_cv_slides(tender_analysis)
            section_name = "CVs"
        else:
            raise ValueError(f"Section inconnue: {section}")

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})

        # Générer le PPTX SANS cover ni closing (mode modulaire)
        job["steps"].append({"step": "pptx", "status": "active", "progress": 85})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_name = tender_analysis.get("client_name", "client").replace(" ", "_")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        pptx_path = output_dir / f"proposal_{section}_{client_name}_{timestamp}.pptx"

        # Mode modulaire : UNIQUEMENT les slides de la section (sans cover ni closing)
        # L'utilisateur assemble ensuite les sections manuellement
        full_slides = slides

        from utils.pptx_generator import build_proposal_pptx
        build_proposal_pptx(
            template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
            slides_data=full_slides,
            output_path=str(pptx_path),
            consultant_info={
                "name": os.getenv("CONSULTANT_NAME", "Jean-Sébastien Abessouguie Bayiha"),
                "company": os.getenv("COMPANY_NAME", "Wenvision"),
            },
        )

        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "section": section,
            "section_name": section_name,
            "slides_count": len(slides),
            "pptx_path": str(pptx_path.relative_to(BASE_DIR)),
            "tender_text": tender_text,  # Inclure le texte pour la régénération
            "slides_data": slides  # Inclure les données des slides
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.post("/api/proposal/preview")
@limiter.limit("20/minute")
async def api_proposal_preview(
    request: Request,
    pptx_path: str = Form(...),
):
    """Génère des images de prévisualisation des slides"""
    try:
        import subprocess
        import tempfile
        from PIL import Image

        # Résoudre le chemin absolu du PPTX
        file_path = BASE_DIR / pptx_path

        if not file_path.exists():
            return JSONResponse({"error": "Fichier PPTX introuvable"}, status_code=404)

        # Créer un répertoire temporaire pour les images
        temp_dir = Path(tempfile.mkdtemp(dir=BASE_DIR / "output"))

        try:
            # Convertir PPTX en PNG avec LibreOffice (méthode la plus fiable)
            # Note: LibreOffice doit être installé sur le système
            subprocess.run([
                "soffice",
                "--headless",
                "--convert-to", "png",
                "--outdir", str(temp_dir),
                str(file_path)
            ], check=True, timeout=30, capture_output=True)

            # Récupérer toutes les images générées
            preview_images = sorted(temp_dir.glob("*.png"))

            if not preview_images:
                # Fallback: essayer avec python-pptx + Pillow (moins fiable mais sans dépendance externe)
                from pptx import Presentation
                from pptx.util import Inches

                prs = Presentation(str(file_path))
                preview_images = []

                for i, slide in enumerate(prs.slides):
                    # Cette approche est limitée car python-pptx ne rend pas visuellement
                    # On crée juste un placeholder pour indiquer que la conversion a échoué
                    pass

                if not preview_images:
                    return JSONResponse({
                        "error": "Impossible de générer la prévisualisation. LibreOffice n'est pas installé.",
                        "preview_images": []
                    }, status_code=500)

            # Créer des versions miniatures pour la galerie
            thumbnails = []
            for img_path in preview_images:
                # Copier vers le dossier output avec un nom unique
                thumb_name = f"preview_{uuid.uuid4().hex[:8]}_{img_path.name}"
                thumb_path = BASE_DIR / "output" / thumb_name

                # Créer une miniature (optionnel, pour optimiser le chargement)
                with Image.open(img_path) as img:
                    img.thumbnail((800, 600))
                    img.save(thumb_path, "PNG")

                thumbnails.append(str(Path("output") / thumb_name))

                # Nettoyer le fichier temporaire
                img_path.unlink()

            # Nettoyer le répertoire temporaire
            temp_dir.rmdir()

            return JSONResponse({
                "preview_images": thumbnails,
                "slide_count": len(thumbnails)
            })

        except subprocess.CalledProcessError as e:
            # LibreOffice n'est pas disponible ou a échoué
            return JSONResponse({
                "error": "La génération de prévisualisation nécessite LibreOffice. Installez-le avec: brew install libreoffice (Mac) ou apt-get install libreoffice (Linux)",
                "preview_images": []
            }, status_code=500)
        except Exception as e:
            return JSONResponse({
                "error": f"Erreur lors de la génération de prévisualisation: {str(e)}",
                "preview_images": []
            }, status_code=500)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/proposal/regenerate-section")
@limiter.limit("10/minute")
async def api_proposal_regenerate_section(
    request: Request,
    section: str = Form(...),
    feedback: str = Form(...),
    tender_text: Optional[str] = Form(None),
    previous_slides: Optional[str] = Form(None),  # JSON string des slides précédentes
):
    """Régénère une section avec feedback en langage naturel"""

    if not feedback.strip():
        return JSONResponse({"error": "Le feedback ne peut pas être vide."}, status_code=400)

    if not tender_text or len(tender_text.strip()) < 50:
        return JSONResponse({"error": "Le texte de l'appel d'offre est requis pour la régénération."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "proposal_section",
        "section": section,
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    # Parse previous_slides si fourni
    prev_slides = []
    if previous_slides:
        try:
            prev_slides = json.loads(previous_slides)
        except:
            pass

    thread = threading.Thread(
        target=_run_proposal_section_with_feedback,
        args=(job_id, tender_text, section, feedback, prev_slides),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_proposal_section_with_feedback(
    job_id: str,
    tender_text: str,
    section: str,
    feedback: str,
    previous_slides: List[dict]
):
    """Régénère une section en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = ProposalGeneratorAgent()

        # Analyser l'appel d'offre
        job["steps"].append({"step": "analyze", "status": "active", "progress": 10})
        tender_analysis = agent.analyze_tender(tender_text)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 30})

        # Interpréter le feedback avec le LLM
        job["steps"].append({"step": "generate", "status": "active", "progress": 40})

        # Construire le contexte des slides précédentes
        previous_context = ""
        if previous_slides:
            previous_context = f"""
SLIDES PRÉCÉDENTES:
{json.dumps(previous_slides, indent=2, ensure_ascii=False)[:2000]}
"""

        # Utiliser le LLM pour interpréter le feedback et générer des instructions structurées
        interpretation = agent.llm_client.generate(
            prompt=f"""L'utilisateur veut modifier la section "{section}" de sa proposition commerciale.

{previous_context}

FEEDBACK UTILISATEUR (en langage naturel):
{feedback}

Analyse ce feedback et génère des instructions STRUCTURÉES pour régénérer la section.
Réponds en JSON avec ces champs:
{{
  "changes_requested": ["Liste des modifications demandées"],
  "visual_changes": ["Modifications visuelles (diagrammes, mise en page)"],
  "content_changes": ["Modifications de contenu (texte, chiffres, structure)"],
  "tone_changes": "Changement de ton si demandé",
  "specific_instructions": "Instructions précises pour la régénération"
}}

Exemples:
- "Planning trop court" → ajouter des phases, augmenter les durées
- "Moins de bullets" → réduire à 2-3 bullets par slide
- "Diagramme flow → cycle" → remplacer le type de diagramme
- "Augmenter budget 20%" → multiplier les montants par 1.2""",
            system_prompt="Tu es un expert en interprétation de feedback pour la génération de documents. Sois précis et actionnable.",
            temperature=0.4,
            max_tokens=1500,
        )

        # Parser l'interprétation
        try:
            feedback_data = json.loads(interpretation.strip())
        except:
            feedback_data = {
                "specific_instructions": feedback,
                "changes_requested": [feedback]
            }

        # Générer la section avec les instructions du feedback
        slides = []
        section_name = ""
        references = None

        # Enrichir tender_analysis avec les instructions du feedback
        tender_analysis["feedback_instructions"] = feedback_data.get("specific_instructions", feedback)
        tender_analysis["feedback_data"] = feedback_data

        if section == "agenda":
            slides = agent.generate_agenda_slide(tender_analysis)
            section_name = "Agenda"
        elif section == "context":
            slides = agent.generate_context_slides(tender_analysis)
            section_name = "Contexte"
        elif section == "approach":
            references = agent.match_references(tender_analysis)
            slides = agent.generate_approach_slides(tender_analysis, references)
            section_name = "Approche"
        elif section == "planning":
            slides = agent.generate_planning_slide(tender_analysis)
            section_name = "Planning"
        elif section == "budget":
            slides = agent.generate_budget_slide(tender_analysis)
            section_name = "Chiffrage"
        elif section == "references":
            references = agent.load_references()
            slides = agent.generate_references_slides(tender_analysis, {"all_references": references})
            section_name = "Références"
        elif section == "cvs":
            slides = agent.generate_cv_slides(tender_analysis)
            section_name = "CVs"
        else:
            raise ValueError(f"Section inconnue: {section}")

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})

        # Générer le PPTX
        job["steps"].append({"step": "pptx", "status": "active", "progress": 85})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_name = tender_analysis.get("client_name", "client").replace(" ", "_")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        pptx_path = output_dir / f"proposal_{section}_{client_name}_{timestamp}_v2.pptx"

        full_slides = slides

        from utils.pptx_generator import build_proposal_pptx
        build_proposal_pptx(
            template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
            slides_data=full_slides,
            output_path=str(pptx_path),
            consultant_info={
                "name": os.getenv("CONSULTANT_NAME", "Jean-Sébastien Abessouguie Bayiha"),
                "company": os.getenv("COMPANY_NAME", "Wenvision"),
            },
        )

        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "section": section,
            "section_name": section_name,
            "slides_count": len(slides),
            "pptx_path": str(pptx_path.relative_to(BASE_DIR)),
            "feedback_applied": feedback_data.get("changes_requested", [feedback]),
            "slides_data": slides  # Inclure les données des slides pour la prochaine itération
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        import traceback
        print(f"Error in regenerate section: {traceback.format_exc()}")


@app.post("/api/proposal/regenerate-slide")
@limiter.limit("20/minute")
async def api_proposal_regenerate_slide(
    request: Request,
    section: str = Form(...),
    slide_index: int = Form(...),
    slide_title: str = Form(...),
    slide_bullets: str = Form(...),  # JSON array
    diagram_type: Optional[str] = Form(None),
    tender_text: Optional[str] = Form(None),
):
    """Régénère une seule slide avec le nouveau contenu"""

    if not tender_text or len(tender_text.strip()) < 50:
        return JSONResponse({"error": "Le texte de l'appel d'offre est requis."}, status_code=400)

    try:
        # Parse bullets
        bullets = json.loads(slide_bullets)

        # Charger le PPTX existant pour récupérer toutes les slides
        # On va chercher le fichier le plus récent pour cette section
        output_dir = BASE_DIR / "output"
        matching_files = sorted(
            output_dir.glob(f"proposal_{section}_*.pptx"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not matching_files:
            return JSONResponse({"error": "Aucun PPTX existant trouvé pour cette section"}, status_code=404)

        latest_pptx = matching_files[0]

        # Charger les slides depuis le PPTX existant
        from pptx import Presentation
        prs = Presentation(str(latest_pptx))

        # Vérifier que l'index est valide (en tenant compte de la slide de couverture)
        if slide_index + 1 >= len(prs.slides):
            return JSONResponse({"error": f"Index de slide invalide: {slide_index}"}, status_code=400)

        # Modifier la slide ciblée
        target_slide = prs.slides[slide_index + 1]  # +1 car slide 0 = couverture

        # Trouver les textframes et mettre à jour
        for shape in target_slide.shapes:
            if shape.has_text_frame:
                text_frame = shape.text_frame
                # Le premier textframe est généralement le titre
                if shape.name.startswith("Title") or "titre" in shape.name.lower():
                    text_frame.text = slide_title
                    break

        # Mettre à jour le contenu (bullets)
        for shape in target_slide.shapes:
            if shape.has_text_frame and not (shape.name.startswith("Title") or "titre" in shape.name.lower()):
                text_frame = shape.text_frame
                text_frame.clear()

                # Ajouter les nouveaux bullets
                for i, bullet in enumerate(bullets):
                    p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
                    p.text = bullet
                    p.level = 0

                    # Styling (utiliser les styles existants si possible)
                    from pptx.util import Pt
                    if p.runs:
                        p.runs[0].font.size = Pt(11)

                break

        # Sauvegarder le PPTX modifié
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        agent = ProposalGeneratorAgent()
        tender_analysis = agent.analyze_tender(tender_text)
        client_name = tender_analysis.get("client_name", "client").replace(" ", "_")

        new_pptx_path = output_dir / f"proposal_{section}_{client_name}_{timestamp}_edited.pptx"
        prs.save(str(new_pptx_path))

        # Extraire les données des slides pour le frontend
        slides_data = []
        for i, slide in enumerate(prs.slides):
            if i == 0:  # Skip cover
                continue

            slide_data = {"title": "", "bullets": [], "visual": None}

            for shape in slide.shapes:
                if shape.has_text_frame:
                    if shape.name.startswith("Title") or "titre" in shape.name.lower():
                        slide_data["title"] = shape.text_frame.text
                    else:
                        for paragraph in shape.text_frame.paragraphs:
                            if paragraph.text.strip():
                                slide_data["bullets"].append(paragraph.text.strip())

            slides_data.append(slide_data)

        return JSONResponse({
            "pptx_path": str(new_pptx_path.relative_to(BASE_DIR)),
            "slides_data": slides_data,
            "message": "Slide régénérée avec succès"
        })

    except Exception as e:
        import traceback
        print(f"Error in regenerate slide: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/proposal/export-to-slides")
@limiter.limit("5/minute")
async def api_export_to_slides(
    request: Request,
    section: str = Form(...),
    tender_text: Optional[str] = Form(None),
    slides_data: str = Form(...),  # JSON string
):
    """Exporte une section vers Google Slides"""

    try:
        # Parser les données des slides avec sanitization robuste
        # Fix: le JSON envoyé depuis le frontend peut contenir des caractères de contrôle
        # ou des chaînes mal échappées, causant "Unterminated string"
        import re
        sanitized = slides_data.strip()
        # Supprimer les caractères de contrôle (sauf \n, \t, \r qui sont gérés par JSON)
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
        # Remplacer les vrais retours à la ligne dans les valeurs string par \\n
        # (ceux qui ne sont pas déjà échappés)
        sanitized = sanitized.replace('\r\n', '\\n').replace('\r', '\\n')

        try:
            slides = json.loads(sanitized)
        except json.JSONDecodeError:
            # Fallback: essayer de nettoyer plus agressivement
            # Parfois les guillemets internes ne sont pas échappés
            sanitized = sanitized.replace('\t', '\\t')
            # Tenter un nettoyage ligne par ligne
            lines = sanitized.split('\n')
            cleaned_lines = []
            for line in lines:
                # Ne pas modifier les lignes structurelles JSON
                cleaned_lines.append(line)
            sanitized = '\n'.join(cleaned_lines)
            slides = json.loads(sanitized)

        # Analyser le tender pour obtenir le titre
        if tender_text and len(tender_text.strip()) >= 50:
            agent = ProposalGeneratorAgent()
            tender_analysis = agent.analyze_tender(tender_text)
            client_name = tender_analysis.get("client_name", "Client")
            project_title = tender_analysis.get("project_title", "Projet")
        else:
            client_name = "Client"
            project_title = "Projet"

        # Générer le titre de la présentation
        section_names = {
            "agenda": "Agenda",
            "context": "Contexte",
            "approach": "Approche",
            "planning": "Planning",
            "budget": "Chiffrage",
            "references": "Références",
            "cvs": "CVs"
        }

        section_name = section_names.get(section, section.capitalize())
        presentation_title = f"{client_name} - {project_title} - {section_name}"

        # Exporter vers Google Slides
        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            presentation_id = google_client.export_pptx_to_slides(
                slides_data=slides,
                title=presentation_title
            )

            if presentation_id:
                presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

                return JSONResponse({
                    "presentation_id": presentation_id,
                    "presentation_url": presentation_url,
                    "message": "Présentation Google Slides créée avec succès"
                })
            else:
                return JSONResponse(
                    {"error": "Échec de la création de la présentation Google Slides"},
                    status_code=500
                )

        except Exception as e:
            # Si l'authentification Google échoue ou n'est pas configurée
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse({
                    "error": "Google API non configurée. Veuillez configurer vos credentials Google dans config/google_credentials.json",
                    "setup_required": True
                }, status_code=400)
            else:
                raise

    except Exception as e:
        import traceback
        print(f"Error in export to slides: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


def _run_proposal_feedback(job_id: str, previous_content: str, feedback: str, tender_text: str):
    """Regenere la proposition en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = ProposalGeneratorAgent()

        job["steps"].append({"step": "analyze", "status": "done", "progress": 10})
        job["steps"].append({"step": "template", "status": "done", "progress": 20})
        job["steps"].append({"step": "references", "status": "done", "progress": 30})
        job["steps"].append({"step": "generate", "status": "active", "progress": 40})

        # Analyser le tender_text si disponible pour avoir plus de contexte
        tender_context = ""
        if tender_text:
            try:
                tender_analysis = agent.analyze_tender(tender_text)
                tender_context = f"""
Contexte de l'appel d'offre:
Client: {tender_analysis.get('client_name', 'N/A')}
Projet: {tender_analysis.get('project_title', 'N/A')}
Objectifs: {', '.join(tender_analysis.get('objectives', [])[:3])}
"""
            except Exception:
                tender_context = f"Appel d'offre: {tender_text[:1000]}"

        # Regenerer le contenu markdown avec feedback
        revised_content = agent.llm_client.generate(
            prompt=f"""Voici une proposition commerciale generee precedemment:

{previous_content[:6000]}

FEEDBACK DE L'UTILISATEUR:
{feedback}

{tender_context}

Reecris la proposition en integrant les corrections demandees dans le feedback.
Conserve la structure et le style professionnel. Ne modifie que ce qui est demande dans le feedback.
Sois concret et precis. Evite les majuscules inutiles et les emojis.
Fournis la proposition complete revisee.""",
            system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges une proposition commerciale selon le retour du consultant.
Reponds en francais de maniere professionnelle.""",
            temperature=0.6,
            max_tokens=8000,
        )

        job["steps"].append({"step": "generate", "status": "done", "progress": 60})
        job["steps"].append({"step": "slides", "status": "active", "progress": 65})

        # Regenerer les slides avec feedback - avec meilleur prompt
        revised_slides = None
        try:
            slides_response = agent.llm_client.generate(
                prompt=f"""Genere une structure complete de slides PowerPoint pour cette proposition commerciale revisee.

PROPOSITION REVISEE:
{revised_content[:5000]}

FEEDBACK APPLIQUE:
{feedback}

{tender_context}

Genere la structure COMPLETE avec tout le contenu. Reponds UNIQUEMENT en JSON valide:

[
  {{"type":"cover","client":"...","project":"...","date":"{datetime.now().strftime('%d/%m/%Y')}"}},
  {{"type":"section","title":"Notre comprehension du contexte","number":1}},
  {{"type":"content","title":"Contexte et enjeux","bullets":["Bullet 1","Bullet 2","Bullet 3","Bullet 4"],"subtitle":""}},
  {{"type":"content","title":"Objectifs","bullets":["Objectif 1","Objectif 2","Objectif 3"]}},
  {{"type":"section","title":"Notre expertise","number":2}},
  {{"type":"content","title":"Notre valeur ajoutee","bullets":["Valeur 1","Valeur 2","Valeur 3","Valeur 4"]}},
  {{"type":"section","title":"Notre demarche","number":3}},
  {{"type":"content","title":"Phases du projet","bullets":["Phase 1: Description","Phase 2: Description","Phase 3: Description"]}},
  {{"type":"section","title":"Planning","number":4}},
  {{"type":"table","title":"Planning previsionnel","headers":["Phase","Duree","Livrables"],"rows":[["Phase 1","2 sem","Livrable"],["Phase 2","3 sem","Livrable"]]}},
  {{"type":"section","title":"Budget","number":5}},
  {{"type":"table","title":"Chiffrage","headers":["Prestation","Jours","TJM","Total"],"rows":[["Phase 1","10j","1000€","10000€"],["Total","","","XX XXX€"]]}},
  {{"type":"closing"}}
]

IMPORTANT:
- Chaque slide "content" DOIT avoir un champ "bullets" avec 4-6 points concrets
- Chaque slide "table" DOIT avoir "headers" et "rows"
- Total: 10-16 slides
- Integre les modifications demandees dans le feedback""",
                system_prompt="Tu generes des structures de slides PowerPoint completes en JSON. Sois concret et professionnel.",
                temperature=0.5,
                max_tokens=8000,
            )

            json_start = slides_response.find('[')
            json_end = slides_response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                revised_slides = json.loads(slides_response[json_start:json_end])

                # Valider que les slides ont du contenu
                for slide in revised_slides:
                    if slide.get('type') == 'content' and 'bullets' not in slide:
                        slide['bullets'] = ["Point a developper", "Deuxieme point", "Troisieme point"]
                    elif slide.get('type') == 'table' and 'rows' not in slide:
                        slide['headers'] = slide.get('headers', ['Colonne 1', 'Colonne 2'])
                        slide['rows'] = [['Donnee 1', 'Donnee 2']]

                print(f"   Slides revisees generees: {len(revised_slides)}")
        except Exception as e:
            print(f"   Erreur generation slides: {e}")
            revised_slides = None

        job["steps"].append({"step": "slides", "status": "done", "progress": 85})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"proposal_revised_{timestamp}.md"
        json_path = output_dir / f"proposal_revised_{timestamp}.json"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Proposition commerciale (revisee)\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y')}\n\n---\n\n")
            f.write(revised_content)

        proposal_data = {"content": revised_content, "feedback_applied": feedback, "slides": revised_slides}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(proposal_data, f, indent=2, ensure_ascii=False)

        # Generer le PPTX revise
        pptx_path = None
        if revised_slides:
            try:
                from utils.pptx_generator import build_proposal_pptx
                pptx_path = output_dir / f"proposal_revised_{timestamp}.pptx"
                build_proposal_pptx(
                    template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
                    slides_data=revised_slides,
                    output_path=str(pptx_path),
                    consultant_info={
                        "name": CONSULTANT_NAME,
                        "company": os.getenv("COMPANY_NAME", "Wenvision"),
                    },
                )
                print(f"   PPTX revise genere: {pptx_path}")
            except Exception as e:
                print(f"   Erreur PPTX revise: {e}")
                pptx_path = None

        job["status"] = "done"
        job["result"] = {
            "content": revised_content,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "json_path": str(json_path.relative_to(BASE_DIR)),
            "pptx_path": str(pptx_path.relative_to(BASE_DIR)) if pptx_path else None,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# === API: LINKEDIN ===

@app.post("/api/linkedin/generate")
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
        job["error"] = str(e)


@app.get("/api/linkedin/stream/{job_id}")
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


# === API: LINKEDIN FEEDBACK ===

@app.post("/api/linkedin/regenerate")
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
                prompt=f"""Voici un post LinkedIn genere precedemment:

{post.get('main_post', '')}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce post en integrant les corrections demandees.
Conserve le format LinkedIn (hook, contenu, question d'engagement, hashtags).
Ne modifie que ce qui est demande dans le feedback.""",
                system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un post LinkedIn selon le retour du consultant.

REGLES IMPERATIVES:
- Ne JAMAIS inventer d'anecdotes, d'exemples fictifs ou d'experiences personnelles
- Ne JAMAIS fabriquer de chiffres, statistiques ou citations""",
                temperature=0.6,
                max_tokens=1500,
            )
            revised_posts.append({
                "main_post": revised,
                "post_type": post.get("post_type", "insight"),
                "source_articles": post.get("source_articles", []),
            })

        job["steps"].append({"step": "posts", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "posts": revised_posts,
            "articles": [],
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# === PAGE & API: ARTICLE TO POST ===

@app.get("/article", response_class=HTMLResponse)
async def article_page(request: Request):
    return templates.TemplateResponse("article.html", {
        "request": request,
        "active": "article",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/article/generate")
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

    thread = threading.Thread(
        target=_run_article_to_post, args=(job_id, url, tone), daemon=True
    )
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
            f.write(f"# Post LinkedIn - Partage d'article\n\n")
            f.write(f"**Article:** [{article['title']}]({url})\n")
            f.write(f"**Ton:** {tone}\n\n## Post Principal\n\n")
            f.write(result["main_post"])
            f.write(f"\n\n---\n\n## Version Courte\n\n")
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
        job["error"] = str(e)


@app.get("/api/article/stream/{job_id}")
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


# === API: ARTICLE FEEDBACK ===

@app.post("/api/article/regenerate")
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


def _run_article_feedback(job_id: str, previous_main: str, previous_short: str, feedback: str, article_url: str, tone: str):
    """Regenere le post article en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = ArticleToPostAgent()

        job["steps"].append({"step": "fetch", "status": "done", "progress": 10})
        job["steps"].append({"step": "generate", "status": "active", "progress": 30})

        # Regenerer le post principal
        revised_main = agent.llm_client.generate(
            prompt=f"""Voici un post LinkedIn genere precedemment pour partager un article:

{previous_main}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce post en integrant les corrections demandees.
Conserve le format LinkedIn (hook, perspective, points cles, appel a l'action, hashtags).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
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
            prompt=f"""A partir de ce post LinkedIn revise, cree une version courte (400-600 caracteres max) qui va droit au point.

Post revise:
{revised_main}

Garde le hook et la question finale, compresse le milieu.
NE PAS inventer d'anecdotes ou d'exemples.""",
            system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.""",
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
        job["error"] = str(e)


# === PAGE & API: MEETING SUMMARIZER ===

@app.get("/meeting", response_class=HTMLResponse)
async def meeting_page(request: Request):
    return templates.TemplateResponse("meeting.html", {
        "request": request,
        "active": "meeting",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/meeting/generate")
async def api_meeting_generate(
    transcript_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la generation d'un compte rendu de reunion"""
    text = ""

    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(
                page.extract_text() or "" for page in pdf_reader.pages
            )
        else:
            text = content.decode("utf-8")
    elif transcript_text:
        text = transcript_text
    else:
        return JSONResponse({"error": "Aucun transcript fourni."}, status_code=400)

    if len(text.strip()) < 30:
        return JSONResponse({"error": "Le transcript semble trop court."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "meeting",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_meeting_summarizer, args=(job_id, text), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_meeting_summarizer(job_id: str, transcript: str):
    """Execute la generation de compte rendu en background"""
    job = jobs[job_id]

    try:
        from agents.meeting_summarizer import MeetingSummarizerAgent
        agent = MeetingSummarizerAgent()

        # Step 1: Extraction
        job["steps"].append({"step": "extract", "status": "active", "progress": 10})
        extracted_result = agent.extract_key_info(transcript)
        extracted_info = extracted_result["extracted_info"]
        job["steps"].append({"step": "extract", "status": "done", "progress": 35})

        # Step 2: Compte rendu
        job["steps"].append({"step": "minutes", "status": "active", "progress": 40})
        minutes = agent.generate_minutes(transcript, extracted_info)
        job["steps"].append({"step": "minutes", "status": "done", "progress": 70})

        # Step 3: Email
        job["steps"].append({"step": "email", "status": "active", "progress": 75})
        email_result = agent.generate_email(extracted_info, minutes)
        job["steps"].append({"step": "email", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"meeting_summary_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Compte Rendu de Reunion\n\n")
            f.write(f"**Genere le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n---\n\n")
            f.write(minutes)
            f.write("\n\n---\n\n# Mail de Partage\n\n")
            f.write(f"**Objet:** {email_result['subject']}\n\n")
            f.write(email_result['body'])

        job["status"] = "done"
        job["result"] = {
            "minutes": minutes,
            "email": email_result,
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        import traceback
        job["status"] = "error"
        job["error"] = str(e)
        print(f"Error in meeting summarizer: {traceback.format_exc()}")


@app.get("/api/meeting/stream/{job_id}")
async def api_meeting_stream(job_id: str):
    """SSE stream pour la progression du compte rendu"""

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


# === API: MEETING FEEDBACK ===

@app.post("/api/meeting/regenerate")
async def api_meeting_regenerate(request: Request):
    """Regenere le compte rendu avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_minutes = body.get("previous_minutes", "")
    previous_email = body.get("previous_email", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "meeting",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_meeting_feedback,
        args=(job_id, previous_minutes, previous_email, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_meeting_feedback(job_id: str, previous_minutes: str, previous_email: str, feedback: str):
    """Regenere le compte rendu en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = MeetingSummarizerAgent()

        job["steps"].append({"step": "extract", "status": "done", "progress": 10})
        job["steps"].append({"step": "minutes", "status": "active", "progress": 30})

        # Regenerer le compte rendu
        revised_minutes = agent.llm_client.generate(
            prompt=f"""Voici un compte rendu de reunion genere precedemment:

{previous_minutes}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce compte rendu en integrant les corrections demandees.
Conserve la structure professionnelle (contexte, points abordes, decisions, plan d'actions, points en suspens, prochaines etapes).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un compte rendu de reunion selon le retour du consultant.""",
            temperature=0.5,
            max_tokens=3000,
        )

        job["steps"].append({"step": "minutes", "status": "done", "progress": 70})
        job["steps"].append({"step": "email", "status": "active", "progress": 75})

        # Regenerer le mail
        revised_email = agent.llm_client.generate(
            prompt=f"""Voici un mail de partage de compte rendu genere precedemment:

{previous_email}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reecris ce mail en integrant les corrections demandees.
Conserve le format professionnel (objet, resume executif, decisions cles, actions, signature).
Ne modifie que ce qui est demande dans le feedback.""",
            system_prompt=f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un mail professionnel selon le retour du consultant.""",
            temperature=0.5,
            max_tokens=1500,
        )

        job["steps"].append({"step": "email", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "minutes": revised_minutes,
            "email": revised_email,
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# === PAGE & API: LINKEDIN COMMENT ===

@app.get("/comment", response_class=HTMLResponse)
async def comment_page(request: Request):
    return templates.TemplateResponse("comment.html", {
        "request": request,
        "active": "comment",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/comment/generate")
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
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Commentaires LinkedIn\n\n")
            f.write(f"**Style:** {style}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("## Post original (extrait)\n\n")
            f.write(f"> {result['post_preview']}\n\n")
            f.write("---\n\n")
            f.write("## Commentaire Court\n\n")
            f.write(result['short'])
            f.write("\n\n---\n\n## Commentaire Moyen\n\n")
            f.write(result['medium'])
            f.write("\n\n---\n\n## Commentaire Long\n\n")
            f.write(result['long'])
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
        job["error"] = str(e)


@app.get("/api/comment/stream/{job_id}")
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


# === API: COMMENT FEEDBACK ===

@app.post("/api/comment/regenerate")
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
        args=(job_id, previous_short, previous_medium, previous_long, feedback, post_preview, style),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_comment_feedback(job_id: str, previous_short: str, previous_medium: str, previous_long: str, feedback: str, post_preview: str, style: str):
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
            persona_content = persona_path.read_text(encoding='utf-8')
            start_idx = persona_content.find("### ✨ Ton & Style")
            end_idx = persona_content.find("### 📝 Structure de posts")
            if start_idx != -1 and end_idx != -1:
                persona_style = "\n\nSTYLE 'PARISIEN GENZ' A APPLIQUER:\n" + persona_content[start_idx:end_idx]

        system_prompt = f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Base : Paris | Génération Z assumée
{persona_style}

Tu corriges des commentaires LinkedIn selon le feedback de l'utilisateur."""

        # Regenerer commentaire court
        revised_short = agent.llm_client.generate(
            prompt=f"""Voici un commentaire court genere precedemment pour ce post:

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
            prompt=f"""Voici un commentaire moyen genere precedemment pour ce post:

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
            prompt=f"""Voici un commentaire long genere precedemment pour ce post:

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
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Commentaires LinkedIn (Révisés)\n\n")
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
        job["error"] = str(e)


# === PAGE & API: TECH WATCH ===

@app.get("/techwatch")
async def techwatch_page():
    """Redirection vers la nouvelle page veille"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/veille", status_code=301)


@app.post("/api/techwatch/generate")
@limiter.limit("3/minute")
async def api_techwatch_generate(request: Request):
    """Lance la génération d'un digest de veille tech"""
    body = await request.json()
    keywords_str = body.get("keywords", "").strip()
    keywords = [k.strip() for k in keywords_str.split(',')] if keywords_str else None
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
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Veille Technologique {period_type.capitalize()}\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"**Période:** {days} derniers jours\n")
            f.write(f"**Articles:** {len(articles)}\n\n")
            f.write("---\n\n")
            f.write(result['content'])

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
        job["error"] = str(e)


@app.get("/api/techwatch/stream/{job_id}")
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


# === API: TECH WATCH FEEDBACK ===

@app.post("/api/techwatch/regenerate")
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


def _run_techwatch_feedback(job_id: str, previous_digest: str, feedback: str, num_articles: int, period: str):
    """Regenere le digest en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        agent = TechMonitorAgent()

        job["steps"].append({"step": "collect", "status": "done", "progress": 20})
        job["steps"].append({"step": "analyze", "status": "done", "progress": 40})
        job["steps"].append({"step": "generate", "status": "active", "progress": 50})

        system_prompt = f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un digest de veille technologique selon le retour du consultant."""

        # Regenerer le digest
        revised_digest = agent.llm_client.generate(
            prompt=f"""Voici un digest de veille technologique généré précédemment:

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
        with open(md_path, 'w', encoding='utf-8') as f:
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
        job["error"] = str(e)


# === PAGE & API: DATASET ANALYZER ===

@app.get("/dataset", response_class=HTMLResponse)
async def dataset_page(request: Request):
    return templates.TemplateResponse("dataset.html", {
        "request": request,
        "active": "dataset",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/dataset/analyze")
@limiter.limit("5/minute")
async def api_dataset_analyze(request: Request, file: UploadFile = File(...)):
    """Lance l'analyse d'un dataset"""

    # Vérifier le type de fichier
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.csv', '.xlsx', '.xls']:
        return JSONResponse({"error": "Format non supporté. Utilisez CSV ou Excel."}, status_code=400)

    # Sauvegarder temporairement le fichier
    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = temp_dir / f"upload_{timestamp}_{filename}"

    content = await file.read()
    with open(temp_path, 'wb') as f:
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
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result['report'])

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
        except:
            pass

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        # Nettoyer le fichier temporaire en cas d'erreur
        try:
            if "temp_file" in job:
                os.remove(job["temp_file"])
        except:
            pass


@app.get("/api/dataset/stream/{job_id}")
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


# === API: DATASET FEEDBACK ===

@app.post("/api/dataset/regenerate")
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

        system_prompt = f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un rapport d'analyse de dataset selon le retour du consultant."""

        # Regenerer le rapport
        revised_report = agent.llm_client.generate(
            prompt=f"""Voici un rapport d'analyse de dataset généré précédemment:

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
        with open(md_path, 'w', encoding='utf-8') as f:
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
        job["error"] = str(e)


# === PAGE & API: WORKSHOP PLANNER ===

@app.get("/workshop", response_class=HTMLResponse)
async def workshop_page(request: Request):
    return templates.TemplateResponse("workshop.html", {
        "request": request,
        "active": "workshop",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/workshop/generate")
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
        target=_run_workshop_planner, args=(job_id, topic, duration, audience, objectives), daemon=True
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

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        safe_topic = safe_topic.replace(' ', '_')

        md_path = output_dir / f"workshop_{safe_topic}_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result['plan'])

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
        job["error"] = str(e)


@app.get("/api/workshop/stream/{job_id}")
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


@app.post("/api/workshop/regenerate")
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

        system_prompt = f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges un plan de formation selon le retour du consultant."""

        revised_plan = agent.llm_client.generate(
            prompt=f"""Voici un plan de workshop généré précédemment:

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

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        safe_topic = safe_topic.replace(' ', '_')

        md_path = output_dir / f"workshop_{safe_topic}_{timestamp}_revised.md"
        with open(md_path, 'w', encoding='utf-8') as f:
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
        job["error"] = str(e)


# === PAGE & API: RFP RESPONDER ===

@app.get("/rfp", response_class=HTMLResponse)
async def rfp_page(request: Request):
    return templates.TemplateResponse("rfp.html", {
        "request": request,
        "active": "rfp",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/rfp/generate")
@limiter.limit("3/minute")
async def api_rfp_generate(
    request: Request,
    rfp_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la génération de réponse au RFP"""
    text = ""

    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(
                page.extract_text() or "" for page in pdf_reader.pages
            )
        else:
            text = content.decode("utf-8")
    elif rfp_text:
        text = rfp_text
    else:
        return JSONResponse({"error": "Aucun RFP fourni."}, status_code=400)

    if len(text.strip()) < 100:
        return JSONResponse({"error": "Le RFP semble trop court."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "rfp",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_rfp_responder, args=(job_id, text), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


def _run_rfp_responder(job_id: str, rfp_text: str):
    """Execute la génération en background"""
    job = jobs[job_id]

    try:
        agent = RFPResponderAgent()

        # Step 1: Analyze
        job["steps"].append({"step": "analyze", "status": "active", "progress": 20})
        analysis = agent.analyze_rfp(rfp_text)
        job["steps"].append({"step": "analyze", "status": "done", "progress": 40})

        # Step 2: Generate response
        job["steps"].append({"step": "response", "status": "active", "progress": 50})
        result = agent.generate_response(rfp_text, analysis)
        job["steps"].append({"step": "response", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"rfp_response_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Réponse à l'appel d'offres\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("---\n\n")
            f.write(result['response'])

        job["status"] = "done"
        job["result"] = {
            "response": result["response"],
            "analysis": analysis,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/rfp/stream/{job_id}")
async def api_rfp_stream(job_id: str):
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


@app.post("/api/rfp/regenerate")
async def api_rfp_regenerate(request: Request):
    """Regenere avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_response = body.get("previous_response", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "rfp",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_rfp_feedback,
        args=(job_id, previous_response, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_rfp_feedback(job_id: str, previous_response: str, feedback: str):
    """Regenere avec feedback"""
    job = jobs[job_id]

    try:
        agent = RFPResponderAgent()

        job["steps"].append({"step": "analyze", "status": "done", "progress": 30})
        job["steps"].append({"step": "response", "status": "active", "progress": 50})

        system_prompt = f"""Tu es {agent.consultant_info['name']}, {agent.consultant_info['title']} chez {agent.consultant_info['company']}.
Tu corriges une réponse à un appel d'offres selon le retour du consultant."""

        revised_response = agent.llm_client.generate(
            prompt=f"""Voici une réponse à un RFP générée précédemment:

{previous_response}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Reécris cette réponse en intégrant les corrections demandées.
Conserve le format Markdown et la structure en 10 sections.
Ne modifie que ce qui est demandé dans le feedback.""",
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4000,
        )

        job["steps"].append({"step": "response", "status": "done", "progress": 100})

        # Sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"rfp_response_{timestamp}_revised.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(revised_response)

        job["status"] = "done"
        job["result"] = {
            "response": revised_response,
            "md_path": str(md_path.relative_to(BASE_DIR)),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# === PAGE & API: ARTICLE GENERATOR ===

@app.get("/article-generator", response_class=HTMLResponse)
async def article_generator_page(request: Request):
    return templates.TemplateResponse("article-generator.html", {
        "request": request,
        "active": "article-generator",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/article-generator/generate")
@limiter.limit("5/minute")
async def api_article_generator_generate(
    request: Request,
    idea_text: str = Form(...),
    use_context: bool = Form(False),
):
    """Lance la génération d'un article de blog"""
    if len(idea_text.strip()) < 20:
        return JSONResponse({"error": "L'idée est trop courte (minimum 20 caractères)."}, status_code=400)

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
        job["error"] = str(e)


@app.get("/api/article-generator/stream/{job_id}")
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


@app.post("/api/article-generator/regenerate")
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


def _run_article_generator_feedback(job_id: str, previous_content: str, feedback: str, previous_idea: str):
    """Régénère l'article en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        from agents.article_generator import ArticleGeneratorAgent
        agent = ArticleGeneratorAgent()

        job["steps"].append({"step": "generate", "status": "active", "progress": 20})

        revised_prompt = f"""{previous_idea}

CONTEXTE : Voici l'article précédent que tu as généré:

{previous_content}

FEEDBACK de l'utilisateur:
{feedback}

Régénère l'article en tenant compte du feedback. Applique les modifications demandées tout en gardant le style et la qualité Wenvision."""

        revised_content = agent.generate_article(revised_prompt, target_length="medium")

        # Générer le nouveau prompt d'illustration
        illustration_prompt = agent.generate_illustration_prompt(revised_content)

        job["steps"].append({"step": "generate", "status": "done", "progress": 100})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        # Créer un slug pour le nom de fichier
        import re
        slug = re.sub(r'[^\w\s-]', '', previous_idea.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:50]

        md_path = output_dir / f"article_{slug}_revised_{timestamp}.md"

        # Ajouter les métadonnées
        full_article = f"""---
title: {previous_idea}
author: {CONSULTANT_NAME}
company: {COMPANY_NAME}
date: {datetime.now().strftime('%Y-%m-%d')}
revised: true
illustration_prompt: |
  {illustration_prompt}
---

{revised_content}
"""

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
        job["error"] = str(e)


# ====================================
# FORMATION GENERATOR
# ====================================

@app.get("/formation", response_class=HTMLResponse)
async def formation_page(request: Request):
    return templates.TemplateResponse("formation.html", {
        "request": request,
        "active": "formation",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/formation/generate")
@limiter.limit("5/minute")
async def api_formation_generate(
    request: Request,
    client_needs: str = Form(...),
):
    """Lance la génération d'un programme de formation"""
    if len(client_needs.strip()) < 20:
        return JSONResponse({"error": "Le besoin est trop court (minimum 20 caractères)."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "formation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_formation_generator,
        args=(job_id, client_needs),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_formation_generator(job_id: str, client_needs: str):
    """Génère le programme de formation en background"""
    job = jobs[job_id]

    try:
        from agents.formation_generator import FormationGeneratorAgent
        agent = FormationGeneratorAgent()

        job["steps"].append({"step": "analyze", "status": "active", "progress": 10})
        job["steps"].append({"step": "analyze", "status": "done", "progress": 20})
        job["steps"].append({"step": "generate", "status": "active", "progress": 30})

        result = agent.generate_programme(client_needs)

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "format", "status": "active", "progress": 85})

        # Sauvegarder le markdown
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        title = result["metadata"].get("title", "Programme_Formation")
        safe_title = title.replace(" ", "_").replace("/", "-")[:50]
        md_path = output_dir / f"formation_{safe_title}_{timestamp}.md"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        job["steps"].append({"step": "format", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "content": result["markdown"],
            "metadata": result["metadata"],
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/formation/stream/{job_id}")
async def api_formation_stream(job_id: str):
    """SSE stream pour la progression de la génération de formation"""

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


@app.post("/api/formation/regenerate")
async def api_formation_regenerate(request: Request):
    """Régénère le programme avec feedback"""
    body = await request.json()
    feedback = body.get("feedback", "").strip()
    previous_content = body.get("previous_content", "")

    if not feedback:
        return JSONResponse({"error": "Aucun feedback fourni."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "formation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_formation_regenerate,
        args=(job_id, previous_content, feedback),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_formation_regenerate(job_id: str, previous_content: str, feedback: str):
    """Régénère le programme en tenant compte du feedback"""
    job = jobs[job_id]

    try:
        from agents.formation_generator import FormationGeneratorAgent
        agent = FormationGeneratorAgent()

        job["steps"].append({"step": "generate", "status": "active", "progress": 20})

        result = agent.regenerate_with_feedback(previous_content, feedback)

        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "format", "status": "active", "progress": 85})

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / f"formation_revised_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown"])

        job["steps"].append({"step": "format", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "content": result["markdown"],
            "metadata": result["metadata"],
            "md_path": str(md_path.relative_to(BASE_DIR)),
        }

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.post("/api/formation/export-gdocs")
@limiter.limit("5/minute")
async def api_formation_export_gdocs(
    request: Request,
    content: str = Form(...),
    title: str = Form("Programme de Formation"),
):
    """Exporte le programme de formation vers Google Docs"""
    try:
        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            doc_url = google_client.export_markdown_to_docs(content, title)

            if doc_url:
                return JSONResponse({
                    "doc_url": doc_url,
                    "message": "Document Google Docs créé avec succès"
                })
            else:
                return JSONResponse(
                    {"error": "Échec de la création du document Google Docs"},
                    status_code=500
                )

        except Exception as e:
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse({
                    "error": "Google API non configurée. Configurez vos credentials dans config/google_credentials.json",
                    "setup_required": True
                }, status_code=400)
            else:
                raise

    except Exception as e:
        import traceback
        print(f"Error in export to Google Docs: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ====================================
# TRAINING SLIDES GENERATOR
# ====================================

@app.get("/training-slides", response_class=HTMLResponse)
async def training_slides_page(request: Request):
    return templates.TemplateResponse("training-slides.html", {
        "request": request,
        "active": "training-slides",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/training-slides/generate")
@limiter.limit("3/minute")
async def api_training_slides_generate(
    request: Request,
    programme_text: str = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Lance la génération des slides de formation (supporte TXT, MD, DOCX, PDF)"""
    from utils.document_parser import document_parser

    # Récupérer le texte du programme
    text = ""
    if file:
        # Sauvegarder temporairement le fichier
        temp_file = BASE_DIR / "output" / f"temp_{file.filename}"
        temp_file.parent.mkdir(exist_ok=True)

        try:
            content = await file.read()
            with open(temp_file, 'wb') as f:
                f.write(content)

            # Extraire le texte selon le format
            text = document_parser.parse_file(str(temp_file))

            # Supprimer le fichier temporaire
            temp_file.unlink()

            if not text:
                return JSONResponse({
                    "error": f"Impossible d'extraire le texte du fichier {file.filename}. Formats supportés : TXT, MD, DOCX, PDF (avec PyPDF2 ou python-docx installés)"
                }, status_code=400)

        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            return JSONResponse({"error": f"Erreur lors de la lecture du fichier : {str(e)}"}, status_code=400)

    elif programme_text:
        text = programme_text.strip()

    if not text or len(text) < 50:
        return JSONResponse({"error": "Le programme est trop court (minimum 50 caractères)."}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "training-slides",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_training_slides_generator,
        args=(job_id, text),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_training_slides_generator(job_id: str, programme_text: str):
    """Génère les slides de formation en background"""
    job = jobs[job_id]

    try:
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        agent = TrainingSlidesGeneratorAgent()

        job["steps"].append({"step": "parse", "status": "active", "progress": 10})

        result = agent.generate_all_slides(programme_text)

        job["steps"].append({"step": "parse", "status": "done", "progress": 30})
        job["steps"].append({"step": "generate", "status": "done", "progress": 80})
        job["steps"].append({"step": "pptx", "status": "active", "progress": 85})

        # Générer les PPTX par module
        pptx_paths = {}
        for module_name, module_slides in result["modules_slides"].items():
            if module_slides:
                pptx_path = agent.generate_module_pptx(module_slides, module_name)
                pptx_paths[module_name] = pptx_path

        # Générer le PPTX complet
        all_pptx_path = agent.generate_module_pptx(result["all_slides"], "Complet")

        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = {
            "programme_data": result["programme_data"],
            "modules_slides": {k: v for k, v in result["modules_slides"].items()},
            "all_slides": result["all_slides"],
            "total_slides": result["total_slides"],
            "pptx_paths": pptx_paths,
            "all_pptx_path": all_pptx_path,
        }

    except Exception as e:
        import traceback
        print(f"Error in training slides: {traceback.format_exc()}")
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/training-slides/stream/{job_id}")
async def api_training_slides_stream(job_id: str):
    """SSE stream pour la progression des slides de formation"""

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


@app.post("/api/training-slides/export-slides")
@limiter.limit("3/minute")
async def api_training_slides_export(
    request: Request,
    slides_data: str = Form(...),
    title: str = Form("Support de Formation"),
):
    """Exporte les slides de formation vers Google Slides"""
    try:
        import re
        # Sanitize pour éviter les erreurs JSON (supprime les caractères de contrôle)
        sanitized = slides_data.strip()
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)

        slides = json.loads(sanitized)

        from utils.google_api import GoogleAPIClient

        try:
            google_client = GoogleAPIClient()
            presentation_id = google_client.export_pptx_to_slides(
                slides_data=slides,
                title=title
            )

            if presentation_id:
                presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
                return JSONResponse({
                    "presentation_id": presentation_id,
                    "presentation_url": presentation_url,
                    "message": "Présentation Google Slides créée avec succès"
                })
            else:
                return JSONResponse(
                    {"error": "Échec de la création de la présentation"},
                    status_code=500
                )

        except Exception as e:
            if "credentials" in str(e).lower() or "token" in str(e).lower():
                return JSONResponse({
                    "error": "Google API non configurée.",
                    "setup_required": True
                }, status_code=400)
            else:
                raise

    except Exception as e:
        import traceback
        print(f"Error in training slides export: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === API: DOWNLOAD ===

@app.get("/api/download")
async def api_download(path: str):
    """Telecharge un fichier genere"""
    try:
        # Nettoyer le path pour éviter les problèmes d'encodage
        path = path.strip()
        file_path = BASE_DIR / path

        # Vérifier que le fichier existe
        if not file_path.exists():
            print(f"Fichier non trouve: {file_path}")
            return JSONResponse({"error": "Fichier non trouve"}, status_code=404)

        # Vérifier que le fichier est bien dans le répertoire BASE_DIR (sécurité)
        if not file_path.is_relative_to(BASE_DIR):
            print(f"Tentative d'accès à un fichier hors du répertoire autorisé: {file_path}")
            return JSONResponse({"error": "Accès non autorisé"}, status_code=403)

        # Déterminer le type MIME en fonction de l'extension
        media_type = None
        if file_path.suffix == '.pptx':
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif file_path.suffix == '.pdf':
            media_type = "application/pdf"
        elif file_path.suffix == '.md':
            media_type = "text/markdown"
        elif file_path.suffix == '.json':
            media_type = "application/json"
        elif file_path.suffix == '.png':
            media_type = "image/png"
        elif file_path.suffix == '.jpg' or file_path.suffix == '.jpeg':
            media_type = "image/jpeg"

        # Retourner le fichier avec les bons headers
        # Pour les images (PNG, JPG), utiliser inline pour affichage dans le navigateur
        disposition = "inline" if file_path.suffix in ['.png', '.jpg', '.jpeg'] else "attachment"

        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type=media_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{file_path.name}"',
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        print(f"Erreur lors du téléchargement: {e}")
        return JSONResponse({"error": f"Erreur lors du téléchargement: {str(e)}"}, status_code=500)


@app.post("/api/convert-to-pdf")
async def api_convert_to_pdf(request: Request):
    """
    Convertit un fichier PPTX ou Markdown en PDF

    Body JSON:
        - file_path: Chemin relatif du fichier à convertir (PPTX ou MD)
        - file_type: Type de fichier ('pptx' ou 'markdown')
    """
    try:
        from utils.pdf_converter import pdf_converter

        body = await request.json()
        file_path = body.get('file_path', '').strip()
        file_type = body.get('file_type', 'pptx')

        if not file_path:
            return JSONResponse({"error": "Chemin de fichier manquant"}, status_code=400)

        # Chemin absolu
        full_path = BASE_DIR / file_path

        if not full_path.exists():
            return JSONResponse({"error": "Fichier non trouvé"}, status_code=404)

        # Vérifier la sécurité
        if not full_path.is_relative_to(BASE_DIR):
            return JSONResponse({"error": "Accès non autorisé"}, status_code=403)

        # Convertir selon le type
        pdf_path = None
        if file_type == 'pptx' and full_path.suffix == '.pptx':
            pdf_path = pdf_converter.pptx_to_pdf(str(full_path))
        elif file_type == 'markdown' and full_path.suffix in ['.md', '.markdown']:
            pdf_path = pdf_converter.markdown_to_pdf(str(full_path))
        else:
            return JSONResponse({"error": "Type de fichier non supporté"}, status_code=400)

        if pdf_path:
            # Retourner le chemin relatif du PDF
            pdf_rel_path = str(Path(pdf_path).relative_to(BASE_DIR))
            return {
                "success": True,
                "pdf_path": pdf_rel_path,
                "message": "Conversion réussie"
            }
        else:
            return JSONResponse({
                "error": "Conversion PDF échouée",
                "message": "Vérifiez que LibreOffice est installé (pour PPTX) ou pandoc/weasyprint (pour Markdown)"
            }, status_code=500)

    except Exception as e:
        print(f"Erreur lors de la conversion PDF: {e}")
        return JSONResponse({"error": f"Erreur: {str(e)}"}, status_code=500)


@app.get("/api/pdf-capabilities")
async def api_pdf_capabilities():
    """Retourne les capacités de conversion PDF disponibles"""
    try:
        from utils.pdf_converter import pdf_converter
        capabilities = pdf_converter.is_pdf_conversion_available()
        return {
            "capabilities": capabilities,
            "message": "Pour activer la conversion PDF, installez LibreOffice (PPTX→PDF) ou pandoc/weasyprint (MD→PDF)"
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ===================================
# DOCUMENT TO PRESENTATION
# ===================================

@app.get("/doc-to-presentation", response_class=HTMLResponse)
async def doc_to_presentation_page(request: Request):
    return templates.TemplateResponse("doc-to-presentation.html", {
        "request": request,
        "active": "doc-to-presentation",
        "consultant_name": CONSULTANT_NAME,
    })

@app.post("/api/doc-to-presentation/generate")
async def api_doc_to_presentation_generate(
    request: Request,
    target_audience: str = Form(...),
    objective: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """Lance la generation de presentation a partir de documents"""
    if not files:
        return JSONResponse({"error": "Aucun fichier fourni."}, status_code=400)

    # Lire les fichiers uploades
    documents = []
    for f in files:
        content = await f.read()
        documents.append({"filename": f.filename, "content": content})

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "doc-to-presentation",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_doc_to_presentation,
        args=(job_id, documents, target_audience, objective),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_doc_to_presentation(job_id: str, documents: list, target_audience: str, objective: str):
    """Execute la generation de presentation en background"""
    job = jobs[job_id]
    try:
        from agents.doc_to_presentation import DocToPresentationAgent
        agent = DocToPresentationAgent()

        job["steps"].append({"step": "parse", "status": "active", "progress": 10})
        result = agent.run(documents, target_audience, objective)
        job["steps"].append({"step": "pptx", "status": "done", "progress": 100})

        if result.get("error"):
            job["status"] = "error"
            job["error"] = result["error"]
        else:
            job["status"] = "done"
            job["result"] = result

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/doc-to-presentation/stream/{job_id}")
async def api_doc_to_presentation_stream(job_id: str):
    """SSE stream pour la progression"""
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ===================================
# PROPOSAL CANVA (Mode Gemini)
# ===================================

@app.get("/proposal-canva")
async def proposal_canva_page(request: Request):
    """Page de génération de propositions en mode Canva (conversationnel avec Gemini)"""
    return templates.TemplateResponse(
        "proposal-canva.html",
        {
            "request": request,
            "consultant_name": CONSULTANT_NAME,
            "active": "proposal"
        }
    )


@app.post("/api/proposal-canva/generate")
async def api_proposal_canva_generate(request: Request):
    """Génère des propositions en mode conversationnel avec Gemini"""
    try:
        data = await request.json()
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        current_proposal = data.get('current_proposal')

        if not user_message:
            return JSONResponse({"error": "Message manquant"}, status_code=400)

        # Initialiser le client Gemini
        from utils.llm_client import LLMClient
        llm = LLMClient(provider='gemini', model='gemini-3-flash-preview')

        # System prompt pour le mode conversationnel
        system_prompt = f"""Tu es un assistant expert en propositions commerciales pour {COMPANY_NAME}.
Tu aides les consultants à créer des propositions professionnelles de manière conversationnelle.

INSTRUCTIONS:
1. Analyse la demande de l'utilisateur
2. Si c'est la première fois, demande le contexte de l'appel d'offres
3. Génère des slides structurées en JSON selon le besoin
4. Réponds de manière naturelle et conversationnelle
5. Propose des améliorations si nécessaire

FORMAT DE SORTIE:
- Si tu génères des slides, utilise ce format JSON à la fin de ta réponse:
```json
{{
  "slides": [
    {{"type": "cover", "title": "...", "subtitle": "..."}},
    {{"type": "content", "title": "...", "bullets": ["...", "..."]}},
    {{"type": "diagram", "title": "...", "diagram_type": "flow", "elements": ["..."]}},
    {{"type": "stat", "stat_value": "67%", "stat_label": "de ROI", "context": "..."}},
    {{"type": "quote", "quote_text": "...", "author": "..."}},
    {{"type": "highlight", "title": "...", "key_points": ["...", "..."]}}
  ]
}}
```

TYPES DE SLIDES DISPONIBLES:
- cover: Slide de couverture (title, subtitle)
- section: Séparateur de section (title)
- content: Contenu avec bullets (title, bullets)
- diagram: Diagramme visuel (title, diagram_type, elements, description)
- stat: Statistique impactante (stat_value, stat_label, context, subtitle)
- quote: Citation/message clé (quote_text, author, title)
- highlight: Points clés en encadrés (title, key_points, highlight_color)
- closing: Slide de clôture

Consultant: {CONSULTANT_NAME}
Société: {COMPANY_NAME}
"""

        # Construire les messages pour l'API
        messages = []
        for msg in conversation_history:
            if msg['role'] in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # Ajouter le nouveau message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Générer la réponse
        response_text = llm.generate_with_context(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=8000
        )

        # Extraire le JSON s'il existe
        slides = []
        pptx_path = None

        if '```json' in response_text:
            # Extraire le JSON
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            json_str = response_text[json_start:json_end].strip()

            try:
                slides_data = json.loads(json_str)
                slides = slides_data.get('slides', [])

                # Générer le PPTX si des slides sont présentes
                if slides:
                    from utils.pptx_generator import build_proposal_pptx

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_dir = BASE_DIR / "output"
                    output_dir.mkdir(exist_ok=True)

                    output_path = output_dir / f"proposal_canva_{timestamp}.pptx"

                    consultant_info = {
                        'name': CONSULTANT_NAME,
                        'company': COMPANY_NAME
                    }

                    pptx_path = build_proposal_pptx(
                        template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
                        slides_data=slides,
                        output_path=str(output_path),
                        consultant_info=consultant_info
                    )

                    pptx_path = str(Path(pptx_path).relative_to(BASE_DIR))

            except json.JSONDecodeError as e:
                print(f"❌ Erreur JSON: {e}")
                # Continue sans slides

        # Nettoyer la réponse (enlever le JSON)
        response_text_clean = response_text.split('```json')[0].strip()

        # Mettre à jour l'historique
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": response_text_clean})

        return {
            "response": response_text_clean,
            "slides": slides,
            "pptx_path": pptx_path,
            "conversation_history": conversation_history
        }

    except Exception as e:
        print(f"❌ Erreur génération Canva: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/proposal-canva/generate-section")
async def api_proposal_canva_generate_section(request: Request):
    """Génère une section spécifique de proposition (mode modulaire)"""
    try:
        data = await request.json()
        section = data.get('section', '')
        tender_text = data.get('tender_text', '')
        current_proposal = data.get('current_proposal')

        if not section or not tender_text:
            return JSONResponse({"error": "Section et tender_text requis"}, status_code=400)

        # Initialiser le client Gemini
        from utils.llm_client import LLMClient
        llm = LLMClient(provider='gemini', model='gemini-3-flash-preview')

        # Mapping des sections
        section_prompts = {
            'cover': 'Génère une slide de couverture professionnelle',
            'agenda': 'Génère une slide d\'agenda avec la structure de la proposition',
            'context': 'Génère 2-3 slides de contexte avec les enjeux et objectifs',
            'approach': 'Génère 3-4 slides d\'approche méthodologique',
            'planning': 'Génère 2-3 slides de planning avec les phases',
            'budget': 'Génère 1-2 slides de chiffrage avec estimation budgétaire',
            'references': 'Génère 2-3 slides de références projets similaires',
            'cvs': 'Génère 2-3 slides de CVs adaptés au projet'
        }

        section_instruction = section_prompts.get(section, f'Génère des slides pour la section {section}')

        # System prompt
        system_prompt = f"""Tu es un expert en propositions commerciales pour {COMPANY_NAME}.

Génère des slides pour la section "{section}" basées sur cet appel d'offres :

{tender_text[:3000]}

INSTRUCTION: {section_instruction}

FORMAT DE SORTIE - JSON uniquement:
```json
{{
  "slides": [
    {{"type": "content", "title": "...", "bullets": ["...", "..."]}},
    {{"type": "diagram", "title": "...", "diagram_type": "flow", "elements": ["..."]}},
    {{"type": "stat", "stat_value": "67%", "stat_label": "...", "context": "..."}},
    {{"type": "quote", "quote_text": "...", "author": "..."}},
    {{"type": "highlight", "title": "...", "key_points": ["...", "..."]}}
  ]
}}
```

TYPES DE SLIDES:
- cover: couverture (title, subtitle, client_name, project_name)
- section: séparateur (title, section_number)
- content: contenu avec bullets (title, bullets)
- diagram: diagramme (title, diagram_type, elements, description)
- stat: statistique impactante (stat_value, stat_label, context)
- quote: citation (quote_text, author, title)
- highlight: points clés (title, key_points, highlight_color)

Consultant: {CONSULTANT_NAME}
Société: {COMPANY_NAME}
"""

        # Générer la réponse
        response_text = llm.generate(
            prompt=f"Génère les slides pour la section {section}",
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4000
        )

        # Extraire le JSON
        slides = []
        pptx_path = None

        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            json_str = response_text[json_start:json_end].strip()

            try:
                slides_data = json.loads(json_str)
                slides = slides_data.get('slides', [])

                # Générer le PPTX si des slides sont présentes
                if slides:
                    from utils.pptx_generator import build_proposal_pptx

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_dir = BASE_DIR / "output"
                    output_dir.mkdir(exist_ok=True)

                    output_path = output_dir / f"proposal_section_{section}_{timestamp}.pptx"

                    consultant_info = {
                        'name': CONSULTANT_NAME,
                        'company': COMPANY_NAME
                    }

                    pptx_path = build_proposal_pptx(
                        template_path=str(BASE_DIR / "WENVISION_Template_Palette 2026.pptx"),
                        slides_data=slides,
                        output_path=str(output_path),
                        consultant_info=consultant_info
                    )

                    pptx_path = str(Path(pptx_path).relative_to(BASE_DIR))

            except json.JSONDecodeError as e:
                print(f"❌ Erreur JSON section: {e}")
                return JSONResponse({"error": "Erreur parsing JSON"}, status_code=500)

        return {
            "response": f"✅ Section '{section}' générée avec succès ({len(slides)} slides)",
            "slides": slides,
            "pptx_path": pptx_path,
            "section": section
        }

    except Exception as e:
        print(f"❌ Erreur génération section: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


# === SLIDE EDITOR (HTML-First) ===

@app.get("/slide-editor", response_class=HTMLResponse)
async def slide_editor_page(request: Request):
    return templates.TemplateResponse("slide-editor.html", {
        "request": request,
        "active": "slide-editor",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/slide-editor/parse-document")
async def api_slide_editor_parse_document(file: UploadFile = File(...)):
    """Parse un document uploade et retourne son contenu texte (ou chemin pour PPTX)"""
    try:
        content = await file.read()
        filename = file.filename or "document.txt"
        ext = Path(filename).suffix.lower()

        if ext in ('.md', '.txt'):
            text = content.decode('utf-8')
        elif ext == '.pdf':
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        elif ext == '.docx':
            from docx import Document as DocxDocument
            import io
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif ext == '.pptx':
            # Pour PPTX: sauvegarder temporairement le fichier et retourner le chemin
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "wenvision_uploads"
            temp_dir.mkdir(exist_ok=True)

            temp_path = temp_dir / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            with open(temp_path, 'wb') as f:
                f.write(content)

            # Retourner le chemin au lieu du texte
            return {"text": str(temp_path), "filename": filename, "length": len(content), "is_pptx": True}
        else:
            return JSONResponse({"error": f"Format non supporte: {ext}"}, status_code=400)

        return {"text": text, "filename": filename, "length": len(text)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def _generate_slide_illustrations(slides, job, topic, gen_type="presentation"):
    """Add Nano Banana image generation prompts to relevant slides (no actual image generation)"""
    try:
        # Slide types that benefit from illustrations
        visual_types = ["content", "highlight", "stat", "diagram", "image", "two_column"]

        # Context adapte au type de generation
        context_map = {
            "formation": "training presentation",
            "proposal": "business proposal",
            "rex": "experience feedback presentation",
            "presentation": "business presentation"
        }
        context = context_map.get(gen_type, "business presentation")

        for idx, slide in enumerate(slides):
            slide_type = slide.get("type", "")

            # Skip non-visual slides
            if slide_type not in visual_types:
                continue

            # Skip if already has an image or image_prompt
            if slide.get("image") or slide.get("image_prompt"):
                continue

            # Generate prompt for the slide (Nano Banana format)
            title = slide.get("title", "")
            content = slide.get("content", "")
            bullets = slide.get("bullets", [])
            key_points = slide.get("key_points", [])

            # Prompt adapte au type
            if gen_type == "formation":
                prompt = f"""Create a premium, professional illustration for a training presentation slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {', '.join(bullets[:3] if bullets else key_points[:3])}

Style: Educational yet professional, Unreal Engine 5 render, engaging and clear.
Colors: Cool blues, warm amber/gold accents, approachable palette.
Mood: Pedagogical, inspiring, professional learning environment.
Format: Wide 16:9, 1792x1024px."""
            elif gen_type == "proposal":
                prompt = f"""Create a premium, professional illustration for a business proposal slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {', '.join(bullets[:3] if bullets else key_points[:3])}

Style: High-end corporate, Unreal Engine 5 render, sophisticated and impactful.
Colors: Premium blues, gold/amber accents, executive palette.
Mood: Professional, trustworthy, results-oriented, winning proposal aesthetic.
Format: Wide 16:9, 1792x1024px."""
            else:
                prompt = f"""Create a premium, professional illustration for a {context} slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {', '.join(bullets[:3] if bullets else key_points[:3])}

Style: Corporate tech aesthetic, Unreal Engine 5 render, clean and modern.
Colors: Cool blues, warm amber/gold accents, professional palette.
Mood: Sophisticated, futuristic but grounded, business presentation quality.
Format: Wide 16:9, 1792x1024px."""

            # Add prompt and dimensions to slide (for Nano Banana generation)
            slide["image_prompt"] = prompt.strip()
            slide["image_dimensions"] = "1792x1024px (16:9)"
            job["steps"].append({"message": f"Prompt Nano Banana ajoute pour slide {idx+1}", "step": 4})

    except Exception as e:
        print(f"  Erreur ajout prompts illustrations: {e}")
        # Non-blocking - continue sans prompts


def _extract_slides_from_buffer(buffer, job):
    """Parse complete JSON slide objects from a partial LLM response buffer.
    Adds newly found slides to job['slides'] incrementally."""
    # Find the slides array content
    content = buffer
    # Strip markdown fences
    if '```json' in content:
        content = content.split('```json', 1)[1]
        if '```' in content:
            content = content.rsplit('```', 1)[0]
    elif '```' in content:
        parts = content.split('```')
        if len(parts) >= 2:
            content = parts[1]

    # Find the "slides" array or top-level array
    start = -1
    for marker in ['"slides"', "'slides'"]:
        idx = content.find(marker)
        if idx != -1:
            bracket = content.find('[', idx)
            if bracket != -1:
                start = bracket
                break

    if start == -1:
        # Maybe it's a top-level array
        bracket = content.find('[')
        if bracket != -1:
            start = bracket
        else:
            return

    # Extract individual slide objects by tracking brace depth
    existing_count = len(job["slides"])
    obj_start = -1
    depth = 0
    slide_count = 0

    for i in range(start, len(content)):
        c = content[i]
        if c == '{':
            if depth == 0:
                obj_start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and obj_start != -1:
                slide_count += 1
                if slide_count > existing_count:
                    # New slide found - try to parse it
                    obj_str = content[obj_start:i + 1]
                    try:
                        slide = json.loads(obj_str)
                        if isinstance(slide, dict) and ("type" in slide or "title" in slide):
                            job["slides"].append(slide)
                    except json.JSONDecodeError:
                        pass
                obj_start = -1


@app.post("/api/slide-editor/start-generate")
async def api_slide_editor_start_generate(request: Request):
    """Demarre la generation de slides en arriere-plan et retourne un job_id"""
    data = await request.json()
    topic = data.get("topic", "")
    audience = data.get("audience", "")
    slide_count = data.get("slide_count", 10)
    gen_type = data.get("type", "presentation")
    model = data.get("model", "")
    document_text = data.get("document_text", "")
    feedback = data.get("feedback", "")
    previous_slides = data.get("previous_slides", "")

    job_id = f"slide_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(data) % 10000}"

    jobs[job_id] = {
        "type": "slide-editor",
        "status": "running",
        "steps": [],
        "slides": [],
        "result": None,
        "error": None,
    }

    def run_generation():
        job = jobs[job_id]
        try:
            job["steps"].append({"message": "Initialisation du modele...", "step": 0})

            from utils.llm_client import LLMClient
            llm_kwargs = {"max_tokens": 8192}
            if model:
                llm_kwargs["model"] = model
                llm_kwargs["provider"] = "gemini"
            llm = LLMClient(**llm_kwargs)

            consultant_name = os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha')
            company_name = os.getenv('COMPANY_NAME', 'Wenvision')
            json_format = _get_slide_json_format()

            job["steps"].append({"message": "Construction du prompt...", "step": 1})

            # Load references and CVs for proposals
            ref_context = ""
            cv_context = ""
            if gen_type == "proposal":
                try:
                    references_path = Path(BASE_DIR) / "data" / "notebooklm" / "references.json"
                    if references_path.exists():
                        with open(references_path, 'r', encoding='utf-8') as f:
                            refs = json.load(f)
                        ref_context = f"\nREFERENCES WENVISION :\n{json.dumps(refs.get('projects', []), indent=2, ensure_ascii=False)[:3000]}"
                        ref_context += f"\nEXPERTISE : {json.dumps(refs.get('expertise', []), ensure_ascii=False)[:1000]}"
                        ref_context += f"\nMETHODOLOGIES : {json.dumps(refs.get('methodologies', []), ensure_ascii=False)[:1000]}"
                except Exception as e:
                    print(f"  Erreur chargement references: {e}")

                try:
                    bio_path = Path(BASE_DIR) / "Biographies - CV All WEnvision.pptx"
                    if bio_path.exists():
                        from pptx import Presentation as PptxPres
                        prs = PptxPres(str(bio_path))
                        cvs = []
                        for slide in prs.slides:
                            texts = []
                            for shape in slide.shapes:
                                if shape.has_text_frame:
                                    for p in shape.text_frame.paragraphs:
                                        if p.text.strip():
                                            texts.append(p.text.strip())
                            full = "\n".join(texts)
                            if len(full) > 50:
                                cvs.append(full)
                        if cvs:
                            cv_context = f"\nCVs EQUIPE WENVISION :\n" + "\n---\n".join(cvs[:5])[:3000]
                except Exception as e:
                    print(f"  Erreur chargement CVs: {e}")

            if gen_type == "proposal":
                system_prompt = _get_proposal_system_prompt(company_name)
                prompt = _get_proposal_prompt(topic, audience, company_name, consultant_name, json_format, document_text, ref_context, cv_context)
            elif gen_type == "formation":
                system_prompt = _get_formation_system_prompt(company_name)
                prompt = _get_formation_prompt(topic, audience, json_format, document_text)
            elif gen_type == "rex":
                system_prompt = _get_rex_system_prompt(company_name)
                prompt = _get_rex_prompt(topic, audience, json_format, document_text)
            else:
                system_prompt = _get_presentation_system_prompt(company_name)
                prompt = _get_presentation_prompt(topic, audience, slide_count, json_format, document_text)

            # Append feedback context if present
            if feedback and previous_slides:
                prompt += f"""

SLIDES ACTUELLES (a modifier selon le feedback) :
{previous_slides[:6000]}

FEEDBACK UTILISATEUR :
{feedback}

Modifie les slides en tenant compte du feedback. Conserve le format JSON et la structure globale.
Retourne TOUTES les slides (modifiees et non modifiees)."""

            job["steps"].append({"message": "Generation par l'IA en cours...", "step": 2})

            # Stream response and parse slides progressively
            buffer = ""
            try:
                for chunk in llm.generate_stream(prompt=prompt, system_prompt=system_prompt, temperature=0.7):
                    buffer += chunk
                    # Try to extract complete slide objects from the buffer
                    _extract_slides_from_buffer(buffer, job)
            except Exception as stream_err:
                print(f"  Streaming error, falling back to non-streaming: {stream_err}")
                buffer = llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

            response = buffer

            job["steps"].append({"message": "Finalisation...", "step": 3})

            # Final parse to ensure all slides are captured
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()

            try:
                result = json.loads(json_str)
                all_slides = result.get("slides", result if isinstance(result, list) else [])
                # Only replace if final parse found more slides
                if len(all_slides) > len(job["slides"]):
                    job["slides"] = all_slides
            except json.JSONDecodeError:
                pass  # Keep whatever slides were parsed during streaming

            if not job["slides"]:
                raise ValueError("Aucune slide generee - reponse LLM invalide")

            # Add image prompts for relevant slides (no actual generation)
            job["steps"].append({"message": "Ajout des prompts d images...", "step": 4})
            _generate_slide_illustrations(job["slides"], job, topic, gen_type)

            job["result"] = {"slides": job["slides"], "total": len(job["slides"])}
            job["status"] = "done"

        except Exception as e:
            print(f"Erreur slide-editor generate: {e}")
            import traceback
            traceback.print_exc()
            job["error"] = str(e)
            job["status"] = "error"

    import threading
    threading.Thread(target=run_generation, daemon=True).start()

    return {"job_id": job_id}


@app.get("/api/slide-editor/stream/{job_id}")
async def api_slide_editor_stream(job_id: str):
    """SSE stream pour la progression de generation de slides"""
    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouve"})
            return

        last_step_idx = 0
        last_slide_idx = 0

        while True:
            # Send new steps
            while last_step_idx < len(job["steps"]):
                step = job["steps"][last_step_idx]
                yield send_sse("status", step)
                last_step_idx += 1

            # Send slides progressively as they appear (during or after generation)
            while last_slide_idx < len(job["slides"]):
                slide = job["slides"][last_slide_idx]
                yield send_sse("slide", {"index": last_slide_idx, "total": len(job["slides"]), "slide": slide})
                last_slide_idx += 1
                await asyncio.sleep(0.1)

            if job["status"] == "done":
                # Send any remaining slides
                while last_slide_idx < len(job["slides"]):
                    slide = job["slides"][last_slide_idx]
                    yield send_sse("slide", {"index": last_slide_idx, "total": len(job["slides"]), "slide": slide})
                    last_slide_idx += 1
                yield send_sse("done", {"total": len(job["slides"])})
                return

            if job["status"] == "error":
                yield send_sse("error_msg", {"message": job["error"]})
                return

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _get_slide_json_format():
    return """
IMPORTANT : Tu dois retourner UNIQUEMENT un JSON valide avec cette structure :
{{"slides": [...]}}

Types de slides disponibles et leur format JSON :
- "cover" : {{"type":"cover", "title":"...", "subtitle":"...", "meta":"..."}}
- "section" : {{"type":"section", "title":"...", "number":"01"}}
- "content" : {{"type":"content", "title":"...", "bullets":["...","..."]}}
- "stat" : {{"type":"stat", "stat_value":"73%", "stat_label":"...", "context":"...", "subtitle":"..."}}
- "quote" : {{"type":"quote", "quote_text":"...", "author":"...", "title":"..."}}
- "highlight" : {{"type":"highlight", "title":"...", "key_points":["...","...","..."]}}
- "diagram" : {{"type":"diagram", "title":"...", "diagram_type":"flow|pyramid|timeline|cycle|matrix", "elements":["...","..."]}}
- "two_column" : {{"type":"two_column", "title":"...", "left_title":"...", "left_points":["..."], "right_title":"...", "right_points":["..."]}}
- "table" : {{"type":"table", "title":"...", "headers":["...","..."], "rows":[["...","..."]]}}
- "closing" : {{"type":"closing", "title":"Merci", "subtitle":"..."}}

Optionnel : chaque slide peut avoir un champ "tags": ["TAG1", "TAG2"] pour la categoriser.
"""


def _get_proposal_system_prompt(company_name):
    return f"""Tu agis en tant que Consultant Senior chez {company_name}. Ta mission est de rediger le contenu et la structure d'une proposition commerciale au format "Slides".

### IDENTITE VISUELLE (DA)
- Polices : Titres en "Chakra Petch" (Tech/Impact), Textes courants en "Inter" (Lisibilite).
- Palette Couleurs (Regle 60-30-10) :
  - 60% Dominante : Fond Blanc (#FFFFFF) ou Rose Poudre (#FBF0F4) pour les encadres.
  - 30% Secondaire : Textes en Noir Profond (#1F1F1F) ou Gris Moyen (#474747).
  - 10% Accent : Terracotta (#c0504d) ou Corail (#FF6B58). Maximum 5 elements par slide.
- Style : Tags en en-tete (#TECH #DATA), marqueur vertical "WENVISION | 2025-2026", mise en page aeree.

### REGLES DE GENERATION JSON
- Tu dois retourner UNIQUEMENT du JSON valide, pas de texte explicatif
- Chaque slide a un "type" parmi les types disponibles
- Utilise des types varies : stat pour les chiffres, diagram pour les processus, highlight pour les points cles, two_column pour les comparaisons
- Le contenu doit etre redige sur un ton expert, convaincant et direct
- Maximum 4 bullet points par slide, phrases courtes et percutantes
- Tu determines toi-meme le nombre de slides adapte au contenu et a la complexite du besoin client
- Ajoute des slides CV equipe et references missions si ces informations sont fournies"""


def _get_proposal_prompt(topic, audience, company_name, consultant_name, json_format, document_text="", references="", cvs=""):
    doc_section = ""
    if document_text:
        doc_section = f"""

DOCUMENT FOURNI (utilise ce contenu comme base) :
{document_text[:6000]}
"""

    ref_section = ""
    if references:
        ref_section = f"""

REFERENCES DE MISSIONS SIMILAIRES (integre-les dans la proposition) :
{references}
"""

    cv_section = ""
    if cvs:
        cv_section = f"""

EQUIPE DISPONIBLE (integre les profils pertinents dans la proposition) :
{cvs}
"""

    return f"""Genere une proposition commerciale pour le sujet suivant : {topic}

PUBLIC CIBLE : {audience or 'Direction et decideurs'}
CONSULTANT : {consultant_name} - {company_name}
{doc_section}{ref_section}{cv_section}
Determine toi-meme le nombre de slides et la structure les plus adaptes au besoin client.
Adapte la profondeur et le nombre de slides a la complexite du sujet.

### ELEMENTS A COUVRIR (ordre et decoupage libres) :
- Couverture (cover) : titre impactant, meta "{company_name} | 2025-2026"
- Comprehension du besoin : montrer que tu as compris la realite du client
- Approche et methodologie : comment tu vas repondre au besoin
- Demarche / Phases : diagram flow ou timeline
- Planning / Feuille de route
- Dispositif et gouvernance : equipe, roles, rituels
- Facteurs cles de succes
- Pourquoi {company_name} : valeur ajoutee, differenciants
- Presentation {company_name} : Cabinet de conseil en transformation digitale (Strategy & Vision, Data & Insights, Product Management, Scalability Platform)
- Si des CVs sont fournis : slides CV equipe (type "cv") avec experiences REFORMULEES pour le besoin client
- Si des references sont fournies : slides references (type "highlight") avec resultats concrets et paralleles avec la mission
- Cloture (closing) : contact {consultant_name}

{json_format}

Genere maintenant la proposition pour : {topic}"""


def _get_presentation_system_prompt(company_name):
    return f"""Tu es un expert en creation de presentations professionnelles pour {company_name}.
Tu crees des presentations visuelles, impactantes et variees.

REGLES STRICTES :
- VARIETE : Alterne les types de slides. Ne jamais avoir 2 slides "content" consecutives.
- VISUELS : Au moins 40% des slides doivent etre visuelles (stat, diagram, highlight, quote)
- CONCIS : Maximum 3-4 bullet points par slide, phrases courtes
- IMPACT : Chiffres-cles en "stat", principes en "quote", comparaisons en "two_column"

Tu retournes UNIQUEMENT un JSON valide."""


def _get_presentation_prompt(topic, audience, slide_count, json_format, document_text=""):
    doc_section = ""
    if document_text:
        doc_section = f"""

DOCUMENT SOURCE (utilise ce contenu comme base) :
{document_text[:6000]}
"""

    return f"""Genere une presentation de {slide_count} slides sur le sujet suivant :

SUJET : {topic}
PUBLIC CIBLE : {audience or 'Managers et decideurs'}
NOMBRE DE SLIDES : {slide_count}
{doc_section}
Structure attendue : commence par cover, puis alterne sections et contenu, termine par closing.

{json_format}

Reponds UNIQUEMENT avec le JSON."""


def _get_formation_system_prompt(company_name):
    return f"""Tu es un formateur expert chez {company_name}, specialise en data, IA et transformation digitale.
Tu crees des supports de formation pedagogiques, progressifs et engageants.

### IDENTITE VISUELLE (DA)
- Polices : Titres en "Chakra Petch" (Tech/Impact), Textes courants en "Inter" (Lisibilite).
- Palette Couleurs (Regle 60-30-10) :
  - 60% Dominante : Fond Blanc (#FFFFFF) ou Rose Poudre (#FBF0F4) pour les encadres.
  - 30% Secondaire : Textes en Noir Profond (#1F1F1F) ou Gris Moyen (#474747).
  - 10% Accent : Terracotta (#c0504d) ou Corail (#FF6B58). Maximum 5 elements par slide.

### REGLES PEDAGOGIQUES
- Progression : du concept a la pratique (theorie > exemples > exercices)
- 1 idee par slide maximum
- Alterner theorie (content), visualisation (diagram, stat), et recapitulatif (highlight)
- Inclure des slides quiz/exercice avec le type "highlight" (key_points comme options)
- Ajouter un champ "tags" (tableau de strings) pour categoriser chaque slide : ex ["THEORIE"], ["PRATIQUE"], ["QUIZ"], ["DEMO"]
- Maximum 3 bullet points par slide, phrases courtes et pedagogiques

### NOMBRE DE SLIDES
- Tu determines toi-meme le nombre de slides adapte au sujet, a la duree et au contenu du brief
- Chaque module doit avoir : intro, theorie, exercice/quiz, recap

### REGLES DE GENERATION JSON
- Tu dois retourner UNIQUEMENT du JSON valide, pas de texte explicatif
- Chaque slide a un "type" parmi les types disponibles
- Au moins 40% de slides visuelles (stat, diagram, highlight, quote)
- Ne jamais avoir 2 slides "content" consecutives"""


def _get_formation_prompt(topic, audience, json_format, document_text=""):
    doc_section = ""
    if document_text:
        doc_section = f"""

DOCUMENT SOURCE (utilise ce contenu comme matiere pedagogique) :
{document_text[:6000]}
"""

    return f"""Genere un support de formation complet sur le sujet suivant :

SUJET : {topic or 'Formation basee sur le document fourni'}
PUBLIC CIBLE : {audience or 'Equipes techniques et managers'}
{doc_section}
Determine le nombre de slides adapte au contenu et a la duree mentionnee dans le brief.
Si aucune duree n est precisee, genere 15-20 slides (1 journee).

### STRUCTURE ATTENDUE :
1. Cover : titre de la formation + sous-titre
2. Section "Objectifs" : ce que les apprenants sauront faire
3. Sections thematiques : alterner content, diagram, stat, highlight
4. Pour chaque section : concept > illustration > exercice/quiz
5. Recapitulatif final (highlight avec les points cles)
6. Closing : prochaines etapes + contact

IMPORTANT : Ajoute un champ "tags" (tableau) a chaque slide pour la categoriser.
Exemples de tags : "THEORIE", "PRATIQUE", "QUIZ", "DEMO", "RECAP", "OBJECTIFS"

{json_format}

Reponds UNIQUEMENT avec le JSON."""


def _get_rex_system_prompt(company_name):
    return f"""Tu es un consultant senior chez {company_name} qui redige un Retour d Experience (REX) de mission.

### IDENTITE VISUELLE (DA)
- Polices : Titres en "Chakra Petch" (Tech/Impact), Textes courants en "Inter" (Lisibilite).
- Palette Couleurs (Regle 60-30-10) :
  - 60% Dominante : Fond Blanc (#FFFFFF) ou Rose Poudre (#FBF0F4) pour les encadres.
  - 30% Secondaire : Textes en Noir Profond (#1F1F1F) ou Gris Moyen (#474747).
  - 10% Accent : Terracotta (#c0504d) ou Corail (#FF6B58). Maximum 5 elements par slide.

### REGLES DU REX
- Ton factuel et professionnel, oriente resultats
- Chiffres concrets (KPIs, delais, gains, ROI)
- Structure : Contexte > Enjeux > Demarche > Realisations > Resultats > Apprentissages > Recommandations
- Utilise des types visuels varies : stat pour les resultats, diagram pour la demarche, timeline pour le planning
- Maximum 3-4 bullet points par slide
- Ajoute un champ "tags" a chaque slide : "CONTEXTE", "ENJEUX", "DEMARCHE", "RESULTATS", "APPRENTISSAGES"

### REGLES DE GENERATION JSON
- Tu dois retourner UNIQUEMENT du JSON valide, pas de texte explicatif
- Chaque slide a un "type" parmi les types disponibles
- Au moins 40% de slides visuelles (stat, diagram, highlight, timeline)"""


def _get_rex_prompt(topic, client, json_format, document_text=""):
    doc_section = ""
    if document_text:
        doc_section = f"""

DOCUMENT SOURCE (utilise ce contenu comme base pour le REX) :
{document_text[:6000]}
"""

    return f"""Genere un Retour d Experience (REX) de mission pour :

MISSION : {topic or 'Mission basee sur le document fourni'}
CLIENT / CONTEXTE : {client or 'Client entreprise'}
{doc_section}
### STRUCTURE OBLIGATOIRE (10 slides) :

**Slide 1 : Couverture (cover)**
- Titre : "REX Mission - [Nom de la mission]"
- Sous-titre avec le client et la periode

**Slide 2 : Contexte Client (content)**
- Qui est le client, son secteur, sa taille
- Contexte de la mission (appel d offre, besoin identifie)
- Tags: ["CONTEXTE"]

**Slide 3 : Enjeux & Objectifs (highlight)**
- 3-4 enjeux business et objectifs mesurables
- Tags: ["ENJEUX"]

**Slide 4 : Notre Demarche (diagram)**
- Type "flow" : phases de la mission (Cadrage > Audit > Design > Build > Run)
- Tags: ["DEMARCHE"]

**Slide 5 : Planning & Jalons (diagram)**
- Type "timeline" : jalons cles de la mission
- Tags: ["DEMARCHE"]

**Slide 6 : Realisations Cles (highlight)**
- 3-4 livrables ou realisations majeures
- Tags: ["RESULTATS"]

**Slide 7 : Resultats Chiffres (stat)**
- KPI principal avec valeur impactante (ex: +35 pourcent, ROI x3, etc.)
- Tags: ["RESULTATS"]

**Slide 8 : Apprentissages (two_column)**
- Colonne gauche : "Ce qui a bien marche" (facteurs de succes)
- Colonne droite : "Points d'amelioration" (lessons learned)
- Tags: ["APPRENTISSAGES"]

**Slide 9 : Recommandations (content)**
- 3-4 recommandations pour la suite ou pour de futures missions similaires
- Tags: ["APPRENTISSAGES"]

**Slide 10 : Cloture (closing)**
- "Merci" + contact

{json_format}

Reponds UNIQUEMENT avec le JSON."""


@app.post("/api/slide-editor/generate")
async def api_slide_editor_generate(request: Request):
    """Genere des slides JSON via LLM pour le slide editor (non-streaming fallback)"""
    try:
        data = await request.json()
        topic = data.get("topic", "")
        audience = data.get("audience", "")
        slide_count = data.get("slide_count", 10)
        gen_type = data.get("type", "presentation")
        model = data.get("model", "")
        document_text = data.get("document_text", "")

        from utils.llm_client import LLMClient
        llm_kwargs = {"max_tokens": 8192}
        if model:
            llm_kwargs["model"] = model
            llm_kwargs["provider"] = "gemini"
        llm = LLMClient(**llm_kwargs)

        consultant_name = os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha')
        company_name = os.getenv('COMPANY_NAME', 'Wenvision')
        json_format = _get_slide_json_format()

        if gen_type == "proposal":
            system_prompt = _get_proposal_system_prompt(company_name)
            prompt = _get_proposal_prompt(topic, audience, company_name, consultant_name, json_format, document_text)
        elif gen_type == "formation":
            system_prompt = _get_formation_system_prompt(company_name)
            prompt = _get_formation_prompt(topic, audience, json_format, document_text)
        elif gen_type == "rex":
            system_prompt = _get_rex_system_prompt(company_name)
            prompt = _get_rex_prompt(topic, audience, json_format, document_text)
        else:
            system_prompt = _get_presentation_system_prompt(company_name)
            prompt = _get_presentation_prompt(topic, audience, slide_count, json_format, document_text)

        response = llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0].strip()
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0].strip()
        else:
            json_str = response.strip()

        result = json.loads(json_str)
        return JSONResponse(result)

    except json.JSONDecodeError as e:
        print(f"Erreur JSON slide-editor: {e}")
        return JSONResponse({"error": "Erreur de parsing JSON", "slides": []}, status_code=422)
    except Exception as e:
        print(f"Erreur slide-editor generate: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === DOCUMENT EDITOR ===

@app.get("/document-editor", response_class=HTMLResponse)
async def document_editor_page(request: Request):
    return templates.TemplateResponse("document-editor.html", {
        "request": request,
        "active": "document-editor",
        "consultant_name": CONSULTANT_NAME,
    })


@app.get("/veille", response_class=HTMLResponse)
async def veille_page(request: Request):
    return templates.TemplateResponse("veille.html", {
        "request": request,
        "active": "veille",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/document-editor/start-generate")
async def api_document_editor_start_generate(request: Request):
    """Demarre la generation de document en arriere-plan"""
    data = await request.json()
    doc_type = data.get("type", "formation")
    topic = data.get("topic", "")
    document_text = data.get("document_text", "")
    audience = data.get("audience", "")
    length = data.get("length", "medium")
    model = data.get("model", "")
    feedback = data.get("feedback", "")
    previous_content = data.get("previous_content", "")
    use_context = data.get("use_context", False)

    job_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(data) % 10000}"

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
                    system_prompt = "Tu es un expert en redaction chez Wenvision. Tu dois modifier un document existant en tenant compte du feedback utilisateur. Conserve la structure markdown et ameliore le contenu."
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
                        for chunk in llm.generate_stream(prompt=prompt, system_prompt=system_prompt, temperature=0.7):
                            buffer += chunk
                            job["chunks"].append(chunk)
                    except Exception:
                        buffer = llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
                        job["chunks"].append(buffer)

                    response = buffer.strip()
                    if response.startswith('```markdown'):
                        response = response[len('```markdown'):]
                    if response.startswith('```'):
                        response = response[3:]
                    if response.endswith('```'):
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

                system_prompt = f"""Tu es un consultant senior chez {os.getenv('COMPANY_NAME', 'Wenvision')} qui redige un Retour d Experience (REX) de mission.

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
                    for chunk in llm.generate_stream(prompt=prompt, system_prompt=system_prompt, temperature=0.7):
                        buffer += chunk
                        job["chunks"].append(chunk)
                except Exception:
                    buffer = llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
                    job["chunks"].append(buffer)

                response = buffer.strip()
                if response.startswith('```markdown'):
                    response = response[len('```markdown'):]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                result["markdown"] = response.strip()

            elif doc_type == "linkedin":
                job["steps"].append({"message": "Generation du post LinkedIn..."})
                llm = LLMClient(**llm_kwargs)
                consultant_name = os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha')
                company_name = os.getenv('COMPANY_NAME', 'Wenvision')

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
                    for chunk in llm.generate_stream(prompt=prompt, system_prompt=system_prompt, temperature=0.7):
                        buffer += chunk
                        job["chunks"].append(chunk)
                except Exception:
                    buffer = llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
                    job["chunks"].append(buffer)

                response = buffer.strip()
                if response.startswith('```'):
                    response = response.split('```', 1)[1]
                    if response.startswith('\n'):
                        response = response[1:]
                    if '```' in response:
                        response = response.rsplit('```', 1)[0]
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
                is_cv = any(kw in document_text.lower() for kw in [
                    'experience', 'competences', 'formation', 'cv', 'consultant',
                    'diplome', 'certification', 'parcours professionnel'
                ])
                type_label = "CV" if is_cv else "Reference"

                job["steps"].append({"message": f"Generation des slides {type_label}..."})

                gen_result = agent.run(
                    document_text=document_text,
                    mission_brief=topic,  # Le "topic" = l appel d offre
                    doc_type=type_label
                )

                # Retourner slides au lieu de markdown
                job["slides"] = gen_result.get("slides", [])
                result["slides"] = gen_result.get("slides", [])
                result["doc_type"] = type_label

            elif doc_type == "presentation_script":
                job["steps"].append({"message": "Extraction du contenu PPTX..."})

                # document_text contient le chemin vers le fichier PPTX temporaire
                if not document_text or not document_text.endswith('.pptx'):
                    raise ValueError("Fichier PPTX obligatoire pour generer un script de presentation")

                from agents.presentation_script_generator import PresentationScriptGenerator
                agent = PresentationScriptGenerator()
                if model:
                    agent.llm = LLMClient(**llm_kwargs)

                job["steps"].append({"message": "Analyse des slides..."})

                # Stream chunks si possible
                gen_result = agent.run(
                    pptx_path=document_text,
                    presentation_context=topic or ""
                )

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
            job["error"] = str(e)
            job["status"] = "error"

    import threading
    threading.Thread(target=run_doc_generation, daemon=True).start()

    return {"job_id": job_id}


@app.get("/api/document-editor/stream/{job_id}")
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


@app.post("/api/document-editor/export-gdocs")
async def api_document_editor_export_gdocs(request: Request):
    """Exporte le markdown vers Google Docs"""
    try:
        data = await request.json()
        markdown = data.get("markdown", "")
        title = data.get("title", "Document WEnvision")

        if not markdown:
            return JSONResponse({"error": "Pas de contenu a exporter"}, status_code=400)

        from utils.google_api import GoogleAPIClient
        client = GoogleAPIClient()
        url = client.export_markdown_to_docs(markdown, title)

        return {"url": url}
    except Exception as e:
        print(f"Erreur export Google Docs: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== VEILLE TECHNOLOGIQUE =====

@app.get("/api/veille/articles")
async def api_veille_get_articles(
    limit: int = 50,
    offset: int = 0,
    source: str = None,
    keyword: str = None,
    days: int = None
):
    """Liste les articles de veille avec filtres"""
    try:
        from utils.article_db import ArticleDatabase
        db = ArticleDatabase()

        articles = db.get_articles(
            limit=limit,
            offset=offset,
            source=source,
            keyword=keyword,
            days=days
        )

        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        print(f"Erreur lecture articles: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/veille/stats")
async def api_veille_stats():
    """Statistiques sur les articles stockes"""
    try:
        from utils.article_db import ArticleDatabase
        db = ArticleDatabase()
        stats = db.get_article_stats()
        return stats
    except Exception as e:
        print(f"Erreur stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/veille/generate-digest")
async def api_veille_generate_digest(request: Request):
    """Genere un nouveau digest de veille"""
    try:
        data = await request.json()
        period = data.get("period", "daily")
        days = data.get("days", 1 if period == "daily" else 7)
        keywords = data.get("keywords", [])

        from agents.tech_monitor import TechMonitorAgent
        agent = TechMonitorAgent()

        result = agent.run(
            keywords=keywords if keywords else None,
            days=days,
            period=period
        )

        return {
            "success": True,
            "digest": result["content"],
            "num_articles": result["num_articles"],
            "digest_id": result.get("digest_id"),
            "md_path": result.get("md_path")
        }
    except Exception as e:
        print(f"Erreur generation digest: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/veille/digests")
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
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/veille/articles/{article_id}/mark-read")
async def api_veille_mark_read(article_id: int):
    """Marque un article comme lu"""
    try:
        from utils.article_db import ArticleDatabase
        db = ArticleDatabase()
        db.mark_as_read(article_id)
        return {"success": True}
    except Exception as e:
        print(f"Erreur mark read: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/veille/articles/{article_id}/toggle-favorite")
async def api_veille_toggle_favorite(article_id: int):
    """Toggle favori sur un article"""
    try:
        from utils.article_db import ArticleDatabase
        db = ArticleDatabase()
        db.toggle_favorite(article_id)
        return {"success": True}
    except Exception as e:
        print(f"Erreur toggle favorite: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === MAIN ===

if __name__ == "__main__":
    import uvicorn

    # Check if SSL certificates exist
    ssl_cert = BASE_DIR / "ssl" / "cert.pem"
    ssl_key = BASE_DIR / "ssl" / "key.pem"
    use_ssl = ssl_cert.exists() and ssl_key.exists()

    protocol = "https" if use_ssl else "http"
    port = 8443 if use_ssl else 8000

    print(f"\n{'='*50}")
    print("  WEnvision Agents - Interface Web")
    print(f"  {protocol}://localhost:{port}")
    if use_ssl:
        print("  🔒 HTTPS activé (certificat auto-signé)")
    else:
        print("  ⚠️  HTTP uniquement (pas de SSL)")
    print(f"{'='*50}\n")

    if use_ssl:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile=str(ssl_key),
            ssl_certfile=str(ssl_cert)
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
