"""
Consulting Tools Agents - Application Web
FastAPI server exposant les agents de propositions commerciales et veille LinkedIn
"""

import asyncio
import io
import json
import os
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PyPDF2 import PdfReader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from agents.article_to_post import ArticleToPostAgent
from agents.dataset_analyzer import DatasetAnalyzerAgent
from agents.elearning_agent import ElearningAgent
from agents.linkedin_commenter import LinkedInCommenterAgent
from agents.linkedin_monitor import LinkedInMonitorAgent
from agents.meeting_capture_agent import GEMINI_MODELS as MC_GEMINI_MODELS
from agents.meeting_capture_agent import APIKeyError as MCAPIKeyError
from agents.meeting_capture_agent import (
    DraftCreationError,
    MeetingCaptureAgent,
    MeetingGmailClient,
    VideoProcessingError,
)
from agents.meeting_summarizer import MeetingSummarizerAgent
from agents.proposal_generator import ProposalGeneratorAgent
from agents.rfp_responder import RFPResponderAgent
from agents.skills_market import SkillsMarketAgent
from agents.tech_monitor import TechMonitorAgent
from agents.tender_scout_agent import AnalysisError, ScrapingError, TenderScoutAgent
from agents.workshop_planner import WorkshopPlannerAgent
from config import get_consultant_info
from utils.auth import authenticate_user, get_current_user, get_session_secret
from utils.consultant_db import ConsultantDatabase
from utils.elearning_db import ElearningDatabase
from utils.tender_db import TenderDatabase
from utils.validation import (
    sanitize_error_message,
    sanitize_filename,
    sanitize_text_input,
    validate_file_upload,
)

from routers.shared import (
    BASE_DIR,
    jobs,
    skills_market_db,
    elearning_db,
    tender_db,
    limiter,
    templates,
    CONSULTANT_NAME,
    COMPANY_NAME,
    safe_error_message,
    safe_traceback,
    send_sse,
)
from routers.skills_market import router as skills_market_router
from routers.comment import router as comment_router
from routers.techwatch import router as techwatch_router
from routers.dataset import router as dataset_router
from routers.workshop import router as workshop_router
from routers.rfp import router as rfp_router
from routers.linkedin import router as linkedin_router
from routers.article import router as article_router
from routers.meeting import router as meeting_router
from routers.article_generator import router as article_generator_router
from routers.formation import router as formation_router
from routers.training_slides import router as training_slides_router
from routers.meeting_capture import router as meeting_capture_router
from routers.dashboard import router as dashboard_router
from routers.proposal import router as proposal_router
from routers.slide_editor import router as slide_editor_router
from routers.document_editor import router as document_editor_router
from routers.elearning import router as elearning_router
from routers.tenderscout import router as tenderscout_router

# Charger l'environnement
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


# Ajouter le repertoire au path pour les imports
sys.path.insert(0, str(BASE_DIR))


# Rate limiting

# === APP SETUP ===

app = FastAPI(title="Consulting Tools Agents", version="1.0.0")

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Templates and static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include Routers
app.include_router(skills_market_router)
app.include_router(comment_router)
app.include_router(techwatch_router)
app.include_router(dataset_router)
app.include_router(workshop_router)
app.include_router(rfp_router)
app.include_router(linkedin_router)
app.include_router(article_router)
app.include_router(meeting_router)
app.include_router(article_generator_router)
app.include_router(formation_router)
app.include_router(training_slides_router)
app.include_router(meeting_capture_router)
app.include_router(dashboard_router)
app.include_router(proposal_router)
app.include_router(slide_editor_router)
app.include_router(document_editor_router)
app.include_router(elearning_router)
app.include_router(tenderscout_router)


