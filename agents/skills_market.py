"""
Agent Market of Skills - Parse les CV consultants depuis PPTX,
analyse les forces/faiblesses, et recherche en langage naturel
"""

import json
import re
from typing import Any, Dict, List, Optional

from utils.llm_client import LLMClient
from utils.pptx_reader import read_pptx_template


class SkillsMarketAgent:
    """Agent pour le Market of Skills des consultants Consulting Tools"""

    def __init__(self):
        self.llm = LLMClient()

    def parse_consultant_slide(self, slide_text: str) -> Optional[Dict]:
        """
        Parse le texte brut d'un slide PPTX en profil structure

        Args:
            slide_text: Texte extrait du slide

        Returns:
            Dict structure ou None si le slide n'est pas un CV
        """
        if not slide_text or len(slide_text.strip()) < 30:
            return None

        prompt = f"""Analyse ce texte extrait d'un slide de CV/biographie
d'un consultant Consulting Tools et retourne un JSON structure.

TEXTE DU SLIDE:
{slide_text}

Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{{
    "name": "Prenom Nom du consultant",
    "title": "Titre/poste du consultant",
    "bio": "Resume court du profil (2-3 phrases)",
    "skills_technical": [
        {{"name": "Nom competence technique", "level": "expert|senior|confirmed|junior"}}
    ],
    "skills_sector": [
        {{"name": "Nom expertise sectorielle", "level": "expert|senior|confirmed|junior"}}
    ],
    "missions": [
        {{
            "client_name": "Nom client",
            "context_and_challenges": "Contexte et enjeux",
            "deliverables": "Livrables",
            "tasks": "Taches effectuees"
        }}
    ],
    "interests": ["centre d'interet 1", "centre d'interet 2"],
    "strengths": ["point fort 1", "point fort 2"],
    "improvement_areas": ["axe d'amelioration 1"],
    "management_suggestions": "Suggestions pour le management"
}}

REGLES:
- Si le texte n'est PAS un CV/biographie de consultant, retourne
  {{"skip": true}}
- Deduis les competences techniques et sectorielles du contenu
- Deduis les points forts a partir des missions et competences
- Propose des axes d'amelioration constructifs
- Les suggestions manageriales doivent etre concretes et bienveillantes
- Retourne UNIQUEMENT le JSON, rien d'autre"""

        system_prompt = (
            "Tu es un expert RH specialise dans le consulting."
            " Tu analyses des CV de consultants pour en extraire"
            " les informations structurees. Reponds uniquement en JSON."
        )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )
            return self._parse_json_response(response)
        except Exception as e:
            print(f"Erreur parsing consultant: {e}")
            return None

    def import_from_pptx(
        self,
        pptx_path: str,
        progress_callback=None,
    ) -> List[Dict]:
        """
        Importe tous les consultants depuis un fichier PPTX

        Args:
            pptx_path: Chemin vers le PPTX
            progress_callback: Fonction appelee avec (index, total, name)

        Returns:
            Liste de profils consultants structures
        """
        template = read_pptx_template(pptx_path)
        slides = template["slides"]
        total = len(slides)
        consultants = []

        for i, slide in enumerate(slides):
            slide_text = "\n".join(slide.get("content", []))

            if progress_callback:
                progress_callback(i + 1, total, f"Slide {i + 1}")

            parsed = self.parse_consultant_slide(slide_text)

            if parsed and not parsed.get("skip"):
                parsed["raw_pptx_text"] = slide_text
                consultants.append(parsed)

                if progress_callback:
                    name = parsed.get("name", f"Consultant {i + 1}")
                    progress_callback(i + 1, total, name)

        return consultants

    def import_from_text(
        self,
        text: str,
        source_filename: str = "",
        progress_callback=None,
    ) -> List[Dict]:
        """
        Importe des consultants depuis du texte brut (PDF, HTML, etc.)
        Le texte peut contenir un ou plusieurs CV.

        Args:
            text: Texte brut extrait du document
            source_filename: Nom du fichier source
            progress_callback: Fonction appelee avec (index, total, name)

        Returns:
            Liste de profils consultants structures
        """
        if not text or len(text.strip()) < 50:
            return []

        if progress_callback:
            progress_callback(1, 2, "Analyse du document...")

        # Use LLM to split and parse multiple CVs from text
        prompt = f"""Analyse ce document qui contient un ou plusieurs
CV/biographies de consultants.

DOCUMENT ({source_filename}):
{text[:15000]}

Pour CHAQUE consultant identifie dans le document, retourne un JSON.
Retourne UNIQUEMENT un JSON valide:
{{
    "consultants": [
        {{
            "name": "Prenom Nom",
            "title": "Titre/poste",
            "bio": "Resume court (2-3 phrases)",
            "skills_technical": [
                {{"name": "competence", "level": "expert|senior|confirmed|junior"}}
            ],
            "skills_sector": [
                {{"name": "secteur", "level": "expert|senior|confirmed|junior"}}
            ],
            "missions": [
                {{
                    "client_name": "Client",
                    "context_and_challenges": "Contexte",
                    "deliverables": "Livrables",
                    "tasks": "Taches"
                }}
            ],
            "interests": ["interet1"],
            "strengths": ["point fort 1"],
            "improvement_areas": ["axe amelioration 1"],
            "management_suggestions": "Suggestions manageriales"
        }}
    ]
}}

REGLES:
- Identifie tous les consultants distincts dans le document
- Si le document ne contient qu'un seul CV, retourne un seul element
- Deduis competences, forces et axes d'amelioration
- Retourne UNIQUEMENT le JSON"""

        system_prompt = (
            "Tu es un expert RH specialise dans le consulting."
            " Tu analyses des CV pour en extraire les informations"
            " structurees. Reponds uniquement en JSON."
        )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=8192,
            )
            result = self._parse_json_response(response)

            if result and "consultants" in result:
                consultants = result["consultants"]
                for c in consultants:
                    c["raw_pptx_text"] = text[:2000]
                if progress_callback:
                    progress_callback(2, 2, f"{len(consultants)} consultant(s) trouves")
                return consultants

            # Fallback: try parsing as single consultant
            if result and "name" in result:
                result["raw_pptx_text"] = text[:2000]
                if progress_callback:
                    progress_callback(2, 2, "1 consultant trouve")
                return [result]

        except Exception as e:
            print(f"Erreur import texte: {e}")

        return []

    def analyze_strengths(self, consultant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les forces et axes d'amelioration d'un consultant

        Args:
            consultant_data: Profil complet du consultant

        Returns:
            Dict avec strengths, improvement_areas,
            management_suggestions
        """
        skills_tech = [
            s.get("name", s) if isinstance(s, dict) else s
            for s in consultant_data.get("skills_technical", [])
        ]
        skills_sector = [
            s.get("name", s) if isinstance(s, dict) else s
            for s in consultant_data.get("skills_sector", [])
        ]
        missions = consultant_data.get("missions", [])
        missions_desc = []
        for m in missions[:5]:
            if isinstance(m, dict):
                missions_desc.append(
                    f"- {m.get('client_name', 'N/A')}: " f"{m.get('context_and_challenges', '')}"
                )

        prompt = f"""Analyse le profil de ce consultant et fournis une
evaluation constructive.

NOM: {consultant_data.get('name', 'N/A')}
TITRE: {consultant_data.get('title', 'N/A')}
BIO: {consultant_data.get('bio', 'N/A')}

COMPETENCES TECHNIQUES: {', '.join(skills_tech)}
EXPERTISE SECTORIELLE: {', '.join(skills_sector)}

MISSIONS:
{chr(10).join(missions_desc)}

Retourne UNIQUEMENT un JSON:
{{
    "strengths": ["point fort 1", "point fort 2", "point fort 3"],
    "improvement_areas": [
        "axe d'amelioration 1",
        "axe d'amelioration 2"
    ],
    "management_suggestions": "Paragraphe avec suggestions concretes
pour le management afin d'aider ce consultant a progresser"
}}

REGLES:
- 3 a 5 points forts, bases sur les missions et competences
- 2 a 3 axes d'amelioration constructifs
- Les suggestions manageriales doivent etre concretes,
  bienveillantes et actionables
- Retourne UNIQUEMENT le JSON"""

        system_prompt = (
            "Tu es un manager bienveillant en cabinet de conseil."
            " Tu evalues les consultants pour les aider a progresser."
        )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
            )
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception as e:
            print(f"Erreur analyse consultant: {e}")

        return {
            "strengths": consultant_data.get("strengths", []),
            "improvement_areas": consultant_data.get("improvement_areas", []),
            "management_suggestions": consultant_data.get("management_suggestions", ""),
        }

    def natural_language_search(
        self,
        query: str,
        consultants: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Recherche de consultants en langage naturel via LLM

        Args:
            query: Requete en langage naturel
            consultants: Liste des profils consultants

        Returns:
            Liste ordonnee par pertinence avec score et explication
        """
        if not consultants:
            return []

        summaries = []
        for c in consultants:
            skills = []
            for s in c.get("top_skills", []):
                if isinstance(s, dict):
                    skills.append(s.get("name", ""))
                else:
                    skills.append(str(s))
            for s in c.get("skills_technical", []):
                if isinstance(s, dict):
                    skills.append(s.get("name", ""))
            for s in c.get("skills_sector", []):
                if isinstance(s, dict):
                    skills.append(s.get("name", ""))

            missions_info = []
            for m in c.get("missions", [])[:3]:
                if isinstance(m, dict):
                    missions_info.append(m.get("client_name", ""))

            summary = (
                f"ID:{c['id']} | {c.get('name', 'N/A')}"
                f" | {c.get('title', 'N/A')}"
                f" | Skills: {', '.join(set(skills))}"
                f" | Clients: {', '.join(missions_info)}"
            )
            summaries.append(summary)

        prompt = f"""Recherche parmi ces consultants celui/ceux qui
correspondent le mieux a cette requete :

REQUETE: "{query}"

CONSULTANTS DISPONIBLES:
{chr(10).join(summaries)}

Retourne UNIQUEMENT un JSON:
{{
    "results": [
        {{
            "id": <id du consultant>,
            "score": <score de 0 a 100>,
            "explanation": "Explication courte de la pertinence"
        }}
    ]
}}

REGLES:
- Classe par score decroissant
- Ne retourne que les consultants pertinents (score > 30)
- L'explication doit etre en 1-2 phrases
- Retourne UNIQUEMENT le JSON"""

        system_prompt = (
            "Tu es un expert en staffing de cabinet de conseil."
            " Tu trouves le meilleur consultant pour chaque besoin."
        )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )
            result = self._parse_json_response(response)
            if result and "results" in result:
                return result["results"]
        except Exception as e:
            print(f"Erreur recherche NL: {e}")

        return []

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        Parse une reponse LLM contenant du JSON

        Args:
            response: Reponse brute du LLM

        Returns:
            Dict parse ou None
        """
        if not response:
            return None

        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Extract JSON from markdown code block
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{.*\}",
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    text = match.group(1) if "```" in pattern else match.group(0)
                    return json.loads(text)
                except json.JSONDecodeError:
                    continue

        return None

    def generate_cv(self, consultant: Dict, client_need: str = "") -> str:
        """
        Genere un CV HTML professionnel une page a partir du profil d'un consultant.

        Le CV est adapte au besoin client si fourni : les missions et competences
        les plus pertinentes sont selectionnees et reformulees pour matcher le besoin.

        Args:
            consultant: Profil complet issu de ConsultantDatabase.get_consultant().
                        Doit contenir skills_technical, skills_sector, certifications,
                        missions, name, title, bio.
            client_need: Description du besoin client en texte libre, markdown ou
                         contenu extrait d'un PDF (optionnel).

        Returns:
            Fragment HTML du CV, directement integrable dans une page web.
            Commence par une balise <div> ou <header>, sans <html>/<head>/<body>.
        """
        # --- Extraction des competences (schemas DB : liste de dicts avec "name") ---
        skills_tech = [
            s.get("name", str(s)) if isinstance(s, dict) else str(s)
            for s in (consultant.get("skills_technical") or [])
        ]
        skills_sector = [
            s.get("name", str(s)) if isinstance(s, dict) else str(s)
            for s in (consultant.get("skills_sector") or [])
        ]

        # --- Certifications (liste de dicts avec name, organization, date_obtained) ---
        cert_lines = []
        for c in (consultant.get("certifications") or []):
            if isinstance(c, dict):
                cert_lines.append(
                    "- "
                    + c.get("name", "")
                    + (f" ({c.get('organization', '')})" if c.get("organization") else "")
                    + (f", {c.get('date_obtained', '')}" if c.get("date_obtained") else "")
                )
            else:
                cert_lines.append(f"- {c}")

        # --- Missions (source principale de valeur pour l'adequation client) ---
        mission_blocks = []
        for m in (consultant.get("missions") or []):
            if isinstance(m, dict):
                parts = []
                if m.get("client_name"):
                    parts.append(f"Client : {m['client_name']}")
                if m.get("context_and_challenges"):
                    parts.append(f"Contexte : {m['context_and_challenges']}")
                if m.get("deliverables"):
                    parts.append(f"Livrables : {m['deliverables']}")
                if m.get("tasks"):
                    parts.append(f"Taches : {m['tasks']}")
                if parts:
                    mission_blocks.append("\n  ".join(parts))

        # --- Bloc d'adaptation au besoin client ---
        adaptation_block = ""
        if client_need:
            adaptation_block = (
                "\n\nADAPTATION AU BESOIN CLIENT :\n"
                + client_need.strip()[:3000]
                + "\n\nSelectionne et reformule en priorite les missions et competences "
                "qui correspondent a ce besoin. Reorganise les sections si necessaire "
                "pour maximiser la pertinence. Ne garde que les experiences utiles."
            )

        skills_tech_str = ", ".join(skills_tech) if skills_tech else "N/A"
        skills_sector_str = ", ".join(skills_sector) if skills_sector else "N/A"
        missions_str = (
            "\n\n".join(mission_blocks) if mission_blocks else "Aucune mission renseignee"
        )
        certs_str = "\n".join(cert_lines) if cert_lines else "Aucune"

        # Photo consultant si disponible
        photo_url = consultant.get("photo_url", "")
        photo_block = ""
        if photo_url:
            photo_block = f"\nPHOTO URL : {photo_url} (a integrer en haut a droite, img circulaire 80px)"

        prompt = f"""Genere un CV professionnel UNE PAGE A4 en HTML COMPLET pour ce consultant.

