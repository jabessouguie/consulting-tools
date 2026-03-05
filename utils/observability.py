"""
Service d'observabilité pour WEnvision.
Gère les logs systeme, l'analytique produit et le suivi LLM.
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

DB_PATH = Path("data/monitoring/observability.db")


class ObservabilityService:
    """Service central pour la collecte de métriques et logs."""

    def __init__(self):
        os.makedirs(DB_PATH.parent, exist_ok=True)
        self._init_db()
        # Cache local pour les flushs asynchrones si nécessaire
        self._lock = threading.Lock()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            # Table pour la télémétrie HTTP
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS http_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    method TEXT,
                    endpoint TEXT,
                    status_code INTEGER,
                    duration_ms REAL,
                    user_id TEXT,
                    ip_address TEXT
                )
            """
            )
            # Table pour l'observabilité LLM (FinOps)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT,
                    model TEXT,
                    feature TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd REAL,
                    latency_ms REAL,
                    status TEXT,
                    user_id TEXT
                )
            """
            )
            # Table pour l'adoption produit (Events)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    event_name TEXT,
                    properties TEXT
                )
            """
            )

    def log_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        user_id: str = "anonymous",
        ip: str = "",
    ):
        with self._lock, sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO http_metrics (method, endpoint, status_code, duration_ms, user_id, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
                (method, endpoint, status, duration, user_id, ip),
            )

    def log_llm_call(
        self,
        provider: str,
        model: str,
        feature: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float,
        status: str = "success",
        user_id: str = "anonymous",
    ):
        # Estimation simplifiée du coût (exemple: $15/M tokens pour Claude Opus, $0.5/M tokens pour Gemini Flash)
        # En production, on utiliserait une table de prix dynamique
        price_per_1k = 0.015 if "opus" in model.lower() else 0.0005
        cost = ((prompt_tokens + completion_tokens) / 1000) * price_per_1k

        with self._lock, sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO llm_logs
                   (provider, model, feature, prompt_tokens, completion_tokens, total_tokens, cost_usd, latency_ms, status, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    provider,
                    model,
                    feature,
                    prompt_tokens,
                    completion_tokens,
                    prompt_tokens + completion_tokens,
                    cost,
                    duration,
                    status,
                    user_id,
                ),
            )

    def log_event(self, event_name: str, user_id: str = "anonymous", properties: Dict = None):
        props_json = json.dumps(properties or {})
        with self._lock, sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO product_events (user_id, event_name, properties) VALUES (?, ?, ?)",
                (user_id, event_name, props_json),
            )

    def get_stats_summary(self) -> Dict[str, Any]:
        """Récupère une synthèse pour le Dashboard."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            # KPI System
            health = conn.execute(
                "SELECT AVG(duration_ms) as avg_lat, COUNT(*) as total_req FROM http_metrics"
            ).fetchone()
            errors = conn.execute(
                "SELECT COUNT(*) as count FROM http_metrics WHERE status_code >= 400"
            ).fetchone()

            # KPI AI
            ai_stats = conn.execute(
                "SELECT SUM(total_tokens) as tokens, SUM(cost_usd) as cost, AVG(latency_ms) as avg_lat FROM llm_logs"
            ).fetchone()

            # KPI Product
            active_users = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as count FROM product_events WHERE timestamp > date('now', '-30 days')"
            ).fetchone()
            top_features = conn.execute(
                "SELECT event_name, COUNT(*) as count FROM product_events GROUP BY event_name ORDER BY count DESC LIMIT 5"
            ).fetchall()

            return {
                "system": {
                    "avg_latency": round(health["avg_lat"] or 0, 2),
                    "total_requests": health["total_req"],
                    "error_rate": round(
                        (
                            (errors["count"] / health["total_req"] * 100)
                            if health["total_req"] > 0
                            else 0
                        ),
                        2,
                    ),
                },
                "ai": {
                    "total_tokens": ai_stats["tokens"] or 0,
                    "total_cost_usd": round(ai_stats["cost"] or 0, 4),
                    "avg_llm_latency": round(ai_stats["avg_lat"] or 0, 2),
                },
                "product": {
                    "active_users_30d": active_users["count"],
                    "top_features": [dict(f) for f in top_features],
                },
            }


# Instanciation
obs_service = ObservabilityService()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware pour intercepter et logger chaque requête."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # On essaie de récupérer l'ID utilisateur (dépend de votre système d'auth)
        user_id = "anonymous"
        if "user" in request.scope and hasattr(request.scope["user"], "id"):
            user_id = str(request.scope["user"].id)

        response = await call_next(request)

        duration = (time.time() - start_time) * 1000  # ms

        # On ignore le "bruit" technique pour ne pas polluer les stats
        path = request.url.path
        noise_prefixes = ("/static", "/favicon", "/.well-known", "/robots.txt")

        if not path.startswith(noise_prefixes):
            obs_service.log_http_request(
                method=request.method,
                endpoint=path,
                status=response.status_code,
                duration=duration,
                user_id=user_id,
                ip=request.client.host if request.client else "",
            )

        return response
