"""
Utilitaires pour interagir avec les API Google (Drive, Docs, Slides, NotebookLM)
"""

import os
import pickle
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",  # Créer et modifier des fichiers
    "https://www.googleapis.com/auth/presentations",  # Créer et modifier des présentations
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/gmail.send",  # Envoyer des emails
]


class GoogleAPIClient:
    """Client pour interagir avec les API Google"""

    def __init__(self, credentials_path: str = None):
        """
        Initialise le client Google API

        Args:
            credentials_path: Chemin vers le fichier credentials.json
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Authentifie l'utilisateur avec Google OAuth"""
        token_path = "config/token.pickle"

        # Charger les credentials existantes
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                self.creds = pickle.load(token)

        # Si pas de credentials valides, demander l'authentification
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Sauvegarder les credentials
            with open(token_path, "wb") as token:
                pickle.dump(self.creds, token)

    def get_slides_content(self, presentation_id: str) -> Dict[str, Any]:
        """
        Récupère le contenu d'une présentation Google Slides

        Args:
            presentation_id: ID de la présentation

        Returns:
            Dictionnaire contenant le contenu de la présentation
        """
        try:
            service = build("slides", "v1", credentials=self.creds)
            presentation = service.presentations().get(presentationId=presentation_id).execute()

            slides_content = []
            for i, slide in enumerate(presentation.get("slides", [])):
                slide_data = {
                    "slide_number": i + 1,
                    "object_id": slide.get("objectId"),
                    "elements": [],
                }

                # Extraire le texte de chaque élément
                for element in slide.get("pageElements", []):
                    if "shape" in element:
                        shape = element["shape"]
                        if "text" in shape:
                            text_content = self._extract_text_from_shape(shape)
                            if text_content:
                                slide_data["elements"].append(
                                    {"type": "text", "content": text_content}
                                )

                slides_content.append(slide_data)

            return {
                "title": presentation.get("title"),
                "slides": slides_content,
                "total_slides": len(slides_content),
            }

        except HttpError as error:
            print(f"Erreur lors de la récupération des slides: {error}")
            return None

    def _extract_text_from_shape(self, shape: Dict) -> str:
        """Extrait le texte d'un shape"""
        text_elements = []
        text_content = shape.get("text", {})

        for element in text_content.get("textElements", []):
            if "textRun" in element:
                text_elements.append(element["textRun"].get("content", ""))

        return "".join(text_elements).strip()

    def get_document_content(self, document_id: str) -> str:
        """
        Récupère le contenu d'un document Google Docs

        Args:
            document_id: ID du document

        Returns:
            Contenu texte du document
        """
        try:
            service = build("docs", "v1", credentials=self.creds)
            document = service.documents().get(documentId=document_id).execute()

            content = []
            for element in document.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for text_element in element["paragraph"].get("elements", []):
                        if "textRun" in text_element:
                            content.append(text_element["textRun"].get("content", ""))

            return "".join(content)

        except HttpError as error:
            print(f"Erreur lors de la récupération du document: {error}")
            return None

    def get_drive_file_content(self, file_id: str) -> Optional[str]:
        """
        Récupère le contenu d'un fichier depuis Google Drive

        Args:
            file_id: ID du fichier

        Returns:
            Contenu du fichier ou None
        """
        try:
            service = build("drive", "v3", credentials=self.creds)

            # Récupérer les métadonnées
            file = service.files().get(fileId=file_id).execute()
            mime_type = file.get("mimeType")

            # Selon le type, utiliser la bonne méthode
            if "presentation" in mime_type:
                return self.get_slides_content(file_id)
            elif "document" in mime_type:
                return self.get_document_content(file_id)
            else:
                # Export en texte brut
                content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
                return content.decode("utf-8")

        except HttpError as error:
            print(f"Erreur lors de la récupération du fichier: {error}")
            return None

    def search_files(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Recherche des fichiers dans Google Drive

        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats

        Returns:
            Liste des fichiers trouvés
        """
        try:
            service = build("drive", "v3", credentials=self.creds)

            results = (
                service.files()
                .list(
                    q=query, pageSize=max_results, fields="files(id, name, mimeType, modifiedTime)"
                )
                .execute()
            )

            return results.get("files", [])

        except HttpError as error:
            print(f"Erreur lors de la recherche: {error}")
            return []

    def create_presentation(self, title: str) -> Optional[str]:
        """
        Crée une nouvelle présentation Google Slides

        Args:
            title: Titre de la présentation

        Returns:
            ID de la présentation créée ou None en cas d'erreur
        """
        try:
            service = build("slides", "v1", credentials=self.creds)

            presentation = {"title": title}

            response = service.presentations().create(body=presentation).execute()
            presentation_id = response.get("presentationId")

            print(f"✅ Présentation créée: {presentation_id}")
            return presentation_id

        except HttpError as error:
            print(f"❌ Erreur lors de la création de la présentation: {error}")
            return None

    def add_slide(self, presentation_id: str, layout: str = "BLANK") -> Optional[str]:
        """
        Ajoute une nouvelle slide à une présentation

        Args:
            presentation_id: ID de la présentation
            layout: Type de layout ('BLANK', 'TITLE', 'TITLE_AND_BODY', etc.)

        Returns:
            ID de la slide créée ou None en cas d'erreur
        """
        try:
            service = build("slides", "v1", credentials=self.creds)

            requests = [{"createSlide": {"slideLayoutReference": {"predefinedLayout": layout}}}]

            response = (
                service.presentations()
                .batchUpdate(presentationId=presentation_id, body={"requests": requests})
                .execute()
            )

            slide_id = response.get("replies")[0]["createSlide"]["objectId"]
            return slide_id

        except HttpError as error:
            print(f"❌ Erreur lors de l'ajout de la slide: {error}")
            return None

    def add_text_to_slide(
        self,
        presentation_id: str,
        slide_id: str,
        text: str,
        position: Dict[str, float],
        size: Dict[str, float],
        font_size: int = 14,
        bold: bool = False,
    ) -> bool:
        """
        Ajoute du texte à une slide

        Args:
            presentation_id: ID de la présentation
            slide_id: ID de la slide
            text: Texte à ajouter
            position: Position {'x': 100, 'y': 100} en points
            size: Taille {'width': 300, 'height': 50} en points
            font_size: Taille de la police
            bold: Texte en gras

        Returns:
            True si succès, False sinon
        """
        try:
            service = build("slides", "v1", credentials=self.creds)

            # Sanitize le texte avant insertion
            sanitized_text = self._sanitize_text(text)

            # Créer une text box
            element_id = f'textbox_{slide_id}_{position["x"]}_{position["y"]}'

            requests = [
                {
                    "createShape": {
                        "objectId": element_id,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size["width"], "unit": "PT"},
                                "height": {"magnitude": size["height"], "unit": "PT"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": position["x"],
                                "translateY": position["y"],
                                "unit": "PT",
                            },
                        },
                    }
                },
                {"insertText": {"objectId": element_id, "text": sanitized_text}},
            ]

            # Ajouter le formatage si nécessaire
            if font_size != 14 or bold:
                requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": element_id,
                            "style": {
                                "fontSize": {"magnitude": font_size, "unit": "PT"},
                                "bold": bold,
                            },
                            "fields": "fontSize,bold",
                        }
                    }
                )

            service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()

            return True

        except HttpError as error:
            print(f"❌ Erreur lors de l'ajout du texte: {error}")
            return False

    def export_pptx_to_slides(self, slides_data: List[Dict], title: str) -> Optional[str]:
        """
        Convertit des données PPTX en présentation Google Slides

        Args:
            slides_data: Liste des slides avec leur contenu
            title: Titre de la présentation

        Returns:
            ID de la présentation créée ou None en cas d'erreur
        """
        try:
            # Créer la présentation
            presentation_id = self.create_presentation(title)
            if not presentation_id:
                return None

            service = build("slides", "v1", credentials=self.creds)

            # Supprimer la slide par défaut
            presentation = service.presentations().get(presentationId=presentation_id).execute()

            default_slide_id = presentation["slides"][0]["objectId"]

            requests = [{"deleteObject": {"objectId": default_slide_id}}]

            service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()

            # Ajouter chaque slide
            for slide_data in slides_data:
                slide_type = slide_data.get("type", "content")

                if slide_type == "cover":
                    self._add_cover_slide(presentation_id, slide_data)
                elif slide_type == "section":
                    self._add_section_slide(presentation_id, slide_data)
                elif slide_type == "closing":
                    self._add_closing_slide(presentation_id, slide_data)
                elif slide_type == "stat":
                    self._add_stat_slide(presentation_id, slide_data)
                elif slide_type == "quote":
                    self._add_quote_slide(presentation_id, slide_data)
                elif slide_type == "highlight":
                    self._add_highlight_slide(presentation_id, slide_data)
                elif slide_type == "two_column":
                    self._add_two_column_slide(presentation_id, slide_data)
                elif slide_type == "diagram":
                    self._add_diagram_slide(presentation_id, slide_data)
                elif slide_type == "table":
                    self._add_table_slide(presentation_id, slide_data)
                else:
                    self._add_content_slide(presentation_id, slide_data)

            # Générer le lien partageable
            drive_service = build("drive", "v3", credentials=self.creds)
            drive_service.permissions().create(
                fileId=presentation_id, body={"type": "anyone", "role": "writer"}
            ).execute()

            presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
            print(f"✅ Présentation Google Slides créée: {presentation_url}")

            return presentation_id

        except HttpError as error:
            print(f"❌ Erreur lors de l'export vers Google Slides: {error}")
            return None

    def _set_slide_background(
        self, presentation_id: str, slide_id: str, r: float, g: float, b: float
    ):
        """Set slide background color (r, g, b in 0.0-1.0)"""
        try:
            service = build("slides", "v1", credentials=self.creds)
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={
                    "requests": [
                        {
                            "updatePageProperties": {
                                "objectId": slide_id,
                                "pageProperties": {
                                    "pageBackgroundFill": {
                                        "solidFill": {
                                            "color": {"rgbColor": {"red": r, "green": g, "blue": b}}
                                        }
                                    }
                                },
                                "fields": "pageBackgroundFill",
                            }
                        }
                    ]
                },
            ).execute()
        except Exception as e:
            print(f"Erreur background slide: {e}")

    def _add_styled_text(
        self, presentation_id, slide_id, text, position, size, font_size=14, bold=False, color=None
    ):
        """Add text with optional color (r, g, b dict)"""
        try:
            service = build("slides", "v1", credentials=self.creds)
            sanitized_text = self._sanitize_text(text)
            eid = f'tb_{slide_id}_{position["x"]}_{position["y"]}'
            reqs = [
                {
                    "createShape": {
                        "objectId": eid,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size["width"], "unit": "PT"},
                                "height": {"magnitude": size["height"], "unit": "PT"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": position["x"],
                                "translateY": position["y"],
                                "unit": "PT",
                            },
                        },
                    }
                },
                {"insertText": {"objectId": eid, "text": sanitized_text}},
            ]
            style = {"fontSize": {"magnitude": font_size, "unit": "PT"}, "bold": bold}
            fields = "fontSize,bold"
            if color:
                style["foregroundColor"] = {"opaqueColor": {"rgbColor": color}}
                fields += ",foregroundColor"
            reqs.append(
                {
                    "updateTextStyle": {
                        "objectId": eid,
                        "style": style,
                        "fields": fields,
                    }
                }
            )
            service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": reqs}
            ).execute()
        except Exception as e:
            print(f"Erreur styled text: {e}")

    def _add_cover_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de couverture (fond sombre WEnvision)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        # Dark background (#1F1F1F)
        self._set_slide_background(presentation_id, slide_id, 0.122, 0.122, 0.122)

        white = {"red": 1.0, "green": 1.0, "blue": 1.0}
        corail = {"red": 1.0, "green": 0.42, "blue": 0.345}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 160},
                size={"width": 620, "height": 80},
                font_size=36,
                bold=True,
                color=white,
            )
        if slide_data.get("subtitle"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["subtitle"],
                position={"x": 50, "y": 260},
                size={"width": 620, "height": 50},
                font_size=18,
                color=corail,
            )

    def _add_section_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de section (fond sombre)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        self._set_slide_background(presentation_id, slide_id, 0.122, 0.122, 0.122)

        white = {"red": 1.0, "green": 1.0, "blue": 1.0}
        corail = {"red": 1.0, "green": 0.42, "blue": 0.345}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 180},
                size={"width": 620, "height": 80},
                font_size=36,
                bold=True,
                color=white,
            )
        if slide_data.get("subtitle"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["subtitle"],
                position={"x": 50, "y": 270},
                size={"width": 620, "height": 50},
                font_size=16,
                color=corail,
            )

    def _add_content_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de contenu (fond blanc)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=dark,
            )

        if slide_data.get("bullets"):
            clean = [self._sanitize_text(b) for b in slide_data["bullets"]]
            text = "\n".join([f"• {b}" for b in clean])
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 50, "y": 100},
                size={"width": 620, "height": 350},
                font_size=14,
                color=dark,
            )

    def _add_diagram_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide avec diagramme"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=dark,
            )

        if slide_data.get("elements"):
            text = "\n".join(
                [f"{i + 1}. {self._sanitize_text(e)}" for i, e in enumerate(slide_data["elements"])]
            )
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 80, "y": 100},
                size={"width": 560, "height": 350},
                font_size=14,
                color=dark,
            )

    def _add_closing_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de cloture (fond sombre)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        self._set_slide_background(presentation_id, slide_id, 0.122, 0.122, 0.122)

        white = {"red": 1.0, "green": 1.0, "blue": 1.0}
        corail = {"red": 1.0, "green": 0.42, "blue": 0.345}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 150},
                size={"width": 620, "height": 80},
                font_size=36,
                bold=True,
                color=white,
            )
        if slide_data.get("subtitle"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["subtitle"],
                position={"x": 50, "y": 250},
                size={"width": 620, "height": 50},
                font_size=16,
                color=corail,
            )

    def _add_stat_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide statistique"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}
        corail = {"red": 1.0, "green": 0.42, "blue": 0.345}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=dark,
            )
        stat_value = slide_data.get("stat_value", "")
        if stat_value:
            self._add_styled_text(
                presentation_id,
                slide_id,
                str(stat_value),
                position={"x": 100, "y": 130},
                size={"width": 520, "height": 120},
                font_size=72,
                bold=True,
                color=corail,
            )
        stat_label = slide_data.get("stat_label", "")
        if stat_label:
            self._add_styled_text(
                presentation_id,
                slide_id,
                stat_label,
                position={"x": 100, "y": 270},
                size={"width": 520, "height": 50},
                font_size=18,
                color=dark,
            )

    def _add_quote_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide citation (fond rose)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        # Rose Poudre background (#FBF0F4)
        self._set_slide_background(presentation_id, slide_id, 0.984, 0.941, 0.957)
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}

        quote = slide_data.get("quote", slide_data.get("title", ""))
        if quote:
            self._add_styled_text(
                presentation_id,
                slide_id,
                f'"{quote}"',
                position={"x": 80, "y": 120},
                size={"width": 560, "height": 150},
                font_size=22,
                color=dark,
            )
        author = slide_data.get("author", slide_data.get("subtitle", ""))
        if author:
            self._add_styled_text(
                presentation_id,
                slide_id,
                f"— {author}",
                position={"x": 80, "y": 300},
                size={"width": 560, "height": 40},
                font_size=14,
                color={"red": 0.75, "green": 0.31, "blue": 0.3},
            )

    def _add_highlight_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide points cles"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}
        corail = {"red": 1.0, "green": 0.42, "blue": 0.345}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=corail,
            )
        if slide_data.get("bullets"):
            clean = [self._sanitize_text(b) for b in slide_data["bullets"]]
            text = "\n".join([f"• {b}" for b in clean])
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 50, "y": 100},
                size={"width": 620, "height": 350},
                font_size=14,
                color=dark,
            )

    def _add_two_column_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide 2 colonnes"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=dark,
            )
        left = slide_data.get("left_bullets", slide_data.get("bullets", []))
        right = slide_data.get("right_bullets", [])
        if left:
            text = "\n".join([f"• {self._sanitize_text(b)}" for b in left])
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 30, "y": 100},
                size={"width": 310, "height": 340},
                font_size=12,
                color=dark,
            )
        if right:
            text = "\n".join([f"• {self._sanitize_text(b)}" for b in right])
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 370, "y": 100},
                size={"width": 310, "height": 340},
                font_size=12,
                color=dark,
            )

    def _add_table_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide tableau (rendu texte)"""
        slide_id = self.add_slide(presentation_id, "BLANK")
        dark = {"red": 0.122, "green": 0.122, "blue": 0.122}

        if slide_data.get("title"):
            self._add_styled_text(
                presentation_id,
                slide_id,
                slide_data["title"],
                position={"x": 50, "y": 30},
                size={"width": 620, "height": 50},
                font_size=24,
                bold=True,
                color=dark,
            )
        rows = slide_data.get("table_data", slide_data.get("bullets", []))
        if rows:
            if isinstance(rows[0], list):
                text = "\n".join([" | ".join(str(c) for c in row) for row in rows])
            else:
                text = "\n".join([f"• {self._sanitize_text(str(r))}" for r in rows])
            self._add_styled_text(
                presentation_id,
                slide_id,
                text,
                position={"x": 50, "y": 100},
                size={"width": 620, "height": 350},
                font_size=12,
                color=dark,
            )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Nettoie le texte avant envoi à l'API Google Slides.
        Supprime les caractères de contrôle qui causent des erreurs JSON."""
        import re

        if not text:
            return ""
        # Supprimer les caractères de contrôle (garder \n et \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text.strip()

    def export_markdown_to_docs(self, markdown_content: str, title: str) -> Optional[str]:
        """
        Exporte du contenu Markdown vers un Google Doc.

        Args:
            markdown_content: Contenu markdown à convertir
            title: Titre du document

        Returns:
            URL du document créé ou None en cas d'erreur
        """
        try:
            docs_service = build("docs", "v1", credentials=self.creds)
            drive_service = build("drive", "v3", credentials=self.creds)

            # Créer le document
            doc = docs_service.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]

            # Convertir le markdown en requêtes Google Docs
            requests = self._markdown_to_docs_requests(markdown_content)

            if requests:
                docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

            # Rendre le document partageable
            drive_service.permissions().create(
                fileId=doc_id, body={"type": "anyone", "role": "writer"}
            ).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            print(f"✅ Google Doc créé: {doc_url}")
            return doc_url

        except HttpError as error:
            print(f"❌ Erreur lors de l'export vers Google Docs: {error}")
            return None

    def _markdown_to_docs_requests(self, markdown: str) -> List[Dict]:
        """Convertit du markdown en requetes batchUpdate pour Google Docs.

        Gere: headings, bold, italic, inline code, blockquotes,
        listes a puces, listes numerotees, blocs de code, et
        ignore le front matter YAML.
        """
        import re as _re

        requests = []
        lines = markdown.split("\n")
        index = 1  # Position dans le document (commence a 1)

        # Skip YAML front matter (--- ... ---)
        start = 0
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    start = i + 1
                    break

        # Skip image placeholder block (> **[IMAGE PLACEHOLDER]**)
        in_code_block = False

        for line_num in range(start, len(lines)):
            line = lines[line_num]
            stripped = line.strip()

            # Handle code blocks (``` ... ```)
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    # Start of code block - insert a newline
                    text = "\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": text}})
                    index += len(text)
                continue

            if in_code_block:
                # Code block content - insert as-is with monospace
                text = line + "\n"
                requests.append({"insertText": {"location": {"index": index}, "text": text}})
                # Apply monospace font
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(text) - 1,
                            },
                            "textStyle": {
                                "weightedFontFamily": {"fontFamily": "Courier New"},
                                "backgroundColor": {
                                    "color": {
                                        "rgbColor": {
                                            "red": 0.95,
                                            "green": 0.95,
                                            "blue": 0.95,
                                        }
                                    }
                                },
                            },
                            "fields": "weightedFontFamily,backgroundColor",
                        }
                    }
                )
                index += len(text)
                continue

            # Skip image placeholder lines
            if stripped.startswith("> **[IMAGE"):
                continue
            if stripped.startswith("> **Prompt de generation"):
                continue
            if stripped.startswith("> **Dimensions"):
                continue
            if stripped.startswith("![]["):
                continue

            if not stripped:
                text = "\n"
                requests.append({"insertText": {"location": {"index": index}, "text": text}})
                index += len(text)
                continue

            # Determine line type
            heading_level = 0
            is_bullet = False
            is_numbered = False
            is_blockquote = False

            if stripped.startswith("### "):
                heading_level = 3
                clean = stripped[4:]
            elif stripped.startswith("## "):
                heading_level = 2
                clean = stripped[3:]
            elif stripped.startswith("# "):
                heading_level = 1
                clean = stripped[2:]
            elif stripped.startswith("- ") or stripped.startswith("* "):
                is_bullet = True
                clean = stripped[2:]
            elif _re.match(r"^\d+\.\s", stripped):
                is_numbered = True
                clean = _re.sub(r"^\d+\.\s", "", stripped)
            elif stripped.startswith("> "):
                is_blockquote = True
                clean = stripped[2:]
            else:
                clean = stripped

            # Extract inline formatting spans (bold, italic, code)
            # We'll insert plain text first, then apply formatting
            segments = self._parse_inline_formatting(clean)
            plain_text = "".join(s["text"] for s in segments) + "\n"

            requests.append({"insertText": {"location": {"index": index}, "text": plain_text}})

            # Apply inline formatting
            pos = index
            for seg in segments:
                seg_len = len(seg["text"])
                if seg_len == 0:
                    continue

                if seg.get("bold"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": pos,
                                    "endIndex": pos + seg_len,
                                },
                                "textStyle": {"bold": True},
                                "fields": "bold",
                            }
                        }
                    )
                if seg.get("italic"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": pos,
                                    "endIndex": pos + seg_len,
                                },
                                "textStyle": {"italic": True},
                                "fields": "italic",
                            }
                        }
                    )
                if seg.get("code"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": pos,
                                    "endIndex": pos + seg_len,
                                },
                                "textStyle": {
                                    "weightedFontFamily": {"fontFamily": "Courier New"},
                                    "backgroundColor": {
                                        "color": {
                                            "rgbColor": {
                                                "red": 0.93,
                                                "green": 0.93,
                                                "blue": 0.93,
                                            }
                                        }
                                    },
                                },
                                "fields": "weightedFontFamily,backgroundColor",
                            }
                        }
                    )
                pos += seg_len

            # Apply heading style
            if heading_level > 0:
                heading_map = {
                    1: "HEADING_1",
                    2: "HEADING_2",
                    3: "HEADING_3",
                }
                requests.append(
                    {
                        "updateParagraphStyle": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(plain_text),
                            },
                            "paragraphStyle": {"namedStyleType": heading_map[heading_level]},
                            "fields": "namedStyleType",
                        }
                    }
                )

            # Apply bullet list
            if is_bullet:
                requests.append(
                    {
                        "createParagraphBullets": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(plain_text),
                            },
                            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                        }
                    }
                )

            # Apply numbered list
            if is_numbered:
                requests.append(
                    {
                        "createParagraphBullets": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(plain_text),
                            },
                            "bulletPreset": "NUMBERED_DECIMAL_NESTED",
                        }
                    }
                )

            # Apply blockquote indent
            if is_blockquote:
                requests.append(
                    {
                        "updateParagraphStyle": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(plain_text),
                            },
                            "paragraphStyle": {
                                "indentFirstLine": {"magnitude": 36, "unit": "PT"},
                                "indentStart": {"magnitude": 36, "unit": "PT"},
                            },
                            "fields": "indentFirstLine,indentStart",
                        }
                    }
                )
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {
                                "startIndex": index,
                                "endIndex": index + len(plain_text) - 1,
                            },
                            "textStyle": {"italic": True},
                            "fields": "italic",
                        }
                    }
                )

            index += len(plain_text)

        return requests

    @staticmethod
    def _parse_inline_formatting(text: str) -> List[Dict]:
        """Parse inline markdown: **bold**, *italic*, `code`.

        Returns list of segments with text + formatting flags.
        """
        import re as _re

        segments = []
        # Pattern order matters: bold before italic
        pattern = _re.compile(
            r"(\*\*(.+?)\*\*)"  # bold
            r"|(\*(.+?)\*)"  # italic
            r"|(`(.+?)`)"  # inline code
        )
        last_end = 0

        for m in pattern.finditer(text):
            # Plain text before match
            if m.start() > last_end:
                segments.append({"text": text[last_end : m.start()]})

            if m.group(2):  # bold
                segments.append({"text": m.group(2), "bold": True})
            elif m.group(4):  # italic
                segments.append({"text": m.group(4), "italic": True})
            elif m.group(6):  # code
                segments.append({"text": m.group(6), "code": True})

            last_end = m.end()

        # Remaining text
        if last_end < len(text):
            segments.append({"text": text[last_end:]})

        return segments if segments else [{"text": text}]


def extract_notebooklm_content(notebook_url: str) -> str:
    """
    Note: NotebookLM n'a pas d'API publique pour le moment.
    Cette fonction est un placeholder pour une future implémentation.

    Pour l'instant, vous devrez exporter manuellement le contenu de NotebookLM.
    """
    print("⚠️  NotebookLM n'a pas d'API publique.")
    print("   Veuillez exporter le contenu manuellement depuis NotebookLM")
    print("   et le placer dans le dossier data/notebooklm/")
    return None
