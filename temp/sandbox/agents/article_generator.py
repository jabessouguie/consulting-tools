"""
Agent de generation d'articles
Prend une idee et genere un article markdown avec le style Wenvision/Jean-Sebastien
+ generation d'illustration Nano Banana + post LinkedIn + sources web
"""
import os
import sys
import re
import ast
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient
from utils.consultant_profile import ConsultantProfile


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

        # Profil consultant pour contexte enrichi
        self.profile = ConsultantProfile(base_dir=str(self.base_dir))

    def generate_article(self, idea: str, target_length: str = "medium", use_context: bool = False) -> str:
        """Genere un article markdown a partir d'une idee

        Args:
            idea: Sujet de l article
            target_length: short, medium ou long
            use_context: Utiliser le contexte enrichi (articles precedents, veille, personnalite)
        """
        print("  [1/4] Generation de l'article...")

        length_map = {
            "short": "500-800 mots",
            "medium": "1000-1500 mots",
            "long": "2000-3000 mots"
        }
        target_words = length_map.get(target_length, "1000-1500 mots")

        writing_style = self._load_writing_style()

        # Charger contexte enrichi si demande
        context_section = ""
        if use_context:
            print("     📦 Chargement du contexte enrichi...")
            context = self.profile.build_context()
            context_section = "\n\n" + self.profile.format_context_for_prompt(context) + "\n"
            print("     ✓ Contexte charge et formate")

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.

{writing_style}
{context_section}

Tu rediges des articles de blog techniques et accessibles sur l'IA, la data et la transformation digitale.

TON STYLE D'ECRITURE ET REGLES STRICTES :
- Ton expert mais accessible : tu vulgarises sans simplifier a l'exces
- Concret et pragmatique : exemples reels, cas d'usage, retours d'experience
- Critique constructif : tu poses les bonnes questions, tu challenges les idees recues
- Pedagogue : tu expliques les concepts pas a pas
- Engageant : tu interpelles le lecteur, tu poses des questions rhetoriques
- INTERDICTION GRAMMATICALE : n'utilise absolument jamais le pronom "on" (privilegie "nous", "vous" ou la voix passive)
- REGLE TYPOGRAPHIQUE : ne mets jamais de majuscule au premier mot qui suit les deux-points (:)

FORMAT ARTICLE COMPLET :

1. METADONNEES YAML (obligatoire) :
---
title: "[Titre percutant de l'article]"
author: "Jean-Sebastien ABESSOUGUIE"
universe: "[ai|data|cloud|transformation]"
cluster: "[sous-theme, ex: ia-entreprise-roi, data-governance, cloud-migration]"
type: "[focus|analyse|tutorial|opinion]"
readTime: "[X min]" (estime selon longueur)
publishDate: "{datetime.now().strftime('%Y-%m-%d')}"
description: "[Description 1-2 phrases]"
tags: ["[Tag1]", "[Tag2]", "[Tag3]"]
---

2. IMAGE PLACEHOLDER (obligatoire) :
> **[IMAGE PLACEHOLDER]**
>
> **Prompt de generation (DALL-E / Midjourney)** :
> [Genere ici un prompt detaille pour creer une illustration premium et cinematique adaptee au theme de l article. Style : Unreal Engine 5, corporate tech, palette bleu froid + ambre/or, format 1792x1024 (paysage)]
>
> **Dimensions recommandees** : 1792x1024px (format paysage pour blog header)

3. STRUCTURE ARTICLE (CONCLUSION INVERSEE) :
- Titre accrocheur (H1)
- Chapeau et elements de conclusion : livre d emblee les conclusions de l article et les messages cles a retenir en 2 ou 3 phrases
- Introduction (contexte + problematique)
- Developpement en 3-4 sections (H2) avec sous-sections (H3) si besoin
- Exemples concrets et cas d usage
- Points de vigilance / pieges a eviter
- Ouverture finale ou call-to-action (puisque la conclusion est au debut)

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
- Livrer les conclusions et les takeaways des le debut de l article
- Respecter strictement l interdiction d utiliser le pronom on
- Respecter strictement l absence de majuscule apres les deux-points (:)
- Se terminer par une ouverture engageante

IMPORTANT : Commence l article par les metadonnees YAML, puis l image placeholder **![][image1]**, puis le contenu.

