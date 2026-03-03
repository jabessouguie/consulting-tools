"""
Agent de generation de presentations HTML premium
Utilise Gemini 3.1 Pro pour generer des slides HTML de qualite Canva,
en s'inspirant du design system extrait de slides_exemple/
Supporte tous les types : presentation, proposal, formation, rex
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from utils.llm_client import LLMClient


class HtmlSlideGeneratorAgent:
    """Agent qui genere des presentations HTML premium via Gemini 3.1 Pro"""

    _design_cache = None

    def __init__(self, model="gemini-3.1-pro-preview", provider="gemini"):
        self.llm = LLMClient(model=model, provider=provider, max_tokens=65536)
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.slides_exemple_path = self.base_dir / "slides_exemple" / "Module 4.pptx"

    def extract_design_system(self) -> Dict[str, Any]:
        """
        Analyse slides_exemple/ pour extraire le design system.
        Combine les constantes Wenvision avec le contexte du PPTX.
        Resultat cache en memoire apres le premier appel.
        """
        if HtmlSlideGeneratorAgent._design_cache is not None:
            return HtmlSlideGeneratorAgent._design_cache

        template_context = ""
        try:
            if self.slides_exemple_path.exists():
                from utils.pptx_reader import extract_template_structure

                template_context = extract_template_structure(str(self.slides_exemple_path))
        except Exception as e:
            print(f"  Avertissement: impossible de lire slides_exemple: {e}")

        result = {
            "colors": {
                "dark": "#1F1F1F",
                "gray": "#474747",
                "coral": "#FF6B58",
                "terracotta": "#C0504D",
                "white": "#FFFFFF",
                "rose_poudre": "#FBF0F4",
            },
            "fonts": {
                "title": "Chakra Petch",
                "body": "Inter",
            },
            "dimensions": {
                "width": 960,
                "height": 540,
                "ratio": "16:9",
            },
            "template_context": template_context,
        }
        HtmlSlideGeneratorAgent._design_cache = result
        return result

    def _build_system_instruction(self, design_system: Dict[str, Any]) -> str:
        """Construit le system_instruction commun a tous les types."""
        colors = design_system["colors"]
        fonts = design_system["fonts"]
        dims = design_system["dimensions"]

        return f"""Tu es un directeur artistique de renommee mondiale, expert en presentations premium et developpeur front-end d'elite. Tu crees des presentations HTML/CSS au niveau des meilleurs templates Canva/Pitch/Beautiful.ai.

=== IDENTITE VISUELLE WENVISION (reference absolue) ===

POLICES :
- Titres : '{fonts['title']}' (bold 600-700) - Impact tech, moderne
- Texte courant : '{fonts['body']}' (regular 400, semi-bold 500) - Lisibilite optimale
- Google Fonts via <link> : Chakra Petch (400;600;700) et Inter (300;400;500;600)

PALETTE COULEURS - REGLE 60-30-10 stricte :
- 60% DOMINANTE : Fond blanc ({colors['white']}) ou, pour les encadres/cartes uniquement, Rose Poudre ({colors['rose_poudre']})
- 30% SECONDAIRE : Textes en Noir Profond ({colors['dark']}) ou Gris Moyen ({colors['gray']})
- 10% ACCENT : Terracotta ({colors['terracotta']}) ou Corail ({colors['coral']}). Maximum 5 elements d'accent par slide (bordures, icones, barres, boutons, tags)

BRANDING WENVISION :
- Barre decorative corail de 4px en haut de chaque slide a fond blanc

DIMENSIONS : {dims['width']}px x {dims['height']}px (ratio {dims['ratio']})

=== ILLUSTRATIONS & VISUELS (OBLIGATOIRE) ===

Chaque presentation DOIT contenir au minimum 40% de slides visuelles. Techniques d'illustration CSS-only :

1. ICONES SVG INLINE : Pour chaque concept cle, insere une icone SVG inline (viewBox="0 0 24 24", taille 48-64px, stroke={colors['coral']}, fill="none", stroke-width=1.5). Exemples : fleche montante pour croissance, cerveau pour IA, nuage pour cloud, engrenage pour process, graphique pour data, fusee pour innovation, bouclier pour securite.

