"""Router: Analytics — GET /analytics, GET /api/analytics/stats, GET /api/analytics/llm"""
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from routers.shared import CONSULTANT_NAME, templates
from utils.observability import DB_PATH, obs_service

router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "active": "analytics",
            "consultant_name": CONSULTANT_NAME,
        },
    )


@router.get("/api/analytics/stats")
async def api_analytics_stats():
    """KPIs : système, IA, produit."""
    try:
        return JSONResponse(obs_service.get_stats_summary())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/analytics/llm")
async def api_analytics_llm():
    """Détail des appels LLM : par feature, par modèle, coûts."""
    if not DB_PATH.exists():
        return JSONResponse({"by_feature": [], "by_model": [], "recent": []})
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            by_feature = [dict(r) for r in conn.execute(
                """SELECT feature, COUNT(*) as calls,
                          SUM(total_tokens) as tokens,
                          ROUND(SUM(cost_usd), 4) as cost_usd,
                          ROUND(AVG(latency_ms), 0) as avg_latency_ms
                   FROM llm_logs GROUP BY feature ORDER BY calls DESC LIMIT 10"""
            ).fetchall()]
            by_model = [dict(r) for r in conn.execute(
                """SELECT model, provider, COUNT(*) as calls,
                          ROUND(SUM(cost_usd), 4) as cost_usd
                   FROM llm_logs GROUP BY model ORDER BY calls DESC"""
            ).fetchall()]
            recent = [dict(r) for r in conn.execute(
                """SELECT timestamp, feature, model, total_tokens,
                          ROUND(cost_usd, 6) as cost_usd, latency_ms, status
                   FROM llm_logs ORDER BY timestamp DESC LIMIT 20"""
            ).fetchall()]
        return JSONResponse({"by_feature": by_feature, "by_model": by_model, "recent": recent})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/analytics/requests")
async def api_analytics_requests():
    """Top endpoints HTTP par volume et latence."""
    if not DB_PATH.exists():
        return JSONResponse({"top_endpoints": [], "daily": []})
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            top_endpoints = [dict(r) for r in conn.execute(
                """SELECT endpoint, COUNT(*) as hits,
                          ROUND(AVG(duration_ms), 0) as avg_ms,
                          SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
                   FROM http_metrics GROUP BY endpoint ORDER BY hits DESC LIMIT 15"""
            ).fetchall()]
            daily = [dict(r) for r in conn.execute(
                """SELECT DATE(timestamp) as day, COUNT(*) as requests,
                          ROUND(AVG(duration_ms), 0) as avg_ms
                   FROM http_metrics GROUP BY day ORDER BY day DESC LIMIT 30"""
            ).fetchall()]
        return JSONResponse({"top_endpoints": top_endpoints, "daily": daily})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