NOM : {consultant.get("name", "N/A")}
TITRE : {consultant.get("title", "N/A")}
EMAIL : {consultant.get("email") or (consultant.get("name", "consultant").lower().replace(" ", ".") + "@consulting.fr")}
LINKEDIN : {consultant.get("linkedin_url") or "linkedin.com/in/" + consultant.get("name", "consultant").lower().replace(" ", "-")}
BIO : {consultant.get("bio", "")}
{photo_block}
COMPETENCES TECHNIQUES : {skills_tech_str}
EXPERTISE SECTORIELLE : {skills_sector_str}

MISSIONS REALISEES :
{missions_str}

CERTIFICATIONS :
{certs_str}
{adaptation_block}

Genere un DOCUMENT HTML COMPLET (avec <!DOCTYPE html>, <html>, <head>, <body>) avec :
- CSS @page pour A4 portrait, marges 1.2cm, forcer une seule page
- Mise en page 2 colonnes : colonne gauche etroite (competences, certifications, contact), colonne droite large (profil, experiences)
- En-tete : nom en grand (bleu #1a3a5c), titre en dessous, email et linkedin
- Photo en haut a droite si URL fournie (img circulaire 80px)
- Section "Profil" : bio courte adaptee
- Section "Competences" : badges colores compacts (#e8f0fe fond, #1a3a5c texte)
- Section "Experiences" : missions reformulees (client, contexte bref, livrables), les plus pertinentes en premier
- Section "Certifications" si non vide
- Police Inter ou Arial, taille 9pt corps, compact pour tenir sur UNE page A4

REGLES STRICTES :
- Retourne UNIQUEMENT le HTML complet, sans markdown, sans explication, sans ```
- Commence par <!DOCTYPE html>
- CSS dans <style> dans <head>, pas de style inline sauf pour les badges
- Textes en francais professionnel
- UNE SEULE PAGE A4 PORTRAIT"""

        system_prompt = (
            "Tu es un designer RH expert en CVs consultants haute valeur. "
            "Tu reformules les missions pour maximiser la pertinence au besoin client. "
            "Tu generes des CVs HTML complets A4 visuellement professionnels tenant sur une page."
        )

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
        )

        cv_html = response.strip()
        cv_html = re.sub(r"^```(?:html)?\s*", "", cv_html)
        cv_html = re.sub(r"\s*```$", "", cv_html)
        return cv_html.strip()

    def generate_cover_letter(self, consultant: Dict, job_offer: str) -> str:
        """
        Genere une lettre de motivation HTML complete une page A4.

        Args:
            consultant: Profil complet du consultant (name, title, bio, skills, missions...)
            job_offer: Texte de l'offre d'emploi (libre ou copie-colle)

        Returns:
            Document HTML complet avec CSS A4, directement convertible en PDF.
        """
        name = consultant.get("name", "Consultant")
        title = consultant.get("title", "")
        email = consultant.get("email") or (name.lower().replace(" ", ".") + "@consulting.fr")
        linkedin = consultant.get("linkedin_url") or ""

        skills_tech = [
            s.get("name", str(s)) if isinstance(s, dict) else str(s)
            for s in (consultant.get("skills_technical") or [])
        ]
        skills_sector = [
            s.get("name", str(s)) if isinstance(s, dict) else str(s)
            for s in (consultant.get("skills_sector") or [])
        ]

        mission_highlights = []
        for m in (consultant.get("missions") or [])[:3]:
            if isinstance(m, dict):
                parts = []
                if m.get("client_name"):
                    parts.append(m["client_name"])
                if m.get("deliverables"):
                    parts.append((m["deliverables"])[:150])
                if parts:
                    mission_highlights.append(" — ".join(parts))

        skills_str = ", ".join(skills_tech[:8]) if skills_tech else "N/A"
        sector_str = ", ".join(skills_sector[:5]) if skills_sector else "N/A"
        missions_str = "\n".join(f"- {m}" for m in mission_highlights) if mission_highlights else ""

        prompt = f"""Redige une lettre de motivation professionnelle UNE PAGE A4 en HTML COMPLET
pour ce consultant qui postule a l'offre suivante.

PROFIL DU CONSULTANT :
Nom : {name}
Titre : {title}
Bio : {(consultant.get("bio") or "")[:300]}
Competences : {skills_str}
Secteurs : {sector_str}
Missions marquantes :
{missions_str}

OFFRE D'EMPLOI :
{job_offer[:3000]}

Genere un DOCUMENT HTML COMPLET (<!DOCTYPE html>, <html>, <head>, <body>) avec :
- CSS @page A4 portrait, marges 2cm, UNE SEULE PAGE
- En-tete : nom, titre, email ({email}){", LinkedIn : " + linkedin if linkedin else ""}
- Date du jour en haut a droite
- Destinataire : "Madame, Monsieur," (equipe RH)
- Corps : 3-4 paragraphes formels et percutants :
    1. Accroche : poste vise + interet sincere pour l'entreprise/mission
    2. Valeur ajoutee : competences et experiences les plus pertinentes pour l'offre
    3. Adequation : preuves concretes depuis les missions (resultats chiffrables si possible)
    4. Conclusion : disponibilite, entretien, formule de politesse
- Signature : {name}, {title}
- Police Inter ou Georgia, 10.5pt, neutre et professionnel
- Couleur accent sobre : #1a3a5c pour les titres/bordures

REGLES STRICTES :
- UNIQUEMENT le HTML complet, sans markdown, sans explication, sans ```
- Commence par <!DOCTYPE html>
- Texte en francais formel et professionnel
- Adapte le contenu precisement a l'offre (reprend les mots-cles de l'offre)
- UNE SEULE PAGE A4"""

        system_prompt = (
            "Tu es un expert RH et redacteur professionnel specialise dans les lettres de motivation "
            "pour consultants. Tu rediges des lettres percutantes, adaptees a l'offre, "
            "en valorisant le parcours du consultant de facon convaincante."
        )

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
        )

        letter_html = response.strip()
        letter_html = re.sub(r"^```(?:html)?\s*", "", letter_html)
        letter_html = re.sub(r"\s*```$", "", letter_html)
        return letter_html.strip()