Retourne l article complet avec metadonnees en markdown, sans preambule."""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Nettoyer markdown fences si presentes
        result = result.strip()
        if result.startswith('```markdown'):
            result = result[len('```markdown'):]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]
        result = result.strip()

        return result

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
                return f"STYLE D ECRITURE SPECIFIQUE :\n{f.read()}"
        return ""

    def _extract_metadata(self, markdown_text: str) -> Dict[str, Any]:
        """Extrait les metadonnees YAML du front matter"""
        import re

        # Chercher le bloc YAML
        match = re.search(r'^---\n(.*?)\n---', markdown_text, re.DOTALL)
        if not match:
            return {}

        yaml_content = match.group(1)
        metadata = {}

        # Parser manuellement (eviter dependance PyYAML)
        for line in yaml_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"')

                # Tags = liste
                if key == 'tags':
                    try:
                        metadata[key] = ast.literal_eval(value)  # Liste Python - SAFE
                    except (ValueError, SyntaxError):
                        metadata[key] = []
                else:
                    metadata[key] = value

        return metadata

    def generate_illustration_prompt(self, article: str) -> str:
        """Genere un prompt DALL-E/Midjourney ready base sur l article"""

        # Extraire le titre et les concepts cles de l article
        system_prompt = """Tu es un expert en generation de prompts pour DALL-E et Midjourney.
Ton role est de creer un prompt concis et efficace pour generer une illustration premium."""

        user_prompt = f"""Extrait de l article :
{article[:1500]}

Genere un prompt DALL-E/Midjourney (max 300 caracteres) pour une illustration premium de blog tech.

CONTRAINTES :
- Style : Unreal Engine 5 render, corporate tech aesthetic, isometric or wide-angle
- Palette : Cool electric blues + warm amber/gold accents
- Mood : Sophisticated, futuristic but grounded, professional
- Format : Wide landscape 16:9, suitable for blog header
- Contenu : Represente le concept central de l article de maniere metaphorique (PAS literal)

Retourne UNIQUEMENT le prompt, sans explication."""

        try:
            prompt = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            return prompt.strip().strip('"')
        except Exception as e:
            # Fallback : prompt generique
            return "A premium cinematic illustration for a tech consulting blog post. Unreal Engine 5 render, isometric view, 8k quality. Corporate tech aesthetic with cool electric blues and warm amber/gold accents. Sophisticated, futuristic but grounded mood. Wide landscape format, 16:9."

    def run(self, idea: str, target_length: str = "medium", use_context: bool = False) -> Dict[str, Any]:
        """Pipeline complet : article + LinkedIn post + image + sources

        Args:
            idea: Sujet de l article
            target_length: short, medium ou long
            use_context: Utiliser le contexte enrichi (articles precedents, veille, personnalite)
        """
        print(f"\n  GENERATION D'ARTICLE")
        print(f"  Idee : {idea[:100]}...")
        if use_context:
            print(f"  Mode : Contexte enrichi active 🎯")

        # 1. Generation de l article
        article = self.generate_article(idea, target_length, use_context=use_context)

        # Extraire les metadonnees du front matter
        metadata = self._extract_metadata(article)

        # Generer le prompt d image detaille
        illustration_prompt = self.generate_illustration_prompt(article)

        # Remplacer le placeholder generique par le prompt detaille
        placeholder_pattern = r'\[Genere ici un prompt detaille.*?\]'
        import re
        article = re.sub(
            placeholder_pattern,
            illustration_prompt.replace('\n', ' ').strip(),
            article,
            flags=re.DOTALL
        )

        # 2. Generation du post LinkedIn
        linkedin_post = self.generate_linkedin_post(article, article_title=idea)

        # 3. Recherche de sources web
        sources = self.research_web_sources(article)

        # Sauvegarde
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^\w\s-]', '', idea.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:50]

        article_path = output_dir / f"article_{slug}_{timestamp}.md"

        # L article contient deja les metadonnees YAML generees par le LLM
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(article)

        print(f"  Article sauvegarde : {article_path.relative_to(self.base_dir)}")

        result = {
            "article": article,
            "metadata": metadata,
            "linkedin_post": linkedin_post,
            "illustration_prompt": illustration_prompt,
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
