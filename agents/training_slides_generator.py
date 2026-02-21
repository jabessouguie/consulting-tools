"""
Agent de génération de supports de formation (slides)
Prend en entrée un Programme de Formation et génère des slides
exportables en Google Slides, respectant la charte graphique Consulting Tools.
"""
import os
import sys
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient


class TrainingSlidesGeneratorAgent:
    """Agent qui génère des slides de formation à partir d'un programme de formation"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @staticmethod
    def _sanitize_json_string(text: str) -> str:
        """Nettoie le texte avant parsing JSON.
        Supprime les caractères de contrôle qui causent des erreurs JSON."""
        if not text:
            return ""
        # Supprimer les caractères de contrôle (garder \n et \t)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    def parse_programme(self, programme_md: str) -> Dict[str, Any]:
        """
        Parse un programme de formation markdown pour en extraire les modules et la structure.
        
        Returns:
            Dict avec title, duration, modules (chacun avec days, ateliers, objectifs)
        """
        print("📄 Parsing du programme de formation...")

        system_prompt = """Tu es un parser de programmes de formation. 
Analyse le document markdown et extrais la structure complète en JSON.
Retourne UNIQUEMENT un JSON valide, sans explication."""

        prompt = f"""Analyse ce programme de formation et extrais sa structure complète :

{programme_md}

Retourne un JSON avec ce format exact :
{{
    "title": "Titre de la formation",
    "code": "Code du cours",
    "duration": "Durée totale",
    "level": "100/200/300",
    "target_audience": "Public cible",
    "modules": [
        {{
            "name": "Nom du module",
            "duration": "Durée du module",
            "objectives": ["objectif 1", "objectif 2"],
            "days": [
                {{
                    "day_number": 1,
                    "title": "Titre du jour",
                    "topics": ["sujet 1", "sujet 2"],
                    "ateliers": ["atelier 1", "atelier 2"]
                }}
            ]
        }}
    ]
}}"""

        result = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )

        # Nettoyer et parser le JSON
        result = result.strip()
        if result.startswith('```json'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]

        # Sanitizer pour éviter les erreurs JSON
        result = self._sanitize_json_string(result)

        return json.loads(result)

    def generate_slides_for_module(
        self,
        programme_data: Dict,
        module_index: int,
        public_cible: str = "",
        duree: str = ""
    ) -> List[Dict]:
        """
        Génère les slides pour un module spécifique.
        
        Args:
            programme_data: Données du programme parsé
            module_index: Index du module à traiter
            public_cible: Public cible de la formation
            duree: Durée de la formation
            
        Returns:
            Liste de slides (dicts avec type, title, bullets, visual, etc.)
        """
        module = programme_data['modules'][module_index]
        title = programme_data.get('title', 'Formation')

        print(f"🎓 Génération des slides pour le module : {module['name']}...")

        system_prompt = """Tu es un designer de supports de formation chez Consulting Tools, expert en pédagogie visuelle.

