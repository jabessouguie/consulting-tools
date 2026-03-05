"""
Agent MeetingCapture AI
Analyse une vidéo de réunion via l'API Gemini File API (multimodale)
et génère une transcription, un compte rendu et un brouillon d'email.
Fournit également un client Gmail OAuth2 pour créer un brouillon directement.
"""

import json
import re
import time
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import Any, Dict

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

GEMINI_MODELS: Dict[str, str] = {
    "gemini-2.0-flash": "Gemini 2.0 Flash (Optimisé)",
    "gemini-1.5-pro": "Gemini 1.5 Pro (Haute Qualité)",
    "gemini-1.5-flash": "Gemini 1.5 Flash (Rapide)",
}
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

_ANALYZE_PROMPT = (
    "Tu es un assistant de réunion. Analyse cette vidéo et réponds UNIQUEMENT en JSON valide "
    "avec les clés : transcript (diarisation par locuteur + horodatage + notes contextuelles "
    "visuelles entre crochets), summary (resume_executif, points_cles, plan_action), "
    "email_brouillon (objet, corps). Identifie les locuteurs comme \"Locuteur A/B/...\"."
)

_REQUIRED_KEYS = {"transcript", "summary", "email_brouillon"}
_REQUIRED_SUMMARY_KEYS = {"resume_executif", "points_cles", "plan_action"}
_REQUIRED_EMAIL_KEYS = {"objet", "corps"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class APIKeyError(Exception):
    """Clé API Gemini invalide ou manquante."""


class QuotaExceededError(Exception):
    """Quota Gemini dépassé."""


class VideoProcessingError(Exception):
    """Erreur lors du traitement ou de l'analyse de la vidéo."""


class AuthenticationError(Exception):
    """Échec de l'authentification OAuth2 Gmail."""


class DraftCreationError(Exception):
    """Échec de la création du brouillon Gmail."""


# ---------------------------------------------------------------------------
# MeetingCaptureAgent
# ---------------------------------------------------------------------------

class MeetingCaptureAgent:
    """Analyse une vidéo de réunion avec le Gemini File API."""

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        if not api_key or api_key.strip() == "":
            raise APIKeyError("La clé API Gemini est vide ou manquante.")
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_video(self, file_path: str) -> Any:
        """Upload une vidéo via le Gemini File API.

        Args:
            file_path: Chemin local vers le fichier vidéo.

        Returns:
            Objet File retourné par genai.upload_file.

        Raises:
            APIKeyError: Si la clé API est refusée.
            QuotaExceededError: Si le quota est dépassé.
            VideoProcessingError: Pour toute autre erreur d'upload.
        """
        path = Path(file_path)
        if not path.exists():
            raise VideoProcessingError("Fichier vidéo introuvable : " + file_path)

        try:
            uploaded = genai.upload_file(str(path), mime_type=_infer_mime(path))
            return uploaded
        except GoogleAPIError as exc:
            msg = str(exc).lower()
            if "api key" in msg or "permission denied" in msg or "unauthenticated" in msg:
                raise APIKeyError("Clé API Gemini invalide.") from exc
            if "quota" in msg or "resource exhausted" in msg:
                raise QuotaExceededError("Quota Gemini dépassé.") from exc
            raise VideoProcessingError("Erreur d'upload : " + str(exc)) from exc
        except Exception as exc:
            msg = str(exc).lower()
            if "api key" in msg or "permission" in msg or "unauthenticated" in msg:
                raise APIKeyError("Clé API Gemini invalide.") from exc
            if "quota" in msg or "resource exhausted" in msg:
                raise QuotaExceededError("Quota Gemini dépassé.") from exc
            raise VideoProcessingError("Erreur d'upload : " + str(exc)) from exc

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def wait_for_processing(
        self,
        file: Any,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> Any:
        """Attend que le Gemini File API finisse de traiter le fichier.

        Args:
            file: Objet File retourné par upload_video.
            timeout: Délai maximal en secondes.
            poll_interval: Intervalle entre chaque poll en secondes.

        Returns:
            Objet File avec state == ACTIVE.

        Raises:
            TimeoutError: Si le délai est dépassé.
            VideoProcessingError: Si le traitement a échoué côté Gemini.
        """
        deadline = time.time() + timeout
        while True:
            current = genai.get_file(file.name)
            state = str(current.state).upper()
            if "ACTIVE" in state:
                return current
            if "FAILED" in state or "ERROR" in state:
                raise VideoProcessingError(
                    "Le traitement de la vidéo a échoué côté Gemini (state=" + state + ")."
                )
            if time.time() >= deadline:
                raise TimeoutError(
                    "Délai dépassé (" + str(timeout) + "s) : la vidéo n'est pas encore traitée."
                )
            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------------

    def analyze(self, file: Any) -> dict:
        """Appelle le modèle Gemini sur la vidéo uploadée.

        Args:
            file: Objet File ACTIVE retourné par wait_for_processing.

        Returns:
            Dictionnaire analysé issu de parse_response.

        Raises:
            VideoProcessingError: En cas d'erreur de génération ou de parsing.
        """
        try:
            response = self.model.generate_content([file, _ANALYZE_PROMPT])
            return self.parse_response(response.text)
        except (VideoProcessingError, APIKeyError, QuotaExceededError):
            raise
        except Exception as exc:
            raise VideoProcessingError("Erreur d'analyse : " + str(exc)) from exc

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_response(self, raw: str) -> dict:
        """Nettoie et valide la réponse JSON du modèle.

        Args:
            raw: Texte brut retourné par le modèle.

        Returns:
            Dictionnaire validé avec les clés attendues.

        Raises:
            VideoProcessingError: Si le JSON est invalide ou incomplet.
        """
        cleaned = raw.strip()

        # Supprimer les fences Markdown (```json ... ``` ou ``` ... ```)
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise VideoProcessingError("JSON invalide dans la réponse Gemini.") from exc

        if not isinstance(data, dict):
            raise VideoProcessingError("La réponse Gemini n'est pas un objet JSON.")

        missing = _REQUIRED_KEYS - data.keys()
        if missing:
            raise VideoProcessingError(
                "Clés manquantes dans la réponse : " + ", ".join(sorted(missing))
            )

        if not isinstance(data.get("summary"), dict):
            raise VideoProcessingError("La clé 'summary' doit être un objet JSON.")

        missing_summary = _REQUIRED_SUMMARY_KEYS - data["summary"].keys()
        if missing_summary:
            raise VideoProcessingError(
                "Clés manquantes dans summary : " + ", ".join(sorted(missing_summary))
            )

        if not isinstance(data.get("email_brouillon"), dict):
            raise VideoProcessingError("La clé 'email_brouillon' doit être un objet JSON.")

        missing_email = _REQUIRED_EMAIL_KEYS - data["email_brouillon"].keys()
        if missing_email:
            raise VideoProcessingError(
                "Clés manquantes dans email_brouillon : " + ", ".join(sorted(missing_email))
            )

        return data


# ---------------------------------------------------------------------------
# MeetingGmailClient
# ---------------------------------------------------------------------------

class MeetingGmailClient:
    """Client Gmail OAuth2 pour créer des brouillons."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

    def authenticate(self, credentials_path: str, token_path: str) -> Any:
        """Authentifie via OAuth2 desktop flow.

        Args:
            credentials_path: Chemin vers le fichier credentials.json Google.
            token_path: Chemin où stocker/lire le token OAuth2.

        Returns:
            Objet service Google API prêt à l'emploi.

        Raises:
            AuthenticationError: En cas d'échec d'authentification.
        """
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as AuthRequest
        from googleapiclient.discovery import build

        try:
            creds = None
            token_file = Path(token_path)

            if token_file.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_file), self.SCOPES
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(AuthRequest())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(str(token_file), "w") as f:
                    f.write(creds.to_json())

            return build("gmail", "v1", credentials=creds)

        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError("Échec de l'authentification Gmail : " + str(exc)) from exc

    def create_draft(self, service: Any, to: str, subject: str, body: str) -> dict:
        """Crée un brouillon Gmail.

        Args:
            service: Service Gmail retourné par authenticate.
            to: Adresse email du destinataire.
            subject: Objet du message.
            body: Corps du message (texte brut).

        Returns:
            Dictionnaire {"id": ..., "message_id": ...}.

        Raises:
            DraftCreationError: En cas d'échec de création du brouillon.
        """
        try:
            mime_msg = MIMEText(body, "plain", "utf-8")
            mime_msg["to"] = to
            mime_msg["subject"] = subject
            raw = urlsafe_b64encode(mime_msg.as_bytes()).decode()

            draft = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            message_id = draft.get("message", {}).get("id", "")
            return {"id": draft["id"], "message_id": message_id}
        except DraftCreationError:
            raise
        except Exception as exc:
            raise DraftCreationError("Échec de création du brouillon : " + str(exc)) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_mime(path: Path) -> str:
    """Déduit le MIME type à partir de l'extension du fichier vidéo."""
    suffix = path.suffix.lower()
    _MIME_MAP = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
    }
    return _MIME_MAP.get(suffix, "video/mp4")