# === CSRF PROTECTION MIDDLEWARE ===


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware CSRF basé sur Origin/Referer checking
    Plus simple que token-based CSRF, adapté pour une app locale
    """

    async def dispatch(self, request: Request, call_next):
        # Méthodes qui nécessitent protection CSRF
        unsafe_methods = {"POST", "PUT", "DELETE", "PATCH"}

        # Routes exemptées (par exemple les webhooks externes)
        exempt_paths = []

        # Si méthode safe ou route exemptée, passer
        if request.method not in unsafe_methods:
            return await call_next(request)

        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)

        # Vérifier Origin ou Referer
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        # Obtenir l'hôte autorisé
        host = request.headers.get("host", "localhost:8000")
        allowed_origins = [
            f"http://{host}",
            f"https://{host}",
            "http://localhost:8000",
            "https://localhost:8000",
            "http://127.0.0.1:8000",
            "https://127.0.0.1:8000",
        ]

        # Vérifier l'origine
        origin_valid = False

        if origin:
            origin_valid = origin in allowed_origins
        elif referer:
            # Si pas d'Origin, vérifier Referer
            try:
                parsed = urlparse(referer)
                referer_origin = f"{parsed.scheme}://{parsed.netloc}"
                origin_valid = referer_origin in allowed_origins
            except BaseException:
                origin_valid = False

        if not origin_valid:
            print(f"⚠️  CSRF blocked: {request.method} {request.url.path} from {origin or referer}")
            return JSONResponse(
                {"detail": "CSRF validation failed. Request origin not allowed."}, status_code=403
            )

        return await call_next(request)


# === AUTHENTICATION MIDDLEWARE ===


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware pour vérifier l'authentification"""

    async def dispatch(self, request: Request, call_next):
        # Routes publiques (pas besoin d'auth)
        public_paths = ["/login", "/static", "/auth/", "/favicon.ico"]

        # Si la route est publique, passer
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Vérifier l'authentification
        user = get_current_user(request)
        if not user:
            # Si c'est une requête API, renvoyer 401
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Non authentifié"}, status_code=401)
            # Sinon, rediriger vers /login
            return RedirectResponse(url="/login", status_code=302)

        # Stocker l'utilisateur dans request.state pour les templates
        request.state.user = user
        return await call_next(request)


# Ajouter les middlewares dans l'ordre correct
# L'ordre d'ajout est inversé : le dernier ajouté s'exécute en premier
# Protection CSRF (origin checking)
app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=get_session_secret())  # S'exécute en premier

# Security utilities moved to routers/shared.py


# Global model settings (in-memory, persists per session)
AVAILABLE_GEMINI_MODELS = {
    # Gemini 3.x (Preview)
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview 🔥",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview ⚡",
    "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite",
    "deep-research-pro-preview-12-2025": "Deep Research Pro 🔬",
    # Gemini 2.5
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    # Gemini 2.0
    "gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini-2.0-flash-001": "Gemini 2.0 Flash 001",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
    "gemini-2.0-flash-lite-001": "Gemini 2.0 Flash Lite 001",
    # Latest aliases
    "gemini-flash-latest": "Gemini Flash (Latest)",
    "gemini-pro-latest": "Gemini Pro (Latest)",
    # Gemini 1.5
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
}
SELECTED_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
IMAGE_MODEL = "gemini-3-pro-image-preview"  # Nano Banana Pro for images

# Settings persistence
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"


def load_settings():
    """Charge les settings depuis le fichier JSON"""
    global SELECTED_GEMINI_MODEL
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            SELECTED_GEMINI_MODEL = settings.get("gemini_model", SELECTED_GEMINI_MODEL)
        except Exception:
            pass


def save_settings():
    """Sauvegarde les settings dans le fichier JSON"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = {"gemini_model": SELECTED_GEMINI_MODEL}
    with open(SETTINGS_FILE, "w") as f:
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
        files.append(
            {
                "name": f.name,
                "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "path": str(f),
            }
        )
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
            {"detail": "Nom d'utilisateur ou mot de passe incorrect"}, status_code=401
        )


@app.get("/logout")
async def logout(request: Request):
    """Déconnexion"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# === LINKEDIN OAUTH ===


