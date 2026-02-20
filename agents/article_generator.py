"""
Agent de generation d'articles
Prend une idee et genere un article markdown avec le style Wenvision/Jean-Sebastien
+ generation d'illustration Nano Banana + post LinkedIn + sources web
"""
import os
import sys
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient


class ArticleGeneratorAgent:
    """Agent pour generer des articles de blog avec le style Wenvision"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.consultant_info = {
            'name': os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha'),
            'title': os.getenv('CONSULTANT_TITLE', 'Consultant en strategie data et IA'),
            'company': os.getenv('COMPANY_NAME', 'Wenvision'),
        }

    def generate_article(self, idea: str, target_length: str = "medium") -> str:
        """Genere un article markdown a partir d'une idee"""
        print("  [1/4] Generation de l'article...")

        length_map = {
            "short": "500-800 mots",
            "medium": "1000-1500 mots",
            "long": "2000-3000 mots"
        }
        target_words = length_map.get(target_length, "1000-1500 mots")

        writing_style = self._load_writing_style()

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.

{writing_style}

Tu rediges des articles de blog techniques et accessibles sur l'IA, la data et la transformation digitale.

TON STYLE D'ECRITURE ET REGLES STRICTES :
- Ton expert mais accessible : tu vulgarises sans simplifier a l'exces
- Concret et pragmatique : exemples reels, cas d'usage, retours d'experience
- Critique constructif : tu poses les bonnes questions, tu challenges les idees recues
- Pedagogue : tu expliques les concepts pas a pas
- Engageant : tu interpelles le lecteur, tu poses des questions rhetoriques
- INTERDICTION GRAMMATICALE : n'utilise absolument jamais le pronom "on" (privilegie "nous", "vous" ou la voix passive)
- REGLE TYPOGRAPHIQUE : ne mets jamais de majuscule au premier mot qui suit les deux-points (:)

STRUCTURE OBLIGATOIRE (CONCLUSION INVERSEE) :
1. Titre accrocheur (H1)
2. Chapeau et elements de conclusion : livre d'emblee les conclusions de l'article et les messages cles a retenir en 2 ou 3 phrases
3. Introduction (contexte + problematique)
4. Developpement en 3-4 sections (H2) avec sous-sections (H3) si besoin
5. Exemples concrets et cas d'usage
6. Points de vigilance / pieges a eviter
7. Ouverture finale ou call-to-action (puisque la conclusion est au debut)

