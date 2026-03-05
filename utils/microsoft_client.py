"""
MicrosoftClient — Authentification et appels Microsoft Graph API via MSAL.

Fonctionnalités :
- Authentification client_credentials (app-only)
- Envoi de messages Teams
- Upload vers OneDrive
- Création de brouillons Outlook
- Lecture de transcriptions Teams (bêta)
"""

import os
from typing import Any, Dict, List, Optional


class MicrosoftAuthError(Exception):
    """Levée quand l'authentification Microsoft échoue."""


class MicrosoftAPIError(Exception):
    """Levée quand un appel Graph API échoue."""


class MicrosoftClient:
    """
    Client Microsoft Graph API avec authentification MSAL.

    Usage::

        client = MicrosoftClient(
            tenant_id="...",
            client_id="...",
            client_secret="...",
        )
        token = client.authenticate(["https://graph.microsoft.com/.default"])
        client.send_teams_message(channel_id="...", message="Hello Teams!")
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.tenant_id = tenant_id or os.getenv("MICROSOFT_TENANT_ID", "")
        self.client_id = client_id or os.getenv("MICROSOFT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self._app = None
        self._token_cache: Dict[str, str] = {}

    def _get_app(self):
        """Initialise l'application MSAL (lazy)."""
        if self._app is None:
            try:
                import msal
            except ImportError as exc:
                raise MicrosoftAuthError(
                    "msal n'est pas installé. Exécutez : pip install msal"
                ) from exc

            if not all([self.tenant_id, self.client_id, self.client_secret]):
                raise MicrosoftAuthError(
                    "tenant_id, client_id et client_secret sont requis."
                )

            authority = "https://login.microsoftonline.com/" + self.tenant_id
            self._app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=authority,
                client_credential=self.client_secret,
            )
        return self._app

    def authenticate(self, scopes: Optional[List[str]] = None) -> str:
        """
        Obtient un token d'accès via client_credentials flow.

        Args:
            scopes: Scopes Microsoft (défaut: Graph API).

        Returns:
            Token d'accès (str).

        Raises:
            MicrosoftAuthError: si l'authentification échoue.
        """
        if scopes is None:
            scopes = ["https://graph.microsoft.com/.default"]

        scope_key = ",".join(sorted(scopes))
        if scope_key in self._token_cache:
            return self._token_cache[scope_key]

        app = self._get_app()
        result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown"))
            raise MicrosoftAuthError("Authentification Microsoft échouée : " + error)

        token = result["access_token"]
        self._token_cache[scope_key] = token
        return token

    def _headers(self) -> Dict[str, str]:
        """Retourne les headers HTTP avec le token Bearer."""
        token = self.authenticate()
        return {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        }

    def _graph_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        files: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Effectue un appel Graph API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            path: Chemin relatif à GRAPH_BASE.
            json_data: Corps JSON de la requête.
            files: Données binaires (pour uploads).
            content_type: Override du Content-Type.

        Returns:
            Réponse JSON (dict) ou {} si 204 No Content.

        Raises:
            MicrosoftAPIError: si la réponse HTTP est une erreur.
        """
        try:
            import requests
        except ImportError as exc:
            raise MicrosoftAPIError("requests n'est pas installé.") from exc

        url = self.GRAPH_BASE + path
        headers = self._headers()

        if content_type:
            headers["Content-Type"] = content_type
        if files is not None:
            headers.pop("Content-Type", None)

        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_data,
            data=files,
            timeout=30,
        )

        if response.status_code == 204:
            return {}

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        if not response.ok:
            error_msg = data.get("error", {}).get("message", response.text)
            raise MicrosoftAPIError(
                "Graph API " + method.upper() + " " + path + " → "
                + str(response.status_code) + ": " + error_msg
            )

        return data

    def send_teams_message(self, channel_id: str, message: str) -> Dict[str, Any]:
        """
        Envoie un message dans un canal Teams.

        Args:
            channel_id: ID du canal Teams (format: teamId/channelId).
            message: Contenu HTML du message.

        Returns:
            Réponse Graph API de la création du message.
        """
        parts = channel_id.split("/")
        if len(parts) != 2:
            raise MicrosoftAPIError(
                "channel_id doit être au format 'teamId/channelId'"
            )
        team_id, chan_id = parts
        path = "/teams/" + team_id + "/channels/" + chan_id + "/messages"
        return self._graph_request(
            "POST",
            path,
            json_data={"body": {"contentType": "html", "content": message}},
        )

    def upload_to_onedrive(self, file_path: str, remote_path: str) -> Dict[str, Any]:
        """
        Upload un fichier vers OneDrive (me/drive).

        Args:
            file_path: Chemin local du fichier.
            remote_path: Chemin distant dans OneDrive (ex: /Documents/report.docx).

        Returns:
            Métadonnées du fichier uploadé.
        """
        from pathlib import Path

        content = Path(file_path).read_bytes()
        encoded_path = remote_path.lstrip("/")
        path = "/me/drive/root:/" + encoded_path + ":/content"
        return self._graph_request(
            "PUT",
            path,
            files=content,
            content_type="application/octet-stream",
        )

    def get_sharepoint_files(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Liste les fichiers d'un site SharePoint.

        Args:
            site_id: ID du site SharePoint.

        Returns:
            Liste des éléments du drive racine.
        """
        path = "/sites/" + site_id + "/drive/root/children"
        data = self._graph_request("GET", path)
        return data.get("value", [])

    def get_teams_transcript(self, meeting_id: str) -> str:
        """
        Récupère la transcription d'une réunion Teams.

        Args:
            meeting_id: ID de la réunion Teams.

        Returns:
            Texte de la transcription (VTT ou texte brut).
        """
        path = "/me/onlineMeetings/" + meeting_id + "/transcripts"
        data = self._graph_request("GET", path)
        transcripts = data.get("value", [])

        if not transcripts:
            return ""

        # Prendre la première transcription disponible
        transcript_id = transcripts[0].get("id", "")
        if not transcript_id:
            return ""

        content_path = (
            "/me/onlineMeetings/" + meeting_id
            + "/transcripts/" + transcript_id + "/content"
        )
        content_data = self._graph_request("GET", content_path)
        return content_data.get("content", "") or str(content_data)

    def create_outlook_draft(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = "HTML",
    ) -> Dict[str, Any]:
        """
        Crée un brouillon dans Outlook.

        Args:
            to: Adresse email du destinataire.
            subject: Objet du message.
            body: Corps du message (HTML ou texte).
            body_type: "HTML" ou "Text".

        Returns:
            Métadonnées du brouillon créé (dont id).
        """
        return self._graph_request(
            "POST",
            "/me/messages",
            json_data={
                "subject": subject,
                "body": {"contentType": body_type, "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": to}}
                ],
            },
        )

    def test_connection(self) -> bool:
        """
        Vérifie que les credentials fonctionnent via un appel GET /me/drive.

        Returns:
            True si la connexion est établie.

        Raises:
            MicrosoftAuthError, MicrosoftAPIError si la connexion échoue.
        """
        self._graph_request("GET", "/me/drive")
        return True