2. DIAGRAMMES CSS : Cree des diagrammes visuels avec des divs positionnes : flows horizontaux (fleches CSS entre boites), organigrammes, timelines verticales/horizontales, matrices 2x2, pyramides en CSS.

3. BARRES DE PROGRESSION / STATS : Pour les chiffres cles, utilise des barres de progression CSS (div avec width en %, background gradient corail), cercles de progression (border-radius 50%, conic-gradient), ou compteurs grands format (font-size 3em, color corail).

4. CARTES ILLUSTREES : Grilles de 2-3 cartes avec icone SVG + titre + description. Fond rose poudre ou blanc avec bordure gauche corail de 3px.

5. DECORATIONS GEOMETRIQUES : Cercles semi-transparents en position absolute (background: {colors['coral']}10), lignes diagonales decoratives, motifs de points en CSS.

=== REGLES DE GENERATION HTML ===

1. Chaque slide = <section class="slide" data-type="TYPE"> avec TYPE parmi : cover, section, content, stat, quote, highlight, diagram, two_column, table, cv, closing. Le data-type est OBLIGATOIRE.
2. Chaque slide fait {dims['width']}px x {dims['height']}px. Rendu premium.
3. Genere la balise <style> dans le <head> avec le design system complet en CSS variables (:root).
4. MISE EN PAGE AEREE : Max 5 bullet points par slide. Max 30 mots par bullet. Beaucoup de padding (40-60px). Texte long dans <div class="notes"> (display:none).
5. VARIETE OBLIGATOIRE des layouts : cover, bullets avec icones, stat impactant (chiffre geant), quote (blockquote stylise), 2 colonnes, highlights (cartes), diagrammes CSS, tableaux stylises. Ne JAMAIS enchainer 2 slides avec le meme layout.
6. COUVERTURE : fond sombre ({colors['dark']}), titre blanc en Chakra Petch bold, sous-titre en Inter light, barre corail decorative de 80px x 4px, formes geometriques decoratives en arriere-plan.
7. CLOTURE : meme style sombre que la couverture, "Merci" ou "Questions ?", coordonnees.
8. OMBRES & BORDURES : box-shadow subtils (0 2px 12px rgba(0,0,0,0.08)), border-radius 12px pour les cartes, bordure gauche corail sur les encadres importants.
9. Pas de JavaScript - uniquement HTML + CSS.
10. Body background gris clair (#f4f4f4), slides centrees, box-shadow elegant, margin 20px entre slides.
11. page-break-after: always pour l'impression.
12. Ne reponds QUE par du code HTML valide. Pas d'explication, pas de backticks markdown.
13. Utilise des balises semantiques : <h1>/<h2> pour titres, <ul><li> pour bullets, <blockquote> pour citations, <table> pour tableaux, <svg> pour icones."""

    def _build_user_prompt(
        self,
        topic: str,
        num_slides: int,
        gen_type: str = "presentation",
        audience: str = "",
        document_text: str = "",
        extra_context: str = "",
        language: str = "fr",
    ) -> str:
        """Construit le user_prompt adapte au type de generation."""
        lang_prefix = ""
        if language == "en":
            lang_prefix = "Generate all content in English. "

        doc_section = ""
        if document_text:
            doc_section = f"""

DOCUMENT SOURCE (a utiliser comme base) :
{document_text[:4000]}"""

        audience_section = ""
        if audience:
            audience_section = f"\nPUBLIC CIBLE : {audience}"

        extra_section = ""
        if extra_context:
            extra_section = f"\n{extra_context}"

        visual_rules = """
RAPPEL VISUEL OBLIGATOIRE :
- Chaque slide a fond blanc doit avoir une barre corail de 4px en haut.
- Alterne systematiquement les layouts : ne JAMAIS enchainer 2 slides avec le meme type de mise en page.
- Au moins 1 slide sur 3 doit contenir une illustration visuelle (icones SVG, diagramme CSS, barres de stats, grille de cartes illustrees).
- Les slides de type "stat" doivent utiliser des chiffres geants (font-size: 3em+) avec barres de progression CSS."""

        if gen_type == "proposal":
            structure = """
1. Slide de couverture (fond sombre, titre impactant, nom du client, formes decoratives)
2. Slide "Comprehension du besoin" (reformulation contexte, icones SVG par enjeu)
3. Slide "Notre approche" (methodologie en 3-4 cartes illustrees avec icones)
4. Slide "Demarche projet" (diagramme CSS en 4-5 phases avec fleches)
5. Slide "Roadmap" (timeline horizontale CSS avec jalons)
6. Slide "Gouvernance" (organigramme CSS ou matrice RACI stylisee)
7. Slide "Facteurs cles de succes" (highlights en 2 colonnes avec icones)
8. Slide "Pourquoi WEnvision" (3 stats impactantes avec barres de progression)
9. Slide "Equipe proposee" (grille de cartes CV avec icone profil)
10. Slide de cloture (fond sombre, "Merci", contact)"""
            type_instruction = f"""Redige une PROPOSITION COMMERCIALE de {num_slides} slides.
Ton : expert, convaincant, oriente ROI et resultats.
Chaque slide doit demontrer la valeur ajoutee de WEnvision avec des visuels percutants.
{visual_rules}"""

        elif gen_type == "formation":
            structure = """
1. Slide de couverture (fond sombre, titre formation, duree, icone education SVG)
2. Slide "Objectifs pedagogiques" (highlights numerotes avec icones cibles SVG)
3. Slides de contenu (alterner : THEORIE avec bullets + icones, PRATIQUE avec schema etapes, QUIZ avec cartes question/reponse, DEMO avec flow CSS)
4. Slide "Recapitulatif" (highlights en grille de cartes avec icones)
5. Slide de cloture (fond sombre, "Questions ?", contact formateur)"""
            type_instruction = f"""Redige un SUPPORT DE FORMATION de {num_slides} slides.
Ton : pedagogique, progressif, avec exercices pratiques.
Utilise des tags visuels dans les titres : [THEORIE], [PRATIQUE], [QUIZ], [DEMO].
{visual_rules}"""

        elif gen_type == "rex":
            structure = """
1. Slide de couverture (fond sombre, titre mission, client, icone mission SVG)
2. Slide "Contexte & Enjeux" (problematique client avec icones par enjeu)
3. Slide "Demarche" (diagramme CSS de la methodologie appliquee)
4. Slide "Timeline" (timeline horizontale CSS avec jalons chronologiques)
5. Slide "Realisations" (grille de cartes livrables avec icones)
6. Slide "Resultats & Impact" (3-4 stats geantes avec barres avant/apres)
7. Slide "Apprentissages" (highlights en 2 colonnes avec icones)
8. Slide "Recommandations" (prochaines etapes en flow CSS)
9. Slide de cloture (fond sombre, "Merci", contact)"""
            type_instruction = f"""Redige un RETOUR D'EXPERIENCE (REX) de {num_slides} slides.
Ton : factuel, oriente resultats, avec des chiffres concrets.
Mets en valeur les realisations et l'impact mesurable avec des visuels.
{visual_rules}"""

        else:  # presentation
            structure = """
1. Slide de couverture (fond sombre, titre impactant, barre corail, formes decoratives)
2. Slide "Agenda" ou "Objectifs" (highlights numerotes avec icones SVG)
3. Slides de contenu (alterner obligatoirement : bullets avec icones, stat impactant avec barres, citation stylisee, 2 colonnes avec cartes, diagramme CSS, grille de cartes illustrees)
4. Slide de cloture (fond sombre, "Merci", contact)"""
            type_instruction = f"""Cree une PRESENTATION de {num_slides} slides.
Ton : professionnel, clair, visuellement riche et impactant.
{visual_rules}"""

        return f"""{lang_prefix}{type_instruction}

SUJET : {topic}{audience_section}{doc_section}{extra_section}

La presentation doit suivre cette structure :
{structure}

Chaque slide doit inclure des speaker notes dans <div class="notes">.
Genere le HTML complet maintenant."""

    def build_prompt(
        self,
        topic: str,
        num_slides: int,
        design_system: Dict[str, Any],
        gen_type: str = "presentation",
        audience: str = "",
        document_text: str = "",
        extra_context: str = "",
        language: str = "fr",
    ) -> Tuple[str, str]:
        """Construit system_instruction et user_prompt."""
        system_instruction = self._build_system_instruction(design_system)
        user_prompt = self._build_user_prompt(
            topic,
            num_slides,
            gen_type,
            audience,
            document_text,
            extra_context,
            language,
        )
        return system_instruction, user_prompt

    @staticmethod
    def extract_sections_from_buffer(buffer: str) -> List[str]:
        """Extrait les <section ...>...</section> completes d'un buffer HTML."""
        sections = []
        pos = 0
        while True:
            start = buffer.find("<section", pos)
            if start == -1:
                break
            depth = 0
            i = start
            while i < len(buffer):
                if buffer[i : i + 8] == "<section":
                    depth += 1
                    i += 8
                elif buffer[i : i + 10] == "</section>":
                    depth -= 1
                    if depth == 0:
                        sections.append(buffer[start : i + 10])
                        pos = i + 10
                        break
                    i += 10
                else:
                    i += 1
            else:
                break  # Incomplete section
        return sections

    @staticmethod
    def extract_head_html(buffer: str) -> str:
        """Extrait le contenu du <head> (styles, fonts) du buffer HTML."""
        head_start = buffer.find("<head")
        if head_start == -1:
            return ""
        head_start = buffer.find(">", head_start) + 1
        head_end = buffer.find("</head>", head_start)
        if head_end == -1:
            return ""
        return buffer[head_start:head_end]

    @staticmethod
    def parse_section_to_json(section_html: str) -> Dict[str, Any]:
        """Parse une section HTML en objet JSON slide pour les exports."""
        slide = {}

        # Detecter le data-type
        type_match = re.search(r'data-type=["\'](\w+)["\']', section_html)
        if type_match:
            slide["type"] = type_match.group(1)
        else:
            # Heuristique basee sur le contenu et le style
            if "closing" in section_html.lower() or (
                "merci" in section_html.lower() and "#1F1F1F" in section_html
            ):
                slide["type"] = "closing"
            elif "#1F1F1F" in section_html or "background" in section_html:
                # Dark background = cover or section
                slide["type"] = "cover"
            else:
                slide["type"] = "content"

        # Extraire le titre (h1 ou h2)
        title_match = re.search(r"<h[12][^>]*>(.*?)</h[12]>", section_html, re.DOTALL)
        if title_match:
            slide["title"] = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        # Extraire le sous-titre (h3 ou premier p apres le titre)
        subtitle_match = re.search(r"<h3[^>]*>(.*?)</h3>", section_html, re.DOTALL)
        if subtitle_match:
            slide["subtitle"] = re.sub(r"<[^>]+>", "", subtitle_match.group(1)).strip()

        # Extraire les bullets (li elements)
        bullets = re.findall(r"<li[^>]*>(.*?)</li>", section_html, re.DOTALL)
        if bullets:
            slide["bullets"] = [re.sub(r"<[^>]+>", "", b).strip() for b in bullets]

        # Extraire les speaker notes
        notes_match = re.search(r'<div[^>]*class="notes"[^>]*>(.*?)</div>', section_html, re.DOTALL)
        if notes_match:
            slide["notes"] = re.sub(r"<[^>]+>", "", notes_match.group(1)).strip()

        # Type-specific extraction
        stype = slide.get("type", "content")

        if stype == "stat":
            # Chercher un gros chiffre
            stat_match = re.search(
                r"(?:font-size:\s*(?:3|4|5|6|7|8)\d*(?:px|rem|em|vw))[^>]*>([^<]+)", section_html
            )
            if stat_match:
                slide["stat_value"] = stat_match.group(1).strip()
            # Ou chercher un nombre isole dans un grand element
            if "stat_value" not in slide:
                big_num = re.search(r">(\d+[%+]?)</(?:span|div|p|h\d)", section_html)
                if big_num:
                    slide["stat_value"] = big_num.group(1)
            slide["stat_label"] = slide.pop("subtitle", "")

        elif stype == "quote":
            quote_match = re.search(r"<blockquote[^>]*>(.*?)</blockquote>", section_html, re.DOTALL)
            if quote_match:
                slide["quote_text"] = re.sub(r"<[^>]+>", "", quote_match.group(1)).strip()
            # Auteur
            author_match = re.search(
                r"(?:author|cite|attribution)[^>]*>(.*?)</", section_html, re.DOTALL | re.IGNORECASE
            )
            if author_match:
                slide["author"] = re.sub(r"<[^>]+>", "", author_match.group(1)).strip()

        elif stype == "highlight":
            slide["key_points"] = slide.pop("bullets", [])

        elif stype == "two_column":
            # Try to find left/right column content
            cols = re.findall(
                r'<div[^>]*class="[^"]*col[^"]*"[^>]*>(.*?)</div>', section_html, re.DOTALL
            )
            if len(cols) >= 2:
                left_bullets = re.findall(r"<li[^>]*>(.*?)</li>", cols[0], re.DOTALL)
                right_bullets = re.findall(r"<li[^>]*>(.*?)</li>", cols[1], re.DOTALL)
                slide["left_points"] = [re.sub(r"<[^>]+>", "", b).strip() for b in left_bullets]
                slide["right_points"] = [re.sub(r"<[^>]+>", "", b).strip() for b in right_bullets]
                # Column titles
                left_title = re.search(r"<h\d[^>]*>(.*?)</h\d>", cols[0])
                right_title = re.search(r"<h\d[^>]*>(.*?)</h\d>", cols[1])
                if left_title:
                    slide["left_title"] = re.sub(r"<[^>]+>", "", left_title.group(1)).strip()
                if right_title:
                    slide["right_title"] = re.sub(r"<[^>]+>", "", right_title.group(1)).strip()

        elif stype == "table":
            # Extract headers
            headers = re.findall(r"<th[^>]*>(.*?)</th>", section_html, re.DOTALL)
            if headers:
                slide["headers"] = [re.sub(r"<[^>]+>", "", h).strip() for h in headers]
            # Extract rows
            rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", section_html, re.DOTALL)
            rows = []
            for row_html in rows_html:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL)
                if cells:
                    rows.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])
            if rows:
                slide["rows"] = rows

        elif stype == "cover":
            # Meta info (date, company)
            meta_match = re.search(
                r'<(?:p|span|div)[^>]*class="[^"]*meta[^"]*"[^>]*>(.*?)</', section_html, re.DOTALL
            )
            if meta_match:
                slide["meta"] = re.sub(r"<[^>]+>", "", meta_match.group(1)).strip()
            if not slide.get("subtitle"):
                # Look for any secondary text
                p_tags = re.findall(r"<p[^>]*>(.*?)</p>", section_html, re.DOTALL)
                for p in p_tags:
                    text = re.sub(r"<[^>]+>", "", p).strip()
                    if text and text != slide.get("title", ""):
                        slide["subtitle"] = text
                        break

        elif stype == "closing":
            if not slide.get("subtitle"):
                p_tags = re.findall(r"<p[^>]*>(.*?)</p>", section_html, re.DOTALL)
                subtitles = []
                for p in p_tags:
                    text = re.sub(r"<[^>]+>", "", p).strip()
                    if text and text != slide.get("title", ""):
                        subtitles.append(text)
                if subtitles:
                    slide["subtitle"] = "\n".join(subtitles)

        # Ensure title exists
        if "title" not in slide:
            slide["title"] = slide.get("type", "Slide")

        return slide

    def run_streaming(
        self,
        topic: str,
        num_slides: int = 10,
        gen_type: str = "presentation",
        audience: str = "",
        document_text: str = "",
        extra_context: str = "",
        language: str = "fr",
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming pipeline : yield chaque slide au fur et a mesure.
        Chaque yield contient :
        - head_html: le contenu <head> (envoye avec la premiere slide)
        - html_section: le HTML de la section
        - slide_json: l'objet JSON pour les exports
        - index: l'index de la slide
        """
        design_system = self.extract_design_system()
        system_instruction, user_prompt = self.build_prompt(
            topic,
            num_slides,
            design_system,
            gen_type,
            audience,
            document_text,
            extra_context,
            language,
        )

        messages = [{"role": "user", "content": user_prompt}]
        buffer = ""
        sections_sent = 0
        head_html = ""

        # Scale max_tokens based on slide count (~1500 tokens per slide + head)
        scaled_tokens = min(num_slides * 1500 + 2000, 65536)

        for chunk in self.llm.stream_with_context(
            messages=messages,
            system_prompt=system_instruction,
            temperature=0.2,
            max_tokens=scaled_tokens,
            timeout=30000,
        ):
            buffer += chunk

            # Extract head on first pass
            if not head_html:
                head_html = self.extract_head_html(buffer)

            # Extract completed sections
            sections = self.extract_sections_from_buffer(buffer)
            while sections_sent < len(sections):
                section_html = sections[sections_sent]
                slide_json = self.parse_section_to_json(section_html)

                yield {
                    "head_html": head_html if sections_sent == 0 else "",
                    "html_section": section_html,
                    "slide_json": slide_json,
                    "index": sections_sent,
                }
                sections_sent += 1

    def clean_html_response(self, raw_response: str) -> str:
        """Nettoie la reponse de l'API (supprime backticks markdown)."""
        result = raw_response.strip()

        if result.startswith("```html"):
            result = result[7:]
        elif result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        result = result.strip()

        if not result.startswith("<!DOCTYPE") and not result.startswith("<html"):
            for marker in ["<!DOCTYPE html>", "<!DOCTYPE HTML>", "<html"]:
                idx = result.find(marker)
                if idx != -1:
                    result = result[idx:]
                    break

        return result

    def save_html(self, html_content: str) -> str:
        """Sauvegarde le HTML dans output/. Retourne le chemin relatif."""
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"presentation_premium_{timestamp}.html"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(filepath.relative_to(self.base_dir))

    def run(
        self,
        topic: str,
        num_slides: int = 10,
        language: str = "fr",
        gen_type: str = "presentation",
    ) -> Dict[str, Any]:
        """Pipeline complet (non-streaming) pour compatibilite."""
        print("\n  GENERATION SLIDES HTML PREMIUM")
        print(f"  Sujet: {topic[:80]}...")
        print(f"  Slides: {num_slides}")

        design_system = self.extract_design_system()
        system_instruction, user_prompt = self.build_prompt(
            topic,
            num_slides,
            design_system,
            gen_type,
            language=language,
        )

        messages = [{"role": "user", "content": user_prompt}]
        scaled_tokens = min(num_slides * 1500 + 2000, 65536)
        raw_html = self.llm.generate_with_context(
            messages=messages,
            system_prompt=system_instruction,
            temperature=0.2,
            max_tokens=scaled_tokens,
            timeout=30000,
        )

        html_content = self.clean_html_response(raw_html)
        html_path = self.save_html(html_content)

        print(f"  Presentation sauvegardee : {html_path}")

        return {
            "html_content": html_content,
            "html_path": html_path,
            "topic": topic,
            "num_slides": num_slides,
            "design_system": {k: v for k, v in design_system.items() if k != "template_context"},
            "generated_at": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    agent = HtmlSlideGeneratorAgent()
    result = agent.run(
        topic="Introduction a l'IA Generative pour les entreprises",
        num_slides=5,
    )
    print(f"Fichier genere : {result['html_path']}")
