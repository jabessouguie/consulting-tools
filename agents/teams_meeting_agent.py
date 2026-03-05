"""
TeamsMeetingAgent — Analyse des réunions Microsoft Teams via Graph API.

Pipeline :
1. Tenter de récupérer la transcription native via Graph API (get_teams_transcript)
2. Si disponible → analyser le texte via MeetingSummarizerAgent
3. Sinon → déléguer à GeminiVideoAnalyzer pour l'analyse vidéo

Retourne le même format que MeetingCaptureAgent / MeetingSummarizerAgent.
"""

import os
from typing import Any, Dict, Optional


class TeamsMeetingAgent:
    """
    Agent d'analyse de réunions Microsoft Teams.

    Utilise Microsoft Graph API pour accéder aux transcriptions natives,
    avec fallback vers l'analyse vidéo Gemini si indisponible.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Args:
            api_key: Clé API Gemini (pour le fallback vidéo).
            tenant_id: ID du tenant Microsoft Azure AD.
            client_id: ID du client application Azure AD.
            client_secret: Secret client Azure AD.
        """
        from utils.microsoft_client import MicrosoftClient

        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.ms = MicrosoftClient(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    def analyze_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Analyse une réunion Teams.

        Stratégie :
        1. Tente d'obtenir la transcription native Teams (Graph API)
        2. Si disponible → résumé via MeetingSummarizerAgent
        3. Sinon → lève une erreur explicite (enregistrement vidéo requis)

        Args:
            meeting_id: ID de la réunion Teams (onlineMeeting ID).

        Returns:
            Dict avec :
                - "minutes" (str) : compte rendu au format Markdown
                - "email" (dict) : email de partage {subject, body}
                - "source" (str) : "transcript" ou "error"
                - "generated_at" (str) : timestamp ISO
        """
        from datetime import datetime

        # 1. Essayer la transcription native
        transcript = self._get_transcript(meeting_id)

        if transcript:
            return self._analyze_transcript(transcript, meeting_id)

        # 2. Pas de transcription disponible
        return {
            "error": (
                "Aucune transcription disponible pour cette réunion Teams. "
                "Activez les transcriptions dans les paramètres Teams et relancez."
            ),
            "meeting_id": meeting_id,
            "source": "error",
            "generated_at": datetime.now().isoformat(),
        }

    def _get_transcript(self, meeting_id: str) -> str:
        """
        Tente de récupérer la transcription depuis Graph API.

        Returns:
            Texte de la transcription, ou "" si indisponible.
        """
        try:
            return self.ms.get_teams_transcript(meeting_id)
        except Exception:
            return ""

    def _analyze_transcript(self, transcript: str, meeting_id: str) -> Dict[str, Any]:
        """
        Analyse un transcript textuel via MeetingSummarizerAgent.

        Args:
            transcript: Texte de la transcription.
            meeting_id: ID de la réunion (pour les métadonnées).

        Returns:
            Dict avec minutes, email, source, generated_at.
        """
        from agents.meeting_summarizer import MeetingSummarizerAgent

        summarizer = MeetingSummarizerAgent()
        result = summarizer.run(transcript, generate_email=True)
        result["source"] = "transcript"
        result["meeting_id"] = meeting_id
        return result
