"""
Generateur d'images et diagrammes pour les propositions commerciales
- Diagrammes Mermaid via Claude (architecture, flux, sequences)
- Images DALL-E (optionnel, pour illustrations)
"""
import os
import requests
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime


class DiagramGenerator:
    """Generateur de diagrammes via Claude + Mermaid"""

    def __init__(self, llm_client=None):
        """
        Initialise le generateur de diagrammes

        Args:
            llm_client: Client LLM Claude (optionnel, cree automatiquement si absent)
        """
        if llm_client is None:
            from utils.llm_client import LLMClient
            self.llm_client = LLMClient()
        else:
            self.llm_client = llm_client

        self.output_dir = Path(__file__).parent.parent / "data" / "images" / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_mermaid_code(
        self,
        diagram_type: str,
        description: str,
        elements: List[str],
        context: Dict[str, Any]
    ) -> str:
        """
        Genere du code Mermaid via Claude

        Args:
            diagram_type: Type de diagramme ('architecture', 'flow', 'sequence', 'class')
            description: Description du diagramme a generer
            elements: Liste des elements/composants
            context: Contexte (client, projet)

        Returns:
            Code Mermaid genere
        """
        elements_str = "\n".join([f"- {el}" for el in elements])

        prompt = f"""Genere un diagramme Mermaid pour visualiser cette architecture/infrastructure:

Description: {description}
Client: {context.get('client_name', 'Client')}
Projet: {context.get('project_title', 'Projet')}

Composants/Elements:
{elements_str}

Type de diagramme: {diagram_type}

Genere le code Mermaid UNIQUEMENT (sans balises markdown, juste le code).

Pour une architecture, utilise un diagramme 'graph LR' ou 'graph TD' avec:
- Des noeuds representant les composants
- Des fleches montrant les flux de donnees
- Des sous-graphes pour regrouper les elements
- Un style clair et professionnel

Exemple de format:
graph TD
    A[Composant 1] --> B[Composant 2]
    B --> C[Composant 3]

Genere un diagramme similaire adapte aux elements fournis."""

        response = self.llm_client.generate(
            prompt=prompt,
            temperature=0.4,
            max_tokens=1500
        )

        # Nettoyer la reponse
        code = response.strip()
        # Retirer les balises markdown si presentes
        if code.startswith('```mermaid'):
            code = code[10:]
        elif code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]

        return code.strip()

    def mermaid_to_png(self, mermaid_code: str, output_path: str) -> bool:
        """
        Convertit du code Mermaid en image PNG via mmdc CLI

        Args:
            mermaid_code: Code Mermaid
            output_path: Chemin de sortie PNG

        Returns:
            True si succès, False sinon
        """
        try:
            # Verifier si mmdc est installe
            result = subprocess.run(
                ['which', 'mmdc'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print("   mermaid-cli (mmdc) non installe. Installation: npm install -g @mermaid-js/mermaid-cli")
                return False

            # Sauvegarder le code Mermaid dans un fichier temporaire
            temp_mmd = output_path.replace('.png', '.mmd')
            with open(temp_mmd, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)

            # Convertir en PNG
            result = subprocess.run(
                ['mmdc', '-i', temp_mmd, '-o', output_path, '-b', 'transparent'],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Supprimer le fichier temporaire
            if os.path.exists(temp_mmd):
                os.remove(temp_mmd)

            if result.returncode == 0:
                return True
            else:
                print(f"   Erreur mmdc: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("   Timeout lors de la generation du diagramme")
            return False
        except Exception as e:
            print(f"   Erreur conversion Mermaid: {e}")
            return False

    def generate_architecture_diagram(
        self,
        components: List[str],
        context: Dict[str, Any],
        description: str = "Architecture technique de la solution"
    ) -> Optional[str]:
        """
        Genere un diagramme d'architecture via Mermaid

        Args:
            components: Liste des composants de l'architecture
            context: Contexte (client, projet)
            description: Description du diagramme

        Returns:
            Chemin vers l'image generee ou None
        """
        print(f"   Generation diagramme architecture (Mermaid): {len(components)} composants")

        # Generer le code Mermaid via Claude
        mermaid_code = self.generate_mermaid_code(
            diagram_type='architecture',
            description=description,
            elements=components,
            context=context
        )

        # Sauvegarder et convertir en PNG
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"arch_{timestamp}.png"
        output_path = str(self.output_dir / filename)

        if self.mermaid_to_png(mermaid_code, output_path):
            print(f"   Diagramme genere: {output_path}")
            return output_path
        else:
            print("   Echec generation diagramme, utilisation du format PowerPoint natif")
            return None

    def generate_flow_diagram(
        self,
        steps: List[str],
        context: Dict[str, Any],
        description: str = "Processus et flux de travail"
    ) -> Optional[str]:
        """
        Genere un diagramme de flux via Mermaid

        Args:
            steps: Liste des etapes du processus
            context: Contexte (client, projet)
            description: Description du diagramme

        Returns:
            Chemin vers l'image generee ou None
        """
        print(f"   Generation diagramme flux (Mermaid): {len(steps)} etapes")

        mermaid_code = self.generate_mermaid_code(
            diagram_type='flow',
            description=description,
            elements=steps,
            context=context
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flow_{timestamp}.png"
        output_path = str(self.output_dir / filename)

        if self.mermaid_to_png(mermaid_code, output_path):
            print(f"   Diagramme genere: {output_path}")
            return output_path
        else:
            return None

    def generate_sequence_diagram(
        self,
        actors: List[str],
        context: Dict[str, Any],
        description: str = "Diagramme de sequence"
    ) -> Optional[str]:
        """
        Genere un diagramme de sequence via Mermaid

        Args:
            actors: Liste des acteurs/systemes
            context: Contexte (client, projet)
            description: Description du diagramme

        Returns:
            Chemin vers l'image generee ou None
        """
        print(f"   Generation diagramme sequence (Mermaid): {len(actors)} acteurs")

        mermaid_code = self.generate_mermaid_code(
            diagram_type='sequence',
            description=description,
            elements=actors,
            context=context
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sequence_{timestamp}.png"
        output_path = str(self.output_dir / filename)

        if self.mermaid_to_png(mermaid_code, output_path):
            print(f"   Diagramme genere: {output_path}")
            return output_path
        else:
            return None


class ImageGenerator:
    """Generateur d'images via OpenAI DALL-E (optionnel)"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le generateur d'images

        Args:
            api_key: Cle API OpenAI (optionnelle, utilise OPENAI_API_KEY env var par defaut)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/images/generations"
        self.output_dir = Path(__file__).parent.parent / "data" / "images" / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_diagram_image(
        self,
        description: str,
        context: Dict[str, Any],
        style: str = "professional"
    ) -> Optional[str]:
        """
        Genere une image de diagramme via DALL-E

        Args:
            description: Description du diagramme a generer
            context: Contexte de la proposition (client, projet, etc.)
            style: Style de l'image ('professional', 'modern', 'minimalist')

        Returns:
            Chemin vers l'image generee ou None en cas d'erreur
        """
        if not self.api_key:
            print("   DALL-E non configure: OPENAI_API_KEY manquante")
            return None

        # Construire le prompt pour DALL-E
        style_prompts = {
            'professional': 'professional business diagram, clean corporate style, simple and clear',
            'modern': 'modern tech diagram, gradient colors, sleek design',
            'minimalist': 'minimalist diagram, black and white, simple lines'
        }

        style_desc = style_prompts.get(style, style_prompts['professional'])

        client_name = context.get('client_name', 'client')
        project_title = context.get('project_title', 'project')

        prompt = f"""{style_desc}, {description},
for {client_name} - {project_title},
no text labels, icon-based, suitable for business presentation,
high quality, 16:9 aspect ratio"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "dall-e-3",
                "prompt": prompt[:1000],  # DALL-E limite
                "n": 1,
                "size": "1792x1024",  # Format paysage
                "quality": "standard",
                "style": "natural"
            }

            print(f"   Generation image DALL-E: {description[:50]}...")
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']

                # Telecharger l'image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"diagram_{timestamp}.png"
                filepath = self.output_dir / filename

                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    print(f"   Image generee: {filepath}")
                    return str(filepath)
            else:
                print(f"   Erreur DALL-E: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"   Erreur generation image: {e}")
            return None

    def generate_architecture_diagram(
        self,
        components: list,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Genere un diagramme d'architecture technique

        Args:
            components: Liste des composants de l'architecture
            context: Contexte de la proposition

        Returns:
            Chemin vers l'image generee
        """
        components_str = ", ".join(components[:5])  # Max 5 composants
        description = f"technical architecture diagram showing {components_str} components interconnected"
        return self.generate_diagram_image(description, context, style='modern')

    def generate_process_flowchart(
        self,
        steps: list,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Genere un flowchart de processus

        Args:
            steps: Liste des etapes du processus
            context: Contexte de la proposition

        Returns:
            Chemin vers l'image generee
        """
        steps_str = " to ".join(steps[:4])  # Max 4 etapes
        description = f"process flowchart showing steps: {steps_str}"
        return self.generate_diagram_image(description, context, style='professional')

    def generate_data_visualization(
        self,
        viz_type: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Genere une visualisation de donnees

        Args:
            viz_type: Type de visualisation ('dashboard', 'chart', 'graph')
            context: Contexte de la proposition

        Returns:
            Chemin vers l'image generee
        """
        viz_descriptions = {
            'dashboard': 'modern analytics dashboard with charts and KPIs',
            'chart': 'business chart showing growth metrics',
            'graph': 'network graph showing data relationships'
        }

        description = viz_descriptions.get(viz_type, viz_descriptions['dashboard'])
        return self.generate_diagram_image(description, context, style='modern')


class ImageLibrary:
    """Gestionnaire de bibliotheque d'images reutilisables"""

    def __init__(self):
        """Initialise la bibliotheque d'images"""
        self.library_dir = Path(__file__).parent.parent / "data" / "images" / "library"
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_file = self.library_dir / "catalog.json"
        self._load_catalog()

    def _load_catalog(self):
        """Charge le catalogue d'images"""
        import json
        if self.catalog_file.exists():
            with open(self.catalog_file, 'r', encoding='utf-8') as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {
                'categories': {},
                'images': []
            }

    def _save_catalog(self):
        """Sauvegarde le catalogue d'images"""
        import json
        with open(self.catalog_file, 'w', encoding='utf-8') as f:
            json.dump(self.catalog, f, indent=2, ensure_ascii=False)

    def add_image(
        self,
        image_path: str,
        category: str,
        tags: list,
        description: str
    ) -> str:
        """
        Ajoute une image a la bibliotheque

        Args:
            image_path: Chemin vers l'image source
            category: Categorie de l'image
            tags: Tags pour recherche
            description: Description de l'image

        Returns:
            Chemin vers l'image dans la bibliotheque
        """
        import shutil
        from pathlib import Path

        source_path = Path(image_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Image non trouvee: {image_path}")

        # Copier dans la bibliotheque
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category}_{timestamp}{source_path.suffix}"
        dest_path = self.library_dir / filename

        shutil.copy2(source_path, dest_path)

        # Ajouter au catalogue
        self.catalog['images'].append({
            'filename': filename,
            'path': str(dest_path),
            'category': category,
            'tags': tags,
            'description': description,
            'added_at': timestamp
        })

        if category not in self.catalog['categories']:
            self.catalog['categories'][category] = []
        self.catalog['categories'][category].append(filename)

        self._save_catalog()
        print(f"   Image ajoutee a la bibliotheque: {filename}")
        return str(dest_path)

    def search_images(
        self,
        category: Optional[str] = None,
        tags: Optional[list] = None,
        keyword: Optional[str] = None
    ) -> list:
        """
        Recherche des images dans la bibliotheque

        Args:
            category: Filtrer par categorie
            tags: Filtrer par tags
            keyword: Recherche par mot-cle dans description

        Returns:
            Liste d'images correspondantes
        """
        results = self.catalog['images']

        if category:
            results = [img for img in results if img['category'] == category]

        if tags:
            results = [
                img for img in results
                if any(tag in img['tags'] for tag in tags)
            ]

        if keyword:
            keyword_lower = keyword.lower()
            results = [
                img for img in results
                if keyword_lower in img['description'].lower()
            ]

        return results

    def get_image_by_category(self, category: str) -> Optional[str]:
        """
        Recupere une image aleatoire d'une categorie

        Args:
            category: Categorie de l'image

        Returns:
            Chemin vers l'image ou None
        """
        images = self.search_images(category=category)
        if images:
            import random
            return images[random.randint(0, len(images) - 1)]['path']
        return None

    def list_categories(self) -> list:
        """
        Liste toutes les categories disponibles

        Returns:
            Liste des categories
        """
        return list(self.catalog['categories'].keys())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtient des statistiques sur la bibliotheque

        Returns:
            Dict avec statistiques
        """
        return {
            'total_images': len(self.catalog['images']),
            'categories': len(self.catalog['categories']),
            'by_category': {
                cat: len(imgs)
                for cat, imgs in self.catalog['categories'].items()
            }
        }


class NanoBananaGenerator:
    """Generateur d'images via Imagen 4 Fast avec SDK google-generativeai"""

    def __init__(self):
        try:
            import google.generativeai as genai

            # Configurer avec la cle API
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY non trouvee dans .env")

            genai.configure(api_key=api_key)
            self.genai = genai
            # Imagen 4 Fast - modele rapide et fiable pour generation d'images
            self.model_name = "models/imagen-4.0-fast-generate-001"
            print(f"  [NanoBanana] Initialise avec Imagen 4 Fast")

        except Exception as e:
            print(f"  [NanoBanana] Erreur initialisation: {e}")
            self.genai = None

    def generate_image(self, prompt: str, output_path: str) -> Optional[str]:
        """
        Genere une image a partir d'un prompt via Imagen 4 Fast

        Args:
            prompt: Description de l'image a generer
            output_path: Chemin de sortie pour l'image

        Returns:
            Chemin du fichier image genere, ou None si echec
        """
        if not self.genai:
            print("  [NanoBanana] API non initialisee")
            return None

        try:
            # Generer l'image avec Imagen 4 Fast via google-generativeai
            model = self.genai.GenerativeModel(self.model_name)

            # Configuration avec timeout etendu pour generation d'images
            request_options = {
                "timeout": 120.0  # 2 minutes timeout
            }

            response = model.generate_content(
                prompt,
                generation_config=self.genai.GenerationConfig(
                    temperature=1.0,
                ),
                request_options=request_options
            )

            # Extraire et sauvegarder l'image
            if response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)

                        # Ecrire les donnees de l'image
                        image_data = part.inline_data.data
                        with open(output_path, 'wb') as f:
                            f.write(image_data)

                        print(f"  [NanoBanana] Image generee: {output_path}")
                        return output_path

            print(f"  [NanoBanana] Aucune image dans la reponse")
            return None

        except Exception as e:
            print(f"  [NanoBanana] Erreur generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_article_illustration(self, article_text: str, output_path: str) -> Optional[str]:
        """
        Genere une illustration pour un article de blog avec le prompt Art Director

        Args:
            article_text: Texte de l'article
            output_path: Chemin de sortie

        Returns:
            Chemin du fichier image
        """
        prompt = f"""Role & Objective: You are an expert Art Director for a high-end tech consultancy firm.
Your task is to generate a premium, cinematic illustration based on the Blog Post provided below.

Analysis Instructions:
1. Read the blog post below.
2. Extract the core metaphor: Focus on the contrast between "AI speed/chaos" and "Human strategic guidance".
3. Ignore literal elements. Focus on the concept of "Orchestrating Intelligence".

Visual Style Guidelines:
* Aesthetic: Unreal Engine 5 render, isometric or wide-angle, 8k resolution.
* Mood: Sophisticated, futuristic but grounded, "Corporate Tech".
* Lighting: Dramatic contrast between cool electric blues (representing the AI data stream) and warm amber/gold (representing the human touch/value).
* Composition: A central human figure (silhouette or back view) controlling or structuring a massive, complex digital structure.

Input Text (The Blog Post):
{article_text[:3000]}

Action: Generate the illustration now based on this analysis."""

        return self.generate_image(prompt, output_path)


# Categories predefinies pour la bibliotheque
PREDEFINED_CATEGORIES = [
    'architecture',      # Diagrammes d'architecture
    'process',          # Flowcharts et processus
    'dashboard',        # Tableaux de bord
    'team',             # Photos d'equipe
    'technology',       # Logos et icones tech
    'data',             # Visualisations de donnees
    'success',          # Images de reussite/resultats
    'methodology',      # Schemas methodologiques
    'infrastructure',   # Schemas d'infrastructure
    'mockup'           # Mockups d'interfaces
]
