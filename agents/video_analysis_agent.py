"""
Abstraction couche d'analyse vidéo — permet un fallback gracieux quand Gemini n'est pas le provider.

Classes:
    VideoAnalysisInterface  — interface abstraite
    GeminiVideoAnalyzer     — implémentation via Gemini File API
    UnsupportedVideoAnalyzer — fallback pour Claude/OpenAI (pas de support vidéo natif)

Factory:
    get_video_analyzer(api_key, provider) → VideoAnalysisInterface
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class UnsupportedFeatureError(Exception):
    """Levée quand une fonctionnalité n'est pas supportée par le provider actuel."""


class VideoAnalysisInterface(ABC):
    """Interface abstraite pour l'analyse de réunions vidéo."""

    @abstractmethod
    def analyze_video(self, file_path: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyse une vidéo et retourne les résultats structurés.

        Args:
            file_path: Chemin local vers le fichier vidéo.
            model: Modèle à utiliser (optionnel).

        Returns:
            Dict avec les résultats de l'analyse (transcript, summary, …)
        """

    @staticmethod
    def supports_video() -> bool:
        """Retourne True si ce provider supporte l'analyse vidéo."""
        return False


class GeminiVideoAnalyzer(VideoAnalysisInterface):
    """Analyse vidéo via Gemini File API (google.generativeai)."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Args:
            api_key: Clé API Gemini.
            model: Modèle Gemini à utiliser (défaut: gemini-3.1-flash).
        """
        self.api_key = api_key
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash")

    @staticmethod
    def supports_video() -> bool:
        return True

    def analyze_video(self, file_path: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyse la vidéo via Gemini File API.

        Délègue à MeetingCaptureAgent pour réutiliser la logique existante.
        """
        from agents.meeting_capture_agent import MeetingCaptureAgent

        agent = MeetingCaptureAgent(
            api_key=self.api_key,
            model=model or self.model_name,
        )
        uploaded = agent.upload_video(file_path)
        return agent.analyze(uploaded)


class UnsupportedVideoAnalyzer(VideoAnalysisInterface):
    """Fallback pour les providers ne supportant pas l'analyse vidéo (Claude, OpenAI)."""

    def __init__(self, provider: str = "unknown"):
        self.provider = provider

    @staticmethod
    def supports_video() -> bool:
        return False

    def analyze_video(self, file_path: str, model: Optional[str] = None) -> Dict[str, Any]:
        raise UnsupportedFeatureError(
            "L'analyse vidéo nécessite Gemini comme provider. "
            "Changez le fournisseur IA dans /settings pour utiliser cette fonctionnalité."
        )


def get_video_analyzer(
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> VideoAnalysisInterface:
    """
    Factory : retourne l'analyseur vidéo adapté au provider.

    Args:
        api_key: Clé API (utilisée pour Gemini).
        provider: 'gemini', 'claude' ou 'openai'. Si None, lit LLM_PROVIDER.

    Returns:
        GeminiVideoAnalyzer si provider == 'gemini', sinon UnsupportedVideoAnalyzer.
    """
    resolved_provider = provider or os.getenv("LLM_PROVIDER", "gemini")
    if resolved_provider == "gemini":
        resolved_key = api_key or os.getenv("GEMINI_API_KEY", "")
        return GeminiVideoAnalyzer(api_key=resolved_key)
    return UnsupportedVideoAnalyzer(provider=resolved_provider)
