"""
Agent de génération de supports de formation (slides)
Prend en entrée un Programme de Formation et génère des slides
exportables en Google Slides, respectant la charte graphique Consulting Tools.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from utils.image_generator import NanoBananaGenerator
from utils.llm_client import LLMClient


class TrainingSlidesGeneratorAgent:
    """Agent qui génère des slides de formation à partir d'un programme de formation"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)
        self.nano_banana = NanoBananaGenerator()
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @staticmethod
    def _sanitize_json_string(text: str) -> str:
        """Nettoie le texte avant parsing JSON.
        Supprime les caractères de contrôle qui causent des erreurs JSON."""
        if not text:
            return ""
        # Supprimer les caractères de contrôle (garder \n et \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
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

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.3)

        # Nettoyer et parser le JSON
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        # Sanitizer pour éviter les erreurs JSON
        result = self._sanitize_json_string(result)

        return json.loads(result)

    def generate_slides_for_module(
        self, programme_data: Dict, module_index: int, public_cible: str = "", duree: str = ""
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
        module = programme_data["modules"][module_index]
        title = programme_data.get("title", "Formation")

        print(f"🎓 Génération des slides pour le module : {module['name']}...")

        system_prompt = """Tu es un designer de supports de formation chez Consulting Tools, expert en pédagogie visuelle.
Pour chaque slide du module, génère une infographie claire, didactique et très visuelle.

DIRECTIVE D'INFOGRAPHIE (À appliquer systématiquement) :
- OBJECTIF : Rendre l'apprenant intelligent en vulgarisant les concepts (comme l'Agent IA) pour un public "business".
- STYLE : Adopte un style minimaliste et percutant, inspiré de Seth Godin et des formations Wision (schémas clairs, une seule idée principale). Évite les listes à puces (bullet points) et le texte dense. Utilise un maximum de quatre éléments d'information clés pour faciliter l'assimilation.
- CONTENU : Transforme le point du programme fourni en concept visuel impactant.
- CONTRAINTE VISUELLE : Utilise des schémas simples, une analogie visuelle (comme l'utilisation de robots) ou des références à la pop culture pour créer de l'impact et susciter l'engagement du public.

CONSIGNES OBLIGATOIRES pour les slides (style moderne et impactant) :
1. CHARTE GRAPHIQUE : Fond sombre (#1a1a2e), accents corail (#FF6B58), texte blanc.
2. LOOK AND FEEL : Une infographie didactique par slide. Pas de texte dense.
3. VARIÉTÉ : Alterne les types (diagram, stat, quote, highlight, image).
4. MESSAGES : Un seul message clé par slide.
5. DURÉE : Environ 2-3 slides par 10 min.

TYPES DE SLIDES DISPONIBLES :
- "diagram" : L'infographie par excellence (diagram_type: flow, cycle, hierarchy, process, staircase, funnel, radar, grid).
- "stat" : Chiffre clé géant (stat_value, stat_label, context, subtitle).
- "quote" : Principe pédagogique percutant (quote_text, author).
- "highlight" : 2-4 points clés visuels (title, key_points).
- "two_column" : Comparaison visuelle (title, left_points, right_points).
- "image" : Illustration métaphorique (title, image_prompt).
- "section" : Titre de module/chapitre.
- "cover" : Couverture de la formation.

Tu dois retourner UNIQUEMENT un JSON valide avec un tableau de slides (uniques et originales)."""

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
        "title": "L'Agent IA : Votre nouveau collaborateur",
        "caption": "Un agent qui perçoit, raisonne et agit",
        "bullets": ["Perception", "Raisonnement", "Action"],
        "image_prompt": "Minimalist premium illustration of a sleek friendly robot holding a business briefcase, glowing blue brain core, clean white background, Seth Godin aesthetic, professional 3D render, tech-business style, 16:9 format",
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
        "type": "diagram",
        "title": "Adoption de l'IA : 3 étapes clés",
        "diagram_type": "process",
        "elements": ["Acculturation", "Cas d'usages", "Mise à l'échelle"],
        "description": "Feuille de route stratégique"
    }}
]

