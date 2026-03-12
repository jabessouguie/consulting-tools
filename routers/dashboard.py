"""Router: Dashboard, Settings et pages principales"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from routers.shared import (
    BASE_DIR,
    limiter,
    templates,
    CONSULTANT_NAME,
    AVAILABLE_GEMINI_MODELS,
    SELECTED_GEMINI_MODEL,
    IMAGE_MODEL,
    save_settings,
)

router = APIRouter()


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


# === SETTINGS API ===


@router.get("/api/settings/model")
async def get_model_settings():
    """Retourne le modele Gemini selectionne et la liste des modeles disponibles"""
    import routers.shared as shared
    return {
        "current_model": shared.SELECTED_GEMINI_MODEL,
        "available_models": shared.AVAILABLE_GEMINI_MODELS,
        "image_model": shared.IMAGE_MODEL,
    }


@router.post("/api/settings/model")
async def set_model_settings(request: Request):
    """Met a jour le modele Gemini selectionne"""
    import routers.shared as shared
    data = await request.json()
    model = data.get("model")
    if model not in shared.AVAILABLE_GEMINI_MODELS:
        return JSONResponse({"error": "Modele inconnu"}, status_code=400)
    shared.SELECTED_GEMINI_MODEL = model
    shared.save_settings()
    return {"success": True, "model": model}


# === PAGE ROUTES ===


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "active": "dashboard",
            "consultant_name": CONSULTANT_NAME,
            "stats": get_stats(),
            "recent_files": get_recent_files(),
        },
    )


@router.get("/proposal", response_class=HTMLResponse)
async def proposal_page(request: Request):
    return templates.TemplateResponse(
        "proposal.html",
        {
            "request": request,
            "active": "proposal",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.get("/proposal-modular", response_class=HTMLResponse)
async def proposal_modular_page(request: Request):
    return templates.TemplateResponse(
        "proposal-modular.html",
        {
            "request": request,
            "active": "proposal",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.get("/linkedin", response_class=HTMLResponse)
async def linkedin_page(request: Request):
    return templates.TemplateResponse(
        "linkedin.html",
        {
            "request": request,
            "active": "linkedin",
            "consultant_name": CONSULTANT_NAME,
        },
    )
