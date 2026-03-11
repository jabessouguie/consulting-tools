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