RAPPELS :
- PRIORITÉ : Chaque slide doit être une infographie claire et didactique.
- VARIE les types visuels (diagram, stat, quote, highlight, image).
- ÉVITE le texte dense : maximum 4 éléments clés, pas de phrases longues.
- ANALOGIES : Utilise des analogies visuelles (ex: Robots, Pop Culture) pour l'impact.
- STRUCTURE : Une idée principale par slide, ton minimaliste à la Seth Godin.
- Termine par un récap / quiz interactif pour chaque module.
- Inclus des slides pour chaque atelier pratique décrit dans le programme.
"""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Nettoyer et parser
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
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
            "title": programme_data.get("title", "Formation"),
            "bullets": [
                programme_data.get("duration", ""),
                programme_data.get("target_audience", ""),
                f"Niveau {programme_data.get('level', '100')}",
            ],
        }
        all_slides.append(cover)

        # Générer les slides pour chaque module
        for i, module in enumerate(programme_data.get("modules", [])):
            module_slides = self.generate_slides_for_module(
                programme_data,
                i,
                public_cible=programme_data.get("target_audience", ""),
                duree=programme_data.get("duration", ""),
            )
            modules_slides[module["name"]] = module_slides
            all_slides.extend(module_slides)

        # Closing slide
        closing = {
            "type": "closing",
            "title": "Merci !",
            "bullets": [
                "Questions & échanges",
                "Prochaines étapes",
                f"Contact : {os.getenv('CONSULTANT_NAME', 'Consulting Tools')}",
            ],
        }
        all_slides.append(closing)

        print(f"✅ Total : {len(all_slides)} slides générées pour {len(modules_slides)} modules")

        return {
            "programme_data": programme_data,
            "modules_slides": modules_slides,
            "all_slides": all_slides,
            "total_slides": len(all_slides),
            "generated_at": datetime.now().isoformat(),
        }

    def generate_premium_html_presentation(self, programme_md: str) -> Dict[str, Any]:
        """
        Génère une présentation HTML premium suivant le flux demandé par l'utilisateur:
        1. Déterminer le contenu via Gemini
        2. Créer la slide vide (titre HTML)
        3. Déterminer le contenu infographique détaillé
        4. Utiliser Nano Banana pour l'infographie
        5. Insérer dans le HTML
        """
        print("🚀 Génération de la présentation Premium HTML avec Nano Banana...")

        # 1. Parser le programme
        programme_data = self.parse_programme(programme_md)
        title = programme_data.get("title", "Formation")

        all_html_slides = []

        # Déterminer la liste des slides nécessaires
        print("📊 Détermination de la liste des slides...")
        slides_plan = self._get_slides_plan(programme_data)

        output_dir = (
            self.base_dir / "output" / f"premium_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        for i, slide_info in enumerate(slides_plan):
            print(f"🖼️ Génération de la slide {i+1}/{len(slides_plan)}: {slide_info['title']}")

            # 2. Créer la slide vide avec seulement le titre au format HTML
            slide_html = f"""
<section class="slide" data-id="{i}">
    <div class="slide-header">
        <h1>{slide_info['title']}</h1>
    </div>
    <div class="slide-content" id="content-{i}">
        <!-- Détails à venir -->
    </div>
</section>
"""
            # 3. Déterminer le prompt de l'infographie via Gemini
            content_details = self._determine_slide_content(slide_info, title)

            # 4. Utiliser Nano Banana pour créer l'infographie
            image_filename = f"slide_{i}.jpg"
            image_path = images_dir / image_filename

            infographic_image = self.nano_banana.generate_image(
                prompt=content_details["image_prompt"], output_path=str(image_path)
            )

            # 5. Insérer l'infographie dans la slide au format HTML
            relative_image_path = f"images/{image_filename}" if infographic_image else ""

            final_slide_html = self._assemble_final_slide(
                title=slide_info["title"],
                image_path=relative_image_path,
                slide_index=i,
            )

            all_html_slides.append(final_slide_html)

        # Assembler le document complet
        full_html = self._wrap_in_full_document(title, all_html_slides)

        html_path = output_dir / "index.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        print(f"✅ Présentation Premium générée: {html_path}")

        return {
            "html_path": str(html_path.relative_to(self.base_dir)),
            "total_slides": len(all_html_slides),
            "output_dir": str(output_dir),
        }

    def _get_slides_plan(self, programme_data: Dict) -> List[Dict]:
        """Détermine la liste des titres de slides à partir du programme"""
        prompt = f"""Basé sur ce programme de formation :
{json.dumps(programme_data, indent=2, ensure_ascii=False)}

