"""
Agent de generation de commentaires LinkedIn pertinents
Analyse un post et genere un commentaire engageant avec le persona Parisien GenZ
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import requests
from bs4 import BeautifulSoup

from config import get_consultant_info
from utils.llm_client import LLMClient


class LinkedInCommenterAgent:
    """Agent qui genere des commentaires LinkedIn pertinents et authentiques"""

    def __init__(self):
        self.llm_client = LLMClient()

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()

    def extract_post_content(self, post_input: str) -> Dict[str, Any]:
        """
        Extrait le contenu d'un post (soit du texte direct, soit via URL)

        Args:
            post_input: Texte du post OU URL LinkedIn

        Returns:
            Dictionnaire avec le contenu du post
        """
        # Si c'est une URL LinkedIn, essayer de scraper (sinon utiliser le texte tel quel)
        if post_input.strip().startswith("http"):
            print("🌐 Tentative de recuperation du post depuis l'URL...")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                }
                response = requests.get(post_input, headers=headers, timeout=10)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    # Essayer d'extraire le contenu (structure LinkedIn peut varier)
                    post_text = ""
                    for selector in [
                        ".feed-shared-update-v2__description",
                        ".feed-shared-text",
                        "article",
                    ]:
                        element = soup.select_one(selector)
                        if element:
                            post_text = element.get_text(strip=True)
                            break

                    if post_text:
                        print("   ✅ Post recupere depuis l'URL")
                        return {"content": post_text, "url": post_input, "source": "scraped"}
                else:
                    print(
                        f"   ⚠️  Impossible de recuperer l'URL (status {response.status_code}), utilisation du texte fourni"
                    )
            except Exception as e:
                from utils.validation import sanitize_error_message

                print(
                    f"   ⚠️  Erreur lors du scraping: {sanitize_error_message(str(e))}, utilisation du texte fourni"
                )

        # Fallback: utiliser le texte tel quel
        return {"content": post_input, "url": None, "source": "direct"}

    def generate_comments(
        self, post_content: Dict[str, Any], style: str = "insightful"
    ) -> Dict[str, Any]:
        """
        Genere des commentaires pertinents sur un post LinkedIn

        Args:
            post_content: Contenu du post (sortie de extract_post_content)
            style: Style du commentaire (insightful, question, experience, reaction)

        Returns:
            Dictionnaire avec 3 variantes de commentaires
        """
        print("✍️  Generation des commentaires...")

        # Charger le persona depuis le fichier
        persona_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "linkedin_persona.md",
        )
        persona_style = ""
        if os.path.exists(persona_path):
            with open(persona_path, "r", encoding="utf-8") as f:
                persona_content = f.read()
                # Extraire la section Ton & Style
                start_idx = persona_content.find("### ✨ Ton & Style")
                end_idx = persona_content.find("### 📝 Structure de posts")
                if start_idx != -1 and end_idx != -1:
                    persona_style = (
                        "\n\nSTYLE 'PARISIEN GENZ' A APPLIQUER:\n"
                        + persona_content[start_idx:end_idx]
                    )

        style_instructions = {
            "insightful": "Apporte un insight complementaire, une perspective experte. Enrichis la discussion.",
            "question": "Pose une question pertinente qui prolonge la reflexion. Creuse un point specifique.",
            "experience": "Partage brievement une experience similaire de ton cote (mission, observation terrain).",
            "reaction": "Reagis au point principal avec ton analyse. Valide ou nuance avec tact.",
        }

        system_prompt = """Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Base : Paris | Génération Z assumée
{persona_style}

Tu dois generer un COMMENTAIRE LINKEDIN en reponse a un post.

REGLES IMPERATIVES pour les commentaires :
- JAMAIS de "Merci pour le partage" ou formules generiques
- APPORTE DE LA VALEUR : insight, question, perspective complementaire
- Sois SPECIFIQUE au contenu du post, pas vague
- Ton authentique et direct (style Parisien GenZ)
- Entre 50 et 150 caracteres pour la version courte
- Entre 150 et 300 caracteres pour la version moyenne
- Entre 300 et 500 caracteres pour la version longue
- PAS d'emoji ou maximum 1 seul (🎯💡🔍)
- NE JAMAIS inventer de faits, chiffres ou anecdotes qui ne sont pas dans ton experience reelle

