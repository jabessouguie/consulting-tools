"""
Utilitaires pour interagir avec les API Google (Drive, Docs, Slides, NotebookLM)
"""
import os
from typing import Optional, Dict, List, Any
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import json


SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Créer et modifier des fichiers
    'https://www.googleapis.com/auth/presentations',  # Créer et modifier des présentations
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/gmail.send',  # Envoyer des emails
]


class GoogleAPIClient:
    """Client pour interagir avec les API Google"""

    def __init__(self, credentials_path: str = None):
        """
        Initialise le client Google API

        Args:
            credentials_path: Chemin vers le fichier credentials.json
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Authentifie l'utilisateur avec Google OAuth"""
        token_path = 'config/token.pickle'

        # Charger les credentials existantes
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)

        # Si pas de credentials valides, demander l'authentification
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Sauvegarder les credentials
            with open(token_path, 'wb') as token:
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
            service = build('slides', 'v1', credentials=self.creds)
            presentation = service.presentations().get(
                presentationId=presentation_id
            ).execute()

            slides_content = []
            for i, slide in enumerate(presentation.get('slides', [])):
                slide_data = {
                    'slide_number': i + 1,
                    'object_id': slide.get('objectId'),
                    'elements': []
                }

                # Extraire le texte de chaque élément
                for element in slide.get('pageElements', []):
                    if 'shape' in element:
                        shape = element['shape']
                        if 'text' in shape:
                            text_content = self._extract_text_from_shape(shape)
                            if text_content:
                                slide_data['elements'].append({
                                    'type': 'text',
                                    'content': text_content
                                })

                slides_content.append(slide_data)

            return {
                'title': presentation.get('title'),
                'slides': slides_content,
                'total_slides': len(slides_content)
            }

        except HttpError as error:
            print(f"Erreur lors de la récupération des slides: {error}")
            return None

    def _extract_text_from_shape(self, shape: Dict) -> str:
        """Extrait le texte d'un shape"""
        text_elements = []
        text_content = shape.get('text', {})

        for element in text_content.get('textElements', []):
            if 'textRun' in element:
                text_elements.append(element['textRun'].get('content', ''))

        return ''.join(text_elements).strip()

    def get_document_content(self, document_id: str) -> str:
        """
        Récupère le contenu d'un document Google Docs

        Args:
            document_id: ID du document

        Returns:
            Contenu texte du document
        """
        try:
            service = build('docs', 'v1', credentials=self.creds)
            document = service.documents().get(documentId=document_id).execute()

            content = []
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for text_element in element['paragraph'].get('elements', []):
                        if 'textRun' in text_element:
                            content.append(text_element['textRun'].get('content', ''))

            return ''.join(content)

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
            service = build('drive', 'v3', credentials=self.creds)

            # Récupérer les métadonnées
            file = service.files().get(fileId=file_id).execute()
            mime_type = file.get('mimeType')

            # Selon le type, utiliser la bonne méthode
            if 'presentation' in mime_type:
                return self.get_slides_content(file_id)
            elif 'document' in mime_type:
                return self.get_document_content(file_id)
            else:
                # Export en texte brut
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                return content.decode('utf-8')

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
            service = build('drive', 'v3', credentials=self.creds)

            results = service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()

            return results.get('files', [])

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
            service = build('slides', 'v1', credentials=self.creds)

            presentation = {
                'title': title
            }

            response = service.presentations().create(body=presentation).execute()
            presentation_id = response.get('presentationId')

            print(f"✅ Présentation créée: {presentation_id}")
            return presentation_id

        except HttpError as error:
            print(f"❌ Erreur lors de la création de la présentation: {error}")
            return None

    def add_slide(self, presentation_id: str, layout: str = 'BLANK') -> Optional[str]:
        """
        Ajoute une nouvelle slide à une présentation

        Args:
            presentation_id: ID de la présentation
            layout: Type de layout ('BLANK', 'TITLE', 'TITLE_AND_BODY', etc.)

        Returns:
            ID de la slide créée ou None en cas d'erreur
        """
        try:
            service = build('slides', 'v1', credentials=self.creds)

            requests = [{
                'createSlide': {
                    'slideLayoutReference': {
                        'predefinedLayout': layout
                    }
                }
            }]

            response = service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

            slide_id = response.get('replies')[0]['createSlide']['objectId']
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
        bold: bool = False
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
            service = build('slides', 'v1', credentials=self.creds)

            # Sanitize le texte avant insertion
            sanitized_text = self._sanitize_text(text)

            # Créer une text box
            element_id = f'textbox_{slide_id}_{position["x"]}_{position["y"]}'

            requests = [
                {
                    'createShape': {
                        'objectId': element_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': size['width'], 'unit': 'PT'},
                                'height': {'magnitude': size['height'], 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': position['x'],
                                'translateY': position['y'],
                                'unit': 'PT'
                            }
                        }
                    }
                },
                {
                    'insertText': {
                        'objectId': element_id,
                        'text': sanitized_text
                    }
                }
            ]

            # Ajouter le formatage si nécessaire
            if font_size != 14 or bold:
                requests.append({
                    'updateTextStyle': {
                        'objectId': element_id,
                        'style': {
                            'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                            'bold': bold
                        },
                        'fields': 'fontSize,bold'
                    }
                })

            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
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

            service = build('slides', 'v1', credentials=self.creds)

            # Supprimer la slide par défaut
            presentation = service.presentations().get(
                presentationId=presentation_id
            ).execute()

            default_slide_id = presentation['slides'][0]['objectId']

            requests = [{
                'deleteObject': {
                    'objectId': default_slide_id
                }
            }]

            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

            # Ajouter chaque slide
            for slide_data in slides_data:
                slide_type = slide_data.get('type', 'content')

                if slide_type == 'cover':
                    self._add_cover_slide(presentation_id, slide_data)
                elif slide_type == 'section':
                    self._add_section_slide(presentation_id, slide_data)
                elif slide_type in ['content', 'context', 'approach']:
                    self._add_content_slide(presentation_id, slide_data)
                elif slide_type == 'diagram':
                    self._add_diagram_slide(presentation_id, slide_data)

            # Générer le lien partageable
            drive_service = build('drive', 'v3', credentials=self.creds)
            drive_service.permissions().create(
                fileId=presentation_id,
                body={'type': 'anyone', 'role': 'writer'}
            ).execute()

            presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
            print(f"✅ Présentation Google Slides créée: {presentation_url}")

            return presentation_id

        except HttpError as error:
            print(f"❌ Erreur lors de l'export vers Google Slides: {error}")
            return None

    def _add_cover_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de couverture"""
        slide_id = self.add_slide(presentation_id, 'TITLE')

        # Ajouter le titre et sous-titre via batchUpdate
        service = build('slides', 'v1', credentials=self.creds)

        requests = []

        # Récupérer la slide pour obtenir les IDs des placeholders
        presentation = service.presentations().get(
            presentationId=presentation_id
        ).execute()

        current_slide = None
        for slide in presentation['slides']:
            if slide['objectId'] == slide_id:
                current_slide = slide
                break

        if current_slide:
            for element in current_slide.get('pageElements', []):
                if 'shape' in element:
                    shape = element['shape']
                    shape_type = shape.get('shapeType')

                    # Trouver le placeholder de titre
                    if shape_type == 'TEXT_BOX' or 'placeholder' in shape:
                        object_id = element['objectId']

                        # Insérer le titre ou sous-titre
                        if slide_data.get('title'):
                            requests.append({
                                'insertText': {
                                    'objectId': object_id,
                                    'text': self._sanitize_text(slide_data['title'])
                                }
                            })
                        break

        if requests:
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

    def _add_section_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de section"""
        slide_id = self.add_slide(presentation_id, 'SECTION_HEADER')

        if slide_data.get('title'):
            self.add_text_to_slide(
                presentation_id, slide_id,
                slide_data['title'],
                position={'x': 50, 'y': 200},
                size={'width': 600, 'height': 100},
                font_size=36,
                bold=True
            )

    def _add_content_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide de contenu"""
        slide_id = self.add_slide(presentation_id, 'TITLE_AND_BODY')

        # Titre
        if slide_data.get('title'):
            self.add_text_to_slide(
                presentation_id, slide_id,
                slide_data['title'],
                position={'x': 50, 'y': 50},
                size={'width': 600, 'height': 60},
                font_size=28,
                bold=True
            )

        # Bullets
        if slide_data.get('bullets'):
            clean_bullets = [self._sanitize_text(b) for b in slide_data['bullets']]
            bullets_text = '\n'.join([f'• {bullet}' for bullet in clean_bullets])
            self.add_text_to_slide(
                presentation_id, slide_id,
                bullets_text,
                position={'x': 50, 'y': 150},
                size={'width': 600, 'height': 350},
                font_size=14
            )

    def _add_diagram_slide(self, presentation_id: str, slide_data: Dict):
        """Ajoute une slide avec diagramme (version simplifiée)"""
        slide_id = self.add_slide(presentation_id, 'TITLE_AND_BODY')

        # Titre
        if slide_data.get('title'):
            self.add_text_to_slide(
                presentation_id, slide_id,
                self._sanitize_text(slide_data['title']),
                position={'x': 50, 'y': 50},
                size={'width': 600, 'height': 60},
                font_size=28,
                bold=True
            )

        # Éléments du diagramme (version texte pour l'instant)
        if slide_data.get('elements'):
            elements_text = '\n'.join([f'{i+1}. {self._sanitize_text(elem)}' for i, elem in enumerate(slide_data['elements'])])
            self.add_text_to_slide(
                presentation_id, slide_id,
                elements_text,
                position={'x': 100, 'y': 150},
                size={'width': 500, 'height': 350},
                font_size=16
            )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Nettoie le texte avant envoi à l'API Google Slides.
        Supprime les caractères de contrôle qui causent des erreurs JSON."""
        import re
        if not text:
            return ""
        # Supprimer les caractères de contrôle (garder \n et \t)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
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
            docs_service = build('docs', 'v1', credentials=self.creds)
            drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Créer le document
            doc = docs_service.documents().create(body={'title': title}).execute()
            doc_id = doc['documentId']
            
            # Convertir le markdown en requêtes Google Docs
            requests = self._markdown_to_docs_requests(markdown_content)
            
            if requests:
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
            
            # Rendre le document partageable
            drive_service.permissions().create(
                fileId=doc_id,
                body={'type': 'anyone', 'role': 'writer'}
            ).execute()
            
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            print(f"✅ Google Doc créé: {doc_url}")
            return doc_url
            
        except HttpError as error:
            print(f"❌ Erreur lors de l'export vers Google Docs: {error}")
            return None

    def _markdown_to_docs_requests(self, markdown: str) -> List[Dict]:
        """Convertit du markdown basique en requêtes batchUpdate pour Google Docs."""
        requests = []
        lines = markdown.split('\n')
        index = 1  # Position dans le document (commence à 1)
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Ligne vide
                text = '\n'
                requests.append({
                    'insertText': {'location': {'index': index}, 'text': text}
                })
                index += len(text)
                continue
            
            # Déterminer le type de ligne
            heading_level = 0
            if stripped.startswith('### '):
                heading_level = 3
                text = stripped[4:] + '\n'
            elif stripped.startswith('## '):
                heading_level = 2
                text = stripped[3:] + '\n'
            elif stripped.startswith('# '):
                heading_level = 1
                text = stripped[2:] + '\n'
            elif stripped.startswith('- ') or stripped.startswith('* '):
                text = stripped[2:] + '\n'
            else:
                text = stripped + '\n'
            
            # Insérer le texte
            requests.append({
                'insertText': {'location': {'index': index}, 'text': text}
            })
            
            # Appliquer le style de heading si applicable
            if heading_level > 0:
                heading_map = {1: 'HEADING_1', 2: 'HEADING_2', 3: 'HEADING_3'}
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': index, 'endIndex': index + len(text)},
                        'paragraphStyle': {'namedStyleType': heading_map[heading_level]},
                        'fields': 'namedStyleType'
                    }
                })
            
            # Appliquer le style de liste si applicable
            if stripped.startswith('- ') or stripped.startswith('* '):
                requests.append({
                    'createParagraphBullets': {
                        'range': {'startIndex': index, 'endIndex': index + len(text)},
                        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                    }
                })
            
            index += len(text)
        
        return requests


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