CONSIGNES OBLIGATOIRES pour les slides (style Veolia - moderne et impactant) :
1. CHARTE GRAPHIQUE : Fond sombre (#1a1a2e), accents corail (#FF6B58), texte blanc
2. PAS TROP DE TEXTE : Maximum 5 bullet points par slide, phrases courtes
3. LOOK AND FEEL : Slides modernes, professionnelles, visuellement impactantes
4. VARIÉTÉ VISUELLE : Alterne les types de slides (content, diagram, stat, quote, highlight)
5. TRANSITIONS CLAIRES : Chaque transition entre sections est marquée par une slide de séparation
6. MESSAGES CLAIRS : Un message clé par slide, facile à retenir
7. IMPACT VISUEL : Utilise "stat" pour chiffres clés, "quote" pour citations/principes, "highlight" pour points clés
8. PUBLIC CIBLE : Adapte le vocabulaire et la profondeur au niveau du public
9. DURÉE : Calibre le nombre de slides pour la durée prévue (environ 2-3 slides par 10 min)

TYPES DE SLIDES DISPONIBLES :

**Slides de contenu** :
- "content": slide classique avec titre + bullets (max 5 points courts)
- "stat": chiffre clé en très grand (stat_value, stat_label, context, subtitle)
- "quote": citation/principe pédagogique (quote_text, author optional, title optional)
- "highlight": 2-4 points clés dans encadrés colorés (title, key_points)
- "two_column": comparaison 2 colonnes (title, left_title, left_points, right_title, right_points)
- "table": tableau de données (title, headers, rows)

**Slides visuelles** :
- "image": slide avec image (title, caption, bullets, image_prompt, image_dimensions)
  * image_prompt: Prompt detaille pour Nano Banana
  * image_dimensions: "1792x1024px (16:9)" par defaut
  * Exemple prompt: "Premium professional illustration for training, topic: [sujet], style: modern minimal, Unreal Engine 5 render, colors: cool blues + warm amber accents, 16:9 format, 1792x1024px"

**Diagrammes** (type "diagram" + diagram_type):
- "flow": processus lineaire avec fleches (elements: ["Etape 1", "Etape 2", ...])
- "grid": grille 2x2 ou plus (elements: ["Case 1", "Case 2", ...])
- "hierarchy": hierarchie/organigramme (elements: ["Root", "Child 1", "Child 2", ...])
- "process": processus numerote vertical (elements: ["Action 1", "Action 2", ...])
- "relations": schema relationnel en etoile (elements: ["Centre", "Satellite 1", "Satellite 2", ...])
- "cycle": cycle iteratif (elements: ["Phase 1", "Phase 2", ...])
- "timeline": chronologie horizontale (elements: ["2020", "2022", "2025", ...])
- "pyramid": pyramide (elements: ["Base", "Milieu", "Sommet"])

**Slides de structure** :
- "section": separateur de module (title, number optional)
- "cover": slide de couverture (title, subtitle, meta)
- "closing": slide de fin (title, subtitle)

Tu dois retourner UNIQUEMENT un JSON valide avec un tableau de slides."""

        prompt = f"""Génère les slides de formation pour ce module :

Formation : {title}
Module : {module['name']}
Public cible : {public_cible or programme_data.get('target_audience', 'Professionnels')}
Durée du module : {module.get('duration', duree or 'N/A')}
Niveau : {programme_data.get('level', '100')}

Objectifs du module :
{json.dumps(module.get('objectives', []), ensure_ascii=False)}

Contenu par jour :
{json.dumps(module.get('days', []), ensure_ascii=False, indent=2)}

Retourne un JSON avec ce format exact (VARIE LES TYPES) :
[
    {{
        "type": "section",
        "title": "Nom du module"
    }},
    {{
        "type": "stat",
        "stat_value": "87%",
        "stat_label": "de projets IA échouent",
        "context": "Source : Gartner 2025",
        "subtitle": "Le défi de l'IA en entreprise"
    }},
    {{
        "type": "highlight",
        "title": "3 piliers de l'IA responsable",
        "key_points": ["Transparence des algorithmes", "Protection des données", "Équité et non-discrimination"],
        "highlight_color": "corail"
    }},
    {{
        "type": "quote",
        "quote_text": "Les données sont le nouveau pétrole, mais comme le pétrole, elles doivent être raffinées pour créer de la valeur",
        "author": "Clive Humby",
        "title": "Principe fondamental"
    }},
    {{
        "type": "diagram",
        "title": "Cycle de vie d'un modèle ML",
        "diagram_type": "cycle",
        "elements": ["Collecte données", "Entraînement", "Déploiement", "Monitoring"],
        "description": "Processus itératif"
    }},
    {{
        "type": "diagram",
        "title": "Organisation équipe Data",
        "diagram_type": "hierarchy",
        "elements": ["CDO", "Data Engineers", "Data Scientists", "Data Analysts"],
        "description": "Structure hiérarchique"
    }},
    {{
        "type": "image",
        "title": "Architecture Big Data",
        "caption": "Exemple d architecture moderne",
        "bullets": ["Scalabilité", "Résilience", "Performance"],
        "image_prompt": "Premium professional diagram of modern big data architecture, distributed systems, clean minimal design, Unreal Engine 5 render, tech blueprint style, cool blue and amber accents, 16:9 format, 1792x1024px",
        "image_dimensions": "1792x1024px (16:9)"
    }},
    {{
        "type": "table",
        "title": "Comparaison des frameworks ML",
        "headers": ["Framework", "Performance", "Facilité", "Communauté"],
        "rows": [
            ["TensorFlow", "⭐⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐⭐"],
            ["PyTorch", "⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
            ["Scikit-learn", "⭐⭐⭐", "⭐⭐⭐⭐⭐", "⭐⭐⭐⭐"]
        ]
    }},
    {{
        "type": "content",
        "title": "Bonnes pratiques MLOps",
        "bullets": ["Versioning des modèles", "Tests automatisés", "Monitoring continu"],
        "speaker_notes": "Insister sur l'importance du versioning"
    }}
]

RAPPELS :
- VARIE les types de slides (stat, quote, highlight, diagram, content)
- Maximum 5 bullets par slide de type "content", phrases COURTES
- Commence par une slide de type "section" avec le nom du module
- Utilise "stat" pour chiffres impactants, "quote" pour principes, "highlight" pour takeaways
- Termine par un récap / quiz du module
- Inclus des slides pour chaque atelier pratique"""

        result = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )

        # Nettoyer et parser
        result = result.strip()
        if result.startswith('```json'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]

        # Sanitizer pour éviter les erreurs JSON
        result = self._sanitize_json_string(result)

        slides = json.loads(result)
        print(f"✅ {len(slides)} slides générées pour le module '{module['name']}'")
        return slides

    def generate_all_slides(self, programme_md: str) -> Dict[str, Any]:
        """
        Génère toutes les slides pour l'ensemble du programme.
        
        Returns:
            Dict avec modules_slides (slides par module), all_slides (toutes les slides concaténées)
        """
        print("🎓 Génération complète du support de formation...")

        # Parser le programme
        programme_data = self.parse_programme(programme_md)

        all_slides = []
        modules_slides = {}

        # Cover slide
        cover = {
            "type": "cover",
            "title": programme_data.get('title', 'Formation'),
            "bullets": [
                programme_data.get('duration', ''),
                programme_data.get('target_audience', ''),
                f"Niveau {programme_data.get('level', '100')}"
            ]
        }
        all_slides.append(cover)

        # Générer les slides pour chaque module
        for i, module in enumerate(programme_data.get('modules', [])):
            module_slides = self.generate_slides_for_module(
                programme_data, i,
                public_cible=programme_data.get('target_audience', ''),
                duree=programme_data.get('duration', '')
            )
            modules_slides[module['name']] = module_slides
            all_slides.extend(module_slides)

        # Closing slide
        closing = {
            "type": "closing",
            "title": "Merci !",
            "bullets": [
                "Questions & échanges",
                "Prochaines étapes",
                f"Contact : {os.getenv('CONSULTANT_NAME', 'Consulting Tools')}"
            ]
        }
        all_slides.append(closing)

        print(f"✅ Total : {len(all_slides)} slides générées pour {len(modules_slides)} modules")

        return {
            "programme_data": programme_data,
            "modules_slides": modules_slides,
            "all_slides": all_slides,
            "total_slides": len(all_slides),
            "generated_at": datetime.now().isoformat()
        }

    def generate_module_pptx(self, slides: List[Dict], module_name: str) -> str:
        """Génère un fichier PPTX pour un module spécifique"""
        from utils.pptx_generator import build_proposal_pptx

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = module_name.replace(" ", "_").replace("/", "-")[:50]
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"formation_{safe_name}_{timestamp}.pptx"

        template_path = self.base_dir / "Consulting Tools_Template_Palette 2026.pptx"

        build_proposal_pptx(
            template_path=str(template_path),
            slides_data=slides,
            output_path=str(output_path),
            consultant_info={
                "name": os.getenv("CONSULTANT_NAME", "Consulting Tools"),
                "company": os.getenv("COMPANY_NAME", "Consulting Tools"),
            },
        )

        return str(output_path.relative_to(self.base_dir))


if __name__ == "__main__":
    agent = TrainingSlidesGeneratorAgent()
    test_programme = """# **Introduction à l'IA Générative**
## WV-AI-100
Durée du cours : 2 jours (14 heures)

# Description
Formation d'introduction à l'IA générative pour les professionnels.

# Niveau
100

# Programme
## Module 1 : Fondamentaux de l'IA
### Jour 1
- Introduction à l'IA
- Machine Learning vs Deep Learning
#### Atelier : Premiers pas avec un LLM
"""
    result = agent.generate_all_slides(test_programme)
    print(f"Slides générées : {result['total_slides']}")
