"""
Profil consultant enrichi pour generation d articles contextualises
Agrege : articles precedents, veille tech, personnalite, LinkedIn
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter
import re


class ConsultantProfile:
    """Profil enrichi du consultant pour generation contextuelle"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        else:
            base_dir = Path(base_dir)

        self.base_dir = base_dir
        self.output_dir = base_dir / "output"
        self.data_dir = base_dir / "data"

    def load_previous_articles(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Charge les derniers articles rediges

        Args:
            limit: Nombre max d articles a charger

        Returns:
            Liste d articles avec metadata et extraits
        """
        articles = []
        article_files = sorted(
            self.output_dir.glob("article_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]

        for article_path in article_files:
            try:
                with open(article_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extraire metadonnees YAML
                metadata = self._extract_yaml_metadata(content)

                # Extraire un extrait (premiers paragraphes)
                excerpt = self._extract_excerpt(content, max_chars=800)

                articles.append({
                    "path": str(article_path.name),
                    "metadata": metadata,
                    "excerpt": excerpt,
                    "full_content": content[:3000]  # Limiter pour contexte LLM
                })
            except Exception as e:
                print(f"Erreur lecture article {article_path}: {e}")
                continue

        return articles

    def load_personality(self) -> str:
        """
        Charge le fichier de personnalite/convictions du consultant

        Returns:
            Contenu du fichier personality.md ou chaine vide
        """
        personality_path = self.data_dir / "personality.md"

        if personality_path.exists():
            with open(personality_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Creer un template si absent
            default_personality = """# Personnalite et Convictions

## Vision
- L IA doit etre au service de l humain et des organisations
- Pragmatisme avant hype : focus sur ROI et valeur concrete
- Ethique et gouvernance indissociables de la tech

## Style d ecriture
- Ton expert mais accessible
- Critique constructif : challenger les idees recues
- Concret : exemples reels, chiffres, retours d experience
- Pedagogie : expliquer sans simplifier a l exces

## Convictions cles
- L IA generative n est pas magique : elle necessite strategie et gouvernance
- La data reste le petrole de l IA : sans qualite, pas de resultats
- Le consulting doit etre oriente impact, pas buzzwords

## Themes de predilection
- ROI de l IA en entreprise
- Gouvernance des donnees et de l IA
- Adoption et conduite du changement
- GenAI : usages pragmatiques vs hype
"""
            personality_path.parent.mkdir(parents=True, exist_ok=True)
            with open(personality_path, 'w', encoding='utf-8') as f:
                f.write(default_personality)

            return default_personality

    def load_linkedin_profile(self) -> Dict[str, Any]:
        """
        Charge le profil LinkedIn du consultant

        Returns:
            Dict avec bio, experiences, posts recents
        """
        linkedin_path = self.data_dir / "linkedin_profile.json"

        if linkedin_path.exists():
            with open(linkedin_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Template par defaut
            default_profile = {
                "name": os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha'),
                "title": os.getenv('CONSULTANT_TITLE', 'Consultant en strategie data et IA'),
                "company": os.getenv('COMPANY_NAME', 'Consulting Tools'),
                "bio": "Consultant specialise en strategie data et IA, avec une expertise en gouvernance des donnees, adoption de l IA generative et transformation digitale.",
                "experiences": [
                    {
                        "title": "Consultant Data & IA",
                        "company": "Consulting Tools",
                        "description": "Accompagnement des entreprises dans leur strategie data et IA"
                    }
                ],
                "recent_posts": []
            }

            linkedin_path.parent.mkdir(parents=True, exist_ok=True)
            with open(linkedin_path, 'w', encoding='utf-8') as f:
                json.dump(default_profile, f, indent=2, ensure_ascii=False)

            return default_profile

    def load_tech_trends(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Charge les tendances tech recentes depuis la veille

        Args:
            days: Articles des X derniers jours
            limit: Nombre max d articles

        Returns:
            Liste d articles de veille pertinents
        """
        try:
            from utils.article_db import ArticleDatabase
            db = ArticleDatabase()

            articles = db.get_articles(limit=limit, days=days)

            return [{
                "title": a["title"],
                "summary": a.get("summary", "")[:200],
                "source": a.get("source", ""),
                "date": a.get("date")
            } for a in articles]
        except Exception as e:
            print(f"Erreur chargement tendances veille: {e}")
            return []

    def analyze_writing_style(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse le style d ecriture a partir des articles precedents

        Args:
            articles: Liste d articles avec full_content

        Returns:
            Analyse du style (mots cles, structures, tone)
        """
        if not articles:
            return {
                "keywords": [],
                "avg_length": 0,
                "common_phrases": []
            }

        all_text = " ".join([a.get("full_content", "") for a in articles])

        # Extraire mots cles frequents (hors stop words)
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais', 'pour', 'dans', 'sur', 'avec', 'par', 'est', 'sont', 'ont', 'a', 'au'}
        words = re.findall(r'\b\w{5,}\b', all_text.lower())
        words_filtered = [w for w in words if w not in stop_words]
        word_counts = Counter(words_filtered)
        top_keywords = word_counts.most_common(15)

        # Longueur moyenne
        avg_length = len(all_text) // len(articles) if articles else 0

        return {
            "keywords": [kw for kw, count in top_keywords],
            "avg_length": avg_length,
            "num_articles_analyzed": len(articles)
        }

    def build_context(self) -> Dict[str, Any]:
        """
        Construit le contexte complet pour generation d article

        Returns:
            Dict avec tous les elements de contexte
        """
        print("  📦 Chargement du contexte consultant...")

        # 1. Articles precedents
        previous_articles = self.load_previous_articles(limit=5)
        print(f"     ✓ {len(previous_articles)} articles precedents charges")

        # 2. Personnalite
        personality = self.load_personality()
        print(f"     ✓ Personnalite chargee ({len(personality)} chars)")

        # 3. LinkedIn
        linkedin_profile = self.load_linkedin_profile()
        print(f"     ✓ Profil LinkedIn charge")

        # 4. Tendances veille
        tech_trends = self.load_tech_trends(days=30, limit=10)
        print(f"     ✓ {len(tech_trends)} tendances tech chargees")

        # 5. Analyse style
        writing_style = self.analyze_writing_style(previous_articles)
        print(f"     ✓ Style d ecriture analyse")

        return {
            "previous_articles": previous_articles,
            "personality": personality,
            "linkedin_profile": linkedin_profile,
            "tech_trends": tech_trends,
            "writing_style": writing_style
        }

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Formate le contexte pour injection dans le system prompt

        Args:
            context: Contexte complet du consultant

        Returns:
            Texte formatte pour le prompt
        """
        sections = []

        # 1. Personnalite
        if context.get("personality"):
            sections.append(f"## TA PERSONNALITE ET CONVICTIONS\n\n{context['personality'][:1000]}")

        # 2. Style d ecriture
        style = context.get("writing_style", {})
        if style.get("keywords"):
            keywords_str = ", ".join(style["keywords"][:10])
            sections.append(f"## TON VOCABULAIRE HABITUEL\n\nMots cles frequents : {keywords_str}")

        # 3. Articles precedents (extraits)
        prev_articles = context.get("previous_articles", [])
        if prev_articles:
            articles_excerpts = []
            for i, article in enumerate(prev_articles[:3], 1):
                title = article["metadata"].get("title", "Sans titre")
                excerpt = article["excerpt"][:300]
                articles_excerpts.append(f"**Article {i} : {title}**\n{excerpt}...")

            sections.append(f"## TES ARTICLES PRECEDENTS (pour reference de style)\n\n" + "\n\n".join(articles_excerpts))

        # 4. Tendances tech actuelles
        trends = context.get("tech_trends", [])
        if trends:
            trends_list = []
            for trend in trends[:8]:
                trends_list.append(f"- **{trend['title']}** ({trend['source']})")

            sections.append(f"## TENDANCES TECH ACTUELLES (issues de ta veille)\n\n" + "\n".join(trends_list))

        # 5. Profil LinkedIn
        linkedin = context.get("linkedin_profile", {})
        if linkedin.get("bio"):
            sections.append(f"## TON PROFIL LINKEDIN\n\n**Titre** : {linkedin.get('title', '')}\n**Bio** : {linkedin.get('bio', '')[:500]}")

        return "\n\n".join(sections)

    def _extract_yaml_metadata(self, content: str) -> Dict[str, Any]:
        """Extrait les metadonnees YAML du front matter"""
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}

        yaml_content = match.group(1)
        metadata = {}

        for line in yaml_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"')

                if key == 'tags':
                    try:
                        metadata[key] = eval(value)
                    except:
                        metadata[key] = []
                else:
                    metadata[key] = value

        return metadata

    def _extract_excerpt(self, content: str, max_chars: int = 800) -> str:
        """Extrait un extrait de l article (apres metadonnees et image)"""
        # Supprimer front matter YAML
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

        # Supprimer image placeholder
        content = re.sub(r'>\s*\*\*\[IMAGE PLACEHOLDER\].*?\n\n', '', content, flags=re.DOTALL)

        # Prendre premiers paragraphes
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        excerpt = ' '.join(paragraphs[:3])

        return excerpt[:max_chars]


if __name__ == "__main__":
    # Test
    profile = ConsultantProfile()
    context = profile.build_context()

    print("\n=== CONTEXTE CONSULTANT ===")
    print(f"Articles precedents : {len(context['previous_articles'])}")
    print(f"Tendances tech : {len(context['tech_trends'])}")
    print(f"Mots cles : {context['writing_style']['keywords'][:5]}")

    print("\n=== CONTEXTE FORMATTE POUR PROMPT ===")
    formatted = profile.format_context_for_prompt(context)
    print(formatted[:1000] + "...")
