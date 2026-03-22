import json
import os
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
jobs = {}

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