Génère une liste de titres de slides cohérente.
Retourne UNIQUEMENT un JSON listant les titres :
[
    {{"title": "Introduction", "type": "intro"}},
    {{"title": "Module 1 : ...", "type": "section"}},
    ...
]"""
        result = self.llm.generate(prompt=prompt, system_prompt="Tu es un ingénieur pédagogique.")

        # Nettoyer et parser
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        return json.loads(self._sanitize_json_string(result))

    def _determine_slide_content(self, slide_info: Dict, formation_title: str) -> Dict:
        """Détermine le contenu détaillé et le prompt image pour une slide"""
        prompt = f"""Slide Title: {slide_info['title']} 
Formation: {formation_title}

Tu es un directeur artistique expert chez Consulting Tools. Ton rôle est de concevoir le prompt visuel pour une infographie pédagogique qui sera générée par Nano Banana Pro.

DIRECTIVE DE GÉNÉRATION D'IMAGE (Nano Banana Pro) :
"Génère une infographie très visuelle et didactique basée uniquement sur le contenu de la diapositive : {slide_info['title']}.

Assure-toi que l'infographie respecte le style de la formation Consulting Tools, en étant :
* Minimaliste et percutante, inspirée par Seth Godin (une image ou une idée par diapositive).
* Simple et facile à assimiler par le cerveau, en utilisant un maximum de quatre éléments visuels (schémas, icônes).
* Utilisant le style graphique et les couleurs de la présentation actuelle (Corail #FF6B58, Noir Profond #1F1F1F, Fond blanc)."

Retourne un JSON avec:
{{
    "image_prompt": "Le prompt technique détaillé et optimisé en ANGLAIS pour Nano Banana Pro (Gemini 3 Pro Image) afin d'obtenir ce résultat visuel."
}}"""
        result = self.llm.generate(
            prompt=prompt, system_prompt="Tu es un directeur artistique expert en pédagogie visuelle."
        )

        # Nettoyer et parser
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        return json.loads(self._sanitize_json_string(result))

    def _assemble_final_slide(self, title: str, image_path: str, slide_index: int) -> str:
        """Assemble les éléments dans le template HTML d'une slide"""
        image_html = (
            f'<div class="infographic"><img src="{image_path}" alt="Infographie"></div>'
            if image_path
            else '<div class="no-image">Génération de l\'infographie...</div>'
        )

        return f"""
<section class="slide" id="slide-{slide_index}">
    <div class="slide-header">
        <h1>{title}</h1>
    </div>
    <div class="slide-body-full">
        {image_html}
    </div>
</section>
"""

    def _wrap_in_full_document(self, title: str, slides_html: List[str]) -> str:
        """Enveloppe les slides dans un document HTML complet avec CSS Consulting Tools"""
        all_slides = "\n".join(slides_html)
        return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{title} - Consulting Tools</title>
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --dark: #1F1F1F;
            --coral: #FF6B58;
            --white: #FFFFFF;
            --rose: #FBF0F4;
        }}
        body {{
            background: #f0f0f0;
            margin: 0;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            color: var(--dark);
        }}
        .slide {{
            background: var(--white);
            width: 960px;
            height: 540px;
            margin: 0 auto 40px auto;
            border-top: 4px solid var(--coral);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            padding: 40px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-sizing: border-box;
            page-break-after: always;
        }}
        .slide-header h1 {{
            font-family: 'Chakra Petch', sans-serif;
            font-size: 2.2em;
            margin: 0 0 20px 0;
            color: var(--dark);
            text-align: center;
        }}
        .slide-body-full {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background: #fff;
            border-radius: 12px;
        }}
        .infographic {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .infographic img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
        }}
        .no-image {{
            color: #999;
            font-style: italic;
        }}
        @media print {{
            body {{ padding: 0; background: none; }}
            .slide {{ margin: 0; box-shadow: none; border-radius: 0; }}
        }}
    </style>
</head>
<body>
    {all_slides}
</body>
</html>
"""

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
    # Test de la nouvelle génération Premium HTML
    result = agent.generate_premium_html_presentation(test_programme)
    print(f"Présentation HTML générée : {result['html_path']}")
