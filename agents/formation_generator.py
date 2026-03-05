"""
Agent de génération de Programmes de Formation
Prend en entrée un besoin client et remplit le Template Programme Formation
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from utils.llm_client import LLMClient


class FormationGeneratorAgent:
    """Agent qui génère un programme de formation à partir d'un besoin client"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)
        self.template = self._load_template()

    def _load_template(self) -> str:
        """Charge le template Programme Formation"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "[Template Programme Formation].md",
        )
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ Template non trouvé: {template_path}")
            return ""

    def generate_programme(self, client_needs: str) -> Dict[str, Any]:
        """
        Génère un programme de formation complet à partir du besoin client.

        Args:
            client_needs: Description du besoin client en texte libre

        Returns:
            Dict avec le programme structuré et le markdown généré
        """
        print("📋 Analyse du besoin client...")

        system_prompt = """Tu es un expert en ingénierie pédagogique chez Consulting Tools, cabinet de conseil en Stratégie Data & IA.
Tu dois remplir un template de programme de formation en te basant sur le besoin client.

RÈGLES OBLIGATOIRES :
- Chaque champ du template doit être rempli avec du contenu pertinent et professionnel
- La description doit être accrocheuse/vendeuse, minimum 500 caractères
- Les objectifs doivent suivre la taxonomie de Bloom (Connaître, Comprendre, Appliquer, Analyser, Évaluer, Créer)
- Le programme doit être structuré par jours et par modules
- Chaque module contient des ateliers pratiques
- Adapter le niveau (100=tous niveaux, 200=avancé, 300=expertise)
- Prends en considération le public cible et la durée
- Sois pragmatique et orienté business (style Consulting Tools)
- Toutes les compétences doivent être vérifiables et mesurables"""

        prompt = f"""Voici le besoin client :
---
{client_needs}
---

Voici le template à remplir :
---
{self.template}
---

Remplis COMPLÈTEMENT ce template en te basant sur le besoin client.
Remplace chaque placeholder ({{{{...}}}}) et chaque indication entre accolades par du contenu réel.
Conserve la structure markdown exacte du template.
Retourne UNIQUEMENT le document markdown rempli, sans explication ni commentaire."""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Nettoyer le résultat
        result = result.strip()
        if result.startswith("```markdown"):
            result = result[len("```markdown") :]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        # Extraire les métadonnées
        metadata = self._extract_metadata(result)

        print(f"✅ Programme généré : {metadata.get('title', 'Sans titre')}")

        return {
            "markdown": result,
            "metadata": metadata,
            "generated_at": datetime.now().isoformat(),
        }

    def regenerate_with_feedback(self, previous_programme: str, feedback: str) -> Dict[str, Any]:
        """Régénère le programme avec du feedback utilisateur"""
        print("🔄 Régénération avec feedback...")

        system_prompt = """Tu es un expert en ingénierie pédagogique chez Consulting Tools.
Tu dois modifier un programme de formation existant en tenant compte du feedback de l'utilisateur.
Conserve la structure markdown et améliore le contenu selon les indications."""

        prompt = f"""Voici le programme de formation actuel :
---
{previous_programme}
---

Voici le feedback de l'utilisateur :
---
{feedback}
---

Modifie le programme en tenant compte du feedback. Retourne UNIQUEMENT le document markdown modifié."""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Nettoyer
        result = result.strip()
        if result.startswith("```markdown"):
            result = result[len("```markdown") :]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        metadata = self._extract_metadata(result)

        return {
            "markdown": result,
            "metadata": metadata,
            "generated_at": datetime.now().isoformat(),
        }

    def _extract_metadata(self, markdown: str) -> Dict[str, str]:
        """Extrait les métadonnées du programme (titre, durée, niveau)"""
        metadata = {}
        lines = markdown.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# **") and stripped.endswith("**"):
                metadata["title"] = stripped.replace("# **", "").replace("**", "").strip()
            elif "Durée du cours" in stripped:
                parts = stripped.split(":")
                if len(parts) > 1:
                    metadata["duration"] = parts[-1].strip()
            elif stripped.startswith("## ") and not stripped.startswith("## {"):
                # Capture le code du cours
                code = stripped.replace("## ", "").strip()
                if not metadata.get("code"):
                    metadata["code"] = code

        return metadata


if __name__ == "__main__":
    agent = FormationGeneratorAgent()
    result = agent.generate_programme(
        "Formation de 3 jours sur l'IA Générative pour des managers non-techniques. "
        "Focus sur les cas d'usage business, la stratégie d'implémentation et la gouvernance."
    )
    print(result["markdown"][:500])
