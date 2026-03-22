"""Router: Settings & Theme — GET/POST /settings, /api/settings, /theme.css, /api/settings/theme-import"""
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from routers.shared import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from utils.theme_manager import ThemeManager
    settings = ThemeManager.load()
    return templates.TemplateResponse(
        "settings.html", {"request": request, "settings": settings}
    )


@router.get("/api/settings")
async def get_api_settings():
    from utils.theme_manager import ThemeManager
    return JSONResponse(ThemeManager.load())


@router.post("/api/settings")
async def post_api_settings(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON invalide"}, status_code=400)
    if "theme" in body and not isinstance(body["theme"], dict):
        return JSONResponse({"error": "theme doit être un objet"}, status_code=400)
    from utils.theme_manager import ThemeManager
    current = ThemeManager.load()
    current.update(body)
    if "theme" in body and isinstance(body["theme"], dict):
        current["theme"] = dict(current.get("theme", {}))
        current["theme"].update(body["theme"])
    ThemeManager.save(current)
    return JSONResponse({"success": True})


@router.get("/theme.css")
async def theme_css():
    from utils.theme_manager import ThemeManager
    vars_ = ThemeManager.get_css_vars()
    css = ":root {\n"
    css += f"  --corail: {vars_.get('primary_color', '#FF6B58')};\n"
    css += f"  --noir-profond: {vars_.get('secondary_color', '#FBF0F4')};\n"
    css += f"  --background: {vars_.get('background_color', '#1F1F1F')};\n"
    css += f"  --text: {vars_.get('text_color', '#474747')};\n"
    css += f"  --accent: {vars_.get('accent_color', '#3A3A3B')};\n"
    css += f"  --body-font: {vars_.get('body_font', 'Inter, sans-serif')};\n"
    css += f"  --title-font: {vars_.get('title_font', 'Chakra Petch, sans-serif')};\n"
    css += "}\n"
    return Response(content=css, media_type="text/css")


@router.post("/api/settings/theme-import")
async def import_theme(file: UploadFile = File(...)):
    from utils.theme_manager import ThemeManager
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in (".pptx", ".pdf"):
        return JSONResponse(
            {"error": "Seuls les fichiers .pptx et .pdf sont acceptes"},
            status_code=400,
        )
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        if ext == ".pptx":
            theme = ThemeManager.import_from_pptx(tmp_path)
        else:
            theme = ThemeManager.import_from_pdf(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    if not theme:
        return JSONResponse(
            {"error": "Aucune couleur extraite du fichier"}, status_code=422
        )
    return JSONResponse({"theme": theme})