@app.get("/auth/linkedin")
async def linkedin_auth_start():
    """Demarre le flux OAuth LinkedIn"""
    from utils.linkedin_client import LinkedInClient, is_linkedin_configured

    if not is_linkedin_configured():
        return HTMLResponse(
            """
            <h1>LinkedIn OAuth non configure</h1>
            <p>Veuillez configurer les variables suivantes dans votre .env :</p>
            <ul>
                <li>LINKEDIN_CLIENT_ID</li>
                <li>LINKEDIN_CLIENT_SECRET</li>
                <li>LINKEDIN_REDIRECT_URI</li>
            </ul>
            <p>Consultez <a href="https://www.linkedin.com/developers/apps">LinkedIn Developers</a> pour créer une app.</p>
        """,
            status_code=400,
        )

    try:
        client = LinkedInClient()
        auth_url = client.get_auth_url()
        return RedirectResponse(auth_url)
    except Exception as e:
        return HTMLResponse(f"<h1>Erreur</h1><p>{safe_error_message(e)}</p>", status_code=500)


@app.get("/auth/linkedin/callback")
async def linkedin_auth_callback(
    code: str = None, error: str = None, error_description: str = None
):
    """Gere le callback OAuth LinkedIn"""
    from utils.linkedin_client import LinkedInClient

    # Check for errors
    if error:
        return HTMLResponse(
            """
            <h1>Erreur OAuth LinkedIn</h1>
            <p><strong>Erreur :</strong> {error}</p>
            <p><strong>Description :</strong> {error_description or 'N/A'}</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            """
            <h1>Erreur OAuth LinkedIn</h1>
            <p>Code d autorisation manquant</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=400,
        )

    try:
        client = LinkedInClient()
        token_data = client.exchange_code_for_token(code)
        token_data.get("access_token")
        token_data.get("expires_in", "N/A")

        return HTMLResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <title>LinkedIn Connected!</title>
                <style>
                    body {{
                        font-family: 'Inter', sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background: #f8f9fa;
                    }}
                    .success {{
                        background: white;
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    h1 {{ color: #0a66c2; }}
                    code {{
                        background: #f0f0f0;
                        padding: 15px;
                        display: block;
                        border-radius: 8px;
                        margin: 15px 0;
                        font-family: monospace;
                        word-break: break-all;
                    }}
                    .btn {{
                        background: #0a66c2;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 8px;
                        display: inline-block;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="success">
                    <h1>✅ LinkedIn connecté avec succès !</h1>
                    <p>Votre application est maintenant autorisée à publier sur LinkedIn.</p>
                    <p><strong>Expire dans :</strong> {expires_in} secondes</p>

                    <h2>Configuration</h2>
                    <p>Ajoutez cette ligne à votre fichier <code>.env</code> :</p>
                    <code>LINKEDIN_ACCESS_TOKEN={access_token}</code>

                    <p><strong>Important :</strong> Ce token expire. Vous devrez répéter le processus OAuth lorsqu il expirera.</p>

                    <a href="/" class="btn">Retour au dashboard</a>
                </div>
            </body>
            </html>
        """
        )

    except Exception:
        return HTMLResponse(
            """
            <h1>Erreur lors de l echange du code</h1>
            <p>{safe_error_message(e)}</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=500,
        )


# === MAIN ===

if __name__ == "__main__":
    import uvicorn

    # Check if SSL certificates exist
    ssl_cert = BASE_DIR / "ssl" / "cert.pem"
    ssl_key = BASE_DIR / "ssl" / "key.pem"
    use_ssl = ssl_cert.exists() and ssl_key.exists()

    protocol = "https" if use_ssl else "http"
    port = 8443 if use_ssl else 8000

    print(f"\n{'=' * 50}")
    print("  Consulting Tools Agents - Interface Web")
    print(f"  {protocol}://localhost:{port}")
    if use_ssl:
        print("  🔒 HTTPS activé (certificat auto-signé)")
    else:
        print("  ⚠️  HTTP uniquement (pas de SSL)")

    # Security warning for default password
    auth_password = os.getenv("AUTH_PASSWORD", "")
    if (
        not auth_password or auth_password == "CHANGE_ME_ON_FIRST_INSTALL"  # pragma: allowlist secret
    ):
        print("\n  🚨 SECURITE : Mot de passe par defaut detecte !")
        print("  → Veuillez configurer AUTH_PASSWORD dans votre fichier .env")
        print("  → Utilisez un mot de passe fort et unique")

    print(f"{'=' * 50}\n")

    if use_ssl:
        uvicorn.run(
            app, host="0.0.0.0", port=port, ssl_keyfile=str(ssl_key), ssl_certfile=str(ssl_cert)
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
