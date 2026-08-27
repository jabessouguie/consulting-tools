import json
import os
import time
import uuid
from pathlib import Path
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.templating import Jinja2Templates
from utils.consultant_db import ConsultantDatabase
from utils.elearning_db import ElearningDatabase
from utils.tender_db import TenderDatabase

# Base Directory
BASE_DIR = Path(__file__).parent.parent

# Shared Globals
# Registre des jobs de fond. Purge par create_job() : sans cela le dict croit
# indefiniment sur un serveur long-running, chaque entree gardant son resultat
# complet en memoire.
jobs = {}

# Un job est purgeable au-dela de cette duree, quel que soit son statut : un job
# encore "running" apres une heure est un thread mort.
JOB_TTL_SECONDS = 3600
# Plafond dur, pour le cas ou des jobs arriveraient plus vite que le TTL.
MAX_JOBS = 200

# Shared DB Instances (to be initialized in app.py or here)
# We'll initialize them here to be shared across routers and app.py
skills_market_db = ConsultantDatabase()
elearning_db = ElearningDatabase()
tender_db = TenderDatabase()

# Shared Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])

# Shared Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Shared Consultant Info
from config import get_consultant_info
try:
    _config = get_consultant_info()
    CONSULTANT_NAME = _config.get("name", "Consultant")
    COMPANY_NAME = _config.get("company", "Consulting Tools")
except Exception:
    CONSULTANT_NAME = "Consultant"
    COMPANY_NAME = "Consulting Tools"

# Global model settings (in-memory, persists per session)
AVAILABLE_GEMINI_MODELS = {
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview 🔥",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview ⚡",
    "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite",
    "deep-research-pro-preview-12-2025": "Deep Research Pro 🔬",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini-2.0-flash-001": "Gemini 2.0 Flash 001",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
    "gemini-2.0-flash-lite-001": "Gemini 2.0 Flash Lite 001",
    "gemini-flash-latest": "Gemini Flash (Latest)",
    "gemini-pro-latest": "Gemini Pro (Latest)",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
}
SELECTED_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
IMAGE_MODEL = "gemini-3-pro-image-preview"

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

def prune_jobs() -> int:
    """
    Supprime les jobs expires. Retourne le nombre de jobs retires.

    Un job sans `created_at` (cree par du code anterieur au registre horodate)
    est considere comme datant de maintenant : il sera purge au tour suivant
    plutot que d'etre supprime pendant qu'il tourne encore.
    """
    now = time.time()
    expired = [
        jid
        for jid, job in jobs.items()
        if now - job.setdefault("created_at", now) > JOB_TTL_SECONDS
    ]
    for jid in expired:
        jobs.pop(jid, None)

    # Plafond dur : on evince les plus anciens au-dela de MAX_JOBS.
    if len(jobs) > MAX_JOBS:
        oldest = sorted(jobs.items(), key=lambda kv: kv[1].get("created_at", 0))
        for jid, _ in oldest[: len(jobs) - MAX_JOBS]:
            jobs.pop(jid, None)
            expired.append(jid)

    return len(expired)


def create_job(job_type: str, **extra) -> str:
    """
    Cree un job de fond et retourne son identifiant.

    Centralise le boilerplate identique repete dans chaque router
    (uuid tronque + dict de statut) et purge les jobs expires au passage.
    """
    prune_jobs()
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": job_type,
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
        "created_at": time.time(),
        **extra,
    }
    return job_id


def send_sse(event: str, data: dict) -> str:
    """Formate un message SSE (Server-Sent Events)"""
    import json
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def safe_error_message(error: Exception, context: str = "") -> str:
    from utils.validation import sanitize_error_message
    error_msg = str(error)
    sanitized = sanitize_error_message(error_msg)
    if context:
        return f"{context}: {sanitized}"
    return sanitized

def safe_traceback() -> str:
    from utils.validation import sanitize_error_message
    import traceback
    tb = traceback.format_exc()
    return sanitize_error_message(tb)
