"""
Consulting Tools Agents - Application Web
FastAPI server exposant les agents de propositions commerciales et veille LinkedIn
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from utils.auth import get_current_user, get_session_secret

from routers.shared import limiter, load_settings, templates
from routers.auth import router as auth_router
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
from routers.settings import router as settings_router
from routers.microsoft import router as microsoft_router

# Charger l'environnement
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# Ajouter le repertoire au path pour les imports
sys.path.insert(0, str(BASE_DIR))


# === APP SETUP ===

app = FastAPI(title="Consulting Tools Agents", version="1.0.0")

# Rate limiter — use the single instance from routers/shared.py
app.state.limiter = limiter
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include Routers
app.include_router(auth_router)
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
app.include_router(settings_router)
app.include_router(microsoft_router)


# === CSRF PROTECTION MIDDLEWARE ===


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware CSRF basé sur Origin/Referer checking
    Plus simple que token-based CSRF, adapté pour une app locale
    """

    async def dispatch(self, request: Request, call_next):
        unsafe_methods = {"POST", "PUT", "DELETE", "PATCH"}
        exempt_paths = []

        if request.method not in unsafe_methods:
            return await call_next(request)

        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        host = request.headers.get("host", "localhost:8000")
        allowed_origins = [
            f"http://{host}",
            f"https://{host}",
            "http://localhost:8000",
            "https://localhost:8000",
            "http://127.0.0.1:8000",
            "https://127.0.0.1:8000",
        ]

        origin_valid = False

        if origin:
            origin_valid = origin in allowed_origins
        elif referer:
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
        public_paths = ["/login", "/static", "/auth/", "/favicon.ico"]

        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        user = get_current_user(request)
        if not user:
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Non authentifié"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

        request.state.user = user
        return await call_next(request)


# Middlewares — ordre inversé (dernier ajouté s'exécute en premier)
app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=get_session_secret())

# Initialiser les settings au démarrage
load_settings()


# === MAIN ===

if __name__ == "__main__":
    import uvicorn

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

    auth_password = os.getenv("AUTH_PASSWORD", "")
    if not auth_password or auth_password == "CHANGE_ME_ON_FIRST_INSTALL":  # pragma: allowlist secret
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