FORMAT MARKDOWN :
- Utilise # pour H1, ## pour H2, ### pour H3
- **Gras** pour mettre en avant des concepts cles
- `code` pour les termes techniques
- > Citations pour les points importants
- Listes a puces pour les enumerations
- Pas d'emojis"""

        prompt = f"""Redige un article de blog complet ({target_words}) sur le sujet suivant :

{idea}

L'article doit :
- Apporter de la valeur et des insights concrets
- Etre base sur des faits et ton expertise (pas d'invention)
- Inclure des exemples pratiques et cas d'usage
- Livrer les conclusions et les takeaways des le debut de l'article
- Respecter strictement l'interdiction d'utiliser le pronom "on"
- Respecter strictement l'absence de majuscule apres les deux-points (:)
- Se terminer par une ouverture engageante

Retourne l'article directement en markdown, sans preambule."""

        return self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

    def generate_linkedin_post(self, article: str, article_title: str = "", article_url: str = "") -> str:
        """Genere un post LinkedIn pour promouvoir l'article"""
        print("  [2/4] Generation du post LinkedIn...")

        system_prompt = f"""# CONTEXTE
Tu viens de publier un article de blog sur le site de {self.consultant_info['company']}. Tu dois en faire la promotion via un post sur LinkedIn.

# ROLE
Agis en tant que "ghostwriter" personnel, specialise dans la creation de contenu "thought leadership" pour des consultants en transformation digitale sur LinkedIn. Tu connais parfaitement les codes de la plateforme.

# PROFIL
- Poste : {self.consultant_info['title']} chez {self.consultant_info['company']}.
- Style : Pragmatique, gen z, parisien, oriente resultats, avec une vision critique et constructive sur les technologies. Aime aller a contre-courant des "buzzwords".

# OBJECTIFS DU POST
1. Susciter le debat et l'engagement (commentaires, partages).
2. Asseoir l'expertise en montrant une perspective nuancee et basee sur l'experience terrain.
3. Generer du trafic qualifie vers l'article.

# INSTRUCTIONS
Redige une proposition de post LinkedIn qui respecte les points suivants :
1. Accroche percutante : Commence par une phrase ou une question un peu provocatrice qui remet en cause une idee recue.
2. Corps du texte : Resume l'idee centrale de l'article en 2-3 phrases claires.
3. Appel a l'action (CTA) : Termine par une question ouverte pour lancer la discussion dans les commentaires.
4. Hashtags : Propose 5 hashtags pertinents et strategiques (#IA, #Data, #GouvernanceDeDonnees, #TransformationDigitale, #WEnvision).

Livre uniquement le texte du post, sans explication."""

        prompt = f"""Voici l'article pour lequel generer le post LinkedIn :

TITRE : {article_title}
{f'URL : {article_url}' if article_url else ''}

CONTENU :
{article[:3000]}

Genere le post LinkedIn."""

        return self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

    def generate_illustration(self, article: str) -> Optional[str]:
        """Genere une illustration via Nano Banana Pro"""
        print("  [3/4] Generation de l'illustration...")
        try:
            from utils.image_generator import NanoBananaGenerator
            generator = NanoBananaGenerator()

            output_dir = self.base_dir / "output" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"article_illustration_{timestamp}.jpg")

            result = generator.generate_article_illustration(article, output_path)
            return result
        except Exception as e:
            print(f"  [NanoBanana] Erreur illustration: {e}")
            return None

    def research_web_sources(self, article: str) -> List[Dict[str, str]]:
        """Recherche des sources web fiables pour illustrer les points de l'article"""
        print("  [4/4] Recherche de sources web...")

        system_prompt = """Tu es un assistant de recherche specialise dans la data et l'IA.
Tu dois trouver des sources fiables pour etayer les points d'un article."""

        prompt = f"""A partir de cet article, identifie les 5-8 affirmations ou concepts cles qui gagneraient a etre sourcess :

{article[:3000]}

Pour chaque affirmation, suggere une source fiable (etude, rapport, article de reference) avec :
- Le titre de la source
- L'URL probable (utilise des sources connues : Gartner, McKinsey, Harvard Business Review, MIT Technology Review, etc.)
- Un bref extrait pertinent (1-2 phrases)

Reponds au format JSON :
```json
[
  {{"title": "...", "url": "...", "excerpt": "...", "related_point": "..."}},
  ...
]
```"""

        response = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.3)

        # Extraire le JSON
        try:
            import json
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except Exception:
            return []

    def _load_writing_style(self) -> str:
        style_path = self.base_dir / "data" / "writing_style.md"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                return f"STYLE D'ECRITURE SPECIFIQUE :\n{f.read()}"
        return ""

    def generate_illustration_prompt(self, article: str) -> str:
        """Genere un prompt pour Nano Banana Pro"""
        return f"""Role & Objective: You are an expert Art Director for a high-end tech consultancy firm.
Your task is to generate a premium, cinematic illustration based on the Blog Post provided below.

Analysis Instructions:
1. Read the blog post below.
2. Extract the core metaphor.
3. Ignore literal elements. Focus on the concept of "Orchestrating Intelligence".

Visual Style Guidelines:
* Aesthetic: Unreal Engine 5 render, isometric or wide-angle, 8k resolution.
* Mood: Sophisticated, futuristic but grounded, "Corporate Tech".
* Lighting: Dramatic contrast between cool electric blues (representing the AI data stream) and warm amber/gold (representing the human touch/value).
* Composition: A central human figure (silhouette or back view) controlling or structuring a massive, complex digital structure.

Input Text (The Blog Post):
{article[:3000]}

Action: Generate the illustration now based on this analysis."""

    def run(self, idea: str, target_length: str = "medium") -> Dict[str, Any]:
        """Pipeline complet : article + LinkedIn post + image + sources"""
        print(f"\n  GENERATION D'ARTICLE")
        print(f"  Idee : {idea[:100]}...")

        # 1. Generation de l'article
        article = self.generate_article(idea, target_length)

        # 2. Generation du post LinkedIn
        linkedin_post = self.generate_linkedin_post(article, article_title=idea)

        # 3. Generation de l'illustration (desactive - Imagen non disponible)
        # TODO: Integrer DALL-E ou Replicate
        illustration_prompt = self.generate_illustration_prompt(article)
        image_path = None  # self.generate_illustration(article)

        # 4. Recherche de sources web
        sources = self.research_web_sources(article)

        # Sauvegarde
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^\w\s-]', '', idea.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:50]

        article_path = output_dir / f"article_{slug}_{timestamp}.md"

        full_article = f"""---
title: {idea}
author: {self.consultant_info['name']}
company: {self.consultant_info['company']}
date: {datetime.now().strftime('%Y-%m-%d')}
illustration_prompt: |
  {illustration_prompt[:200]}
---

{article}
"""

        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(full_article)

        print(f"  Article sauvegarde : {article_path.relative_to(self.base_dir)}")

        result = {
            "article": article,
            "linkedin_post": linkedin_post,
            "illustration_prompt": illustration_prompt,
            "image_path": str(Path(image_path).relative_to(self.base_dir)) if image_path else None,
            "sources": sources,
            "article_path": str(article_path.relative_to(self.base_dir)),
            "generated_at": datetime.now().isoformat()
        }

        return result


if __name__ == "__main__":
    agent = ArticleGeneratorAgent()
    test_idea = "L'IA generative va-t-elle remplacer les data scientists ?"
    result = agent.run(test_idea, target_length="medium")
    print("\n=== ARTICLE ===")
    print(result["article"][:500] + "...")
    print("\n=== POST LINKEDIN ===")
    print(result["linkedin_post"])