{style_instructions.get(style, style_instructions['insightful'])}"""

        prompt = """Genere 3 variantes de commentaire pour ce post LinkedIn :

CONTENU DU POST :
{post_content['content']}

---

Genere 3 variantes (SANS titre, SANS label, juste le texte du commentaire) :

1. VERSION COURTE (50-150 caracteres)
Une phrase percutante qui va droit au but.

2. VERSION MOYENNE (150-300 caracteres)
2-3 phrases avec un peu plus de substance.

3. VERSION LONGUE (300-500 caracteres)
Un commentaire developpe qui apporte vraiment de la valeur.

Pour chaque variante :
- Sois specifique au contenu du post
- Apporte de la valeur, pas du blabla
- Ton Parisien GenZ : direct, authentique, pas corporate
- Maximum 1 emoji ou pas du tout

Format de sortie :
VERSION_COURTE: [texte]
---
VERSION_MOYENNE: [texte]
---
VERSION_LONGUE: [texte]"""

        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000,
        )

        # Parser les 3 variantes
        parts = response.split("---")

        short = ""
        medium = ""
        long = ""

        for part in parts:
            part = part.strip()
            if "VERSION_COURTE:" in part:
                short = part.replace("VERSION_COURTE:", "").strip()
            elif "VERSION_MOYENNE:" in part:
                medium = part.replace("VERSION_MOYENNE:", "").strip()
            elif "VERSION_LONGUE:" in part:
                long = part.replace("VERSION_LONGUE:", "").strip()

        # Fallback si le parsing echoue
        if not short or not medium or not long:
            lines = response.split("\n")
            comments = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("VERSION")
            ]
            short = comments[0] if len(comments) > 0 else response[:150]
            medium = comments[1] if len(comments) > 1 else response[:300]
            long = comments[2] if len(comments) > 2 else response[:500]

        print("   ✅ Commentaires generes (3 variantes)")

        return {
            "short": short,
            "medium": medium,
            "long": long,
            "style": style,
            "post_preview": (
                post_content["content"][:200] + "..."
                if len(post_content["content"]) > 200
                else post_content["content"]
            ),
            "generated_at": datetime.now().isoformat(),
            "consultant": self.consultant_info,
        }

    def run(self, post_input: str, style: str = "insightful") -> Dict[str, Any]:
        """
        Pipeline complet: extrait post -> genere commentaires

        Args:
            post_input: Texte du post OU URL LinkedIn
            style: Style du commentaire

        Returns:
            Resultat complet
        """
        print(f"\n{'='*50}")
        print("💬 GENERATION DE COMMENTAIRE LINKEDIN")
        print(f"{'='*50}\n")

        post_content = self.extract_post_content(post_input)
        result = self.generate_comments(post_content, style=style)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, f"linkedin_comment_{timestamp}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Commentaires LinkedIn\n\n")
            f.write(f"**Style:** {style}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("## Post original (extrait)\n\n")
            f.write(f"> {result['post_preview']}\n\n")
            f.write("---\n\n")
            f.write("## Commentaire Court\n\n")
            f.write(result["short"])
            f.write("\n\n---\n\n## Commentaire Moyen\n\n")
            f.write(result["medium"])
            f.write("\n\n---\n\n## Commentaire Long\n\n")
            f.write(result["long"])
            f.write("\n")

        result["md_path"] = md_path
        print(f"\n✅ Commentaires sauvegardes: {md_path}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generer des commentaires LinkedIn pertinents")
    parser.add_argument("post", help="Texte du post OU URL LinkedIn")
    parser.add_argument(
        "--style",
        choices=["insightful", "question", "experience", "reaction"],
        default="insightful",
    )

    args = parser.parse_args()

    agent = LinkedInCommenterAgent()
    result = agent.run(post_input=args.post, style=args.style)

    print(f"\n{'='*50}")
    print("COMMENTAIRES GENERES")
    print(f"{'='*50}\n")
    print("📝 Court:\n" + result["short"])
    print("\n📝 Moyen:\n" + result["medium"])
    print("\n📝 Long:\n" + result["long"])


if __name__ == "__main__":
    main()
