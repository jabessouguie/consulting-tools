"""
Agent de veille technologique automatisée
Collecte et analyse des articles tech pour générer un digest périodique
"""
import os
import sys
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import feedparser
import requests
from bs4 import BeautifulSoup
import html2text

from utils.llm_client import LLMClient
from utils.article_db import ArticleDatabase
from config import get_consultant_info


class TechMonitorAgent:
    """Agent de veille technologique pour consultants data/IA"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.body_width = 0

        # Base de données des articles
        self.db = ArticleDatabase()

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()

        # Sources RSS par défaut (thématiques data/IA)
        self.default_sources = [
            'https://www.kdnuggets.com/feed',  # Data Science
            'https://machinelearningmastery.com/feed/',  # ML
            'https://www.datanami.com/feed/',  # Big Data
            'https://hai.stanford.edu/news/rss.xml',  # Stanford AI
            'https://openai.com/blog/rss/',  # OpenAI
            'https://www.deeplearning.ai/blog/rss/',  # DeepLearning.AI
        ]

    def collect_articles(
        self,
        sources: List[str] = None,
        keywords: List[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Collecte des articles depuis des flux RSS

        Args:
            sources: Liste d'URLs RSS (utilise default_sources si None)
            keywords: Filtrer par mots-clés (None = tous les articles)
            days: Articles des X derniers jours

        Returns:
            Liste d'articles avec titre, lien, date, résumé
        """
        if sources is None:
            sources = self.default_sources

        print(f"📰 Collecte des articles depuis {len(sources)} sources...")

        cutoff_date = datetime.now() - timedelta(days=days)
        articles = []

        for source_url in sources:
            try:
                print(f"   🔍 {source_url}")
                feed = feedparser.parse(source_url)

                for entry in feed.entries:
                    # Parser la date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])

                    # Filtrer par date
                    if pub_date and pub_date < cutoff_date:
                        continue

                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    link = entry.get('link', '')

                    # Filtrer par mots-clés si spécifié
                    if keywords:
                        text = (title + ' ' + summary).lower()
                        if not any(kw.lower() in text for kw in keywords):
                            continue

                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': BeautifulSoup(summary, 'html.parser').get_text()[:500],
                        'date': pub_date.isoformat() if pub_date else None,
                        'source': feed.feed.get('title', source_url),
                    })

            except Exception as e:
                print(f"   ⚠️  Erreur sur {source_url}: {str(e)}")
                continue

        print(f"   ✅ {len(articles)} articles collectés")

        # Sauvegarder dans la base de données
        if articles:
            saved_count = self.db.save_articles(articles)
            print(f"   💾 {saved_count} nouveaux articles sauvegardés en BDD")

        return articles

    def analyze_trends(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse les tendances à partir des articles collectés

        Args:
            articles: Liste d'articles

        Returns:
            Tendances identifiées (mots-clés fréquents, thèmes)
        """
        print("🔍 Analyse des tendances...")

        # Extraire les mots-clés des titres
        all_words = []
        for article in articles:
            title = article['title'].lower()
            # Mots simples
            words = [w.strip('.,!?()[]') for w in title.split() if len(w) > 4]
            all_words.extend(words)

        # Compter les occurrences
        word_counts = Counter(all_words)
        top_keywords = word_counts.most_common(10)

        print(f"   ✅ Tendances identifiées")

        return {
            'top_keywords': top_keywords,
            'num_articles': len(articles),
            'sources_count': len(set(a['source'] for a in articles)),
        }

    def generate_digest(
        self,
        articles: List[Dict[str, Any]],
        trends: Dict[str, Any],
        period: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Génère un digest de veille technologique

        Args:
            articles: Articles collectés
            trends: Tendances analysées
            period: "weekly" ou "monthly"

        Returns:
            Digest formaté
        """
        print(f"✍️  Génération du digest {period}...")

        # Trier par date (plus récents d'abord)
        sorted_articles = sorted(
            articles,
            key=lambda x: x['date'] or '',
            reverse=True
        )

        # Limiter à 20 articles max pour le contexte LLM
        top_articles = sorted_articles[:20]

        period_label = "hebdomadaire" if period == "weekly" else "mensuel"

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Tu produis une veille technologique {period_label} pour les consultants data/IA."""

        # Préparer le contexte des articles
        articles_context = "\n\n".join([
            f"**{i+1}. {a['title']}**\n{a['summary'][:200]}...\nSource: {a['source']}\nLien: {a['link']}"
            for i, a in enumerate(top_articles)
        ])

        prompt = f"""Génère un digest de veille technologique {period_label} à partir de ces articles.

ARTICLES COLLECTÉS ({len(articles)} au total, voici les {len(top_articles)} plus récents):

{articles_context}

TENDANCES (mots-clés fréquents):
{', '.join([f'{word} ({count})' for word, count in trends['top_keywords'][:8]])}

---

Le digest doit contenir:

# 📊 Veille Tech {period_label.capitalize()} - Data & IA

## 🎯 Tendances principales

[2-3 tendances majeures observées cette période, avec explications courtes]

## 📰 Articles clés

[5-8 articles les plus pertinents avec :
- Titre et lien
- Résumé en 2-3 phrases
- Pourquoi c'est important pour un consultant data/IA]

## 💡 Insights & Recommandations

[3-4 insights actionnables :
- Ce qu'on retient
- Comment ça impacte nos missions
- Ce qu'on devrait surveiller]

## 🔗 Toutes les sources

[Liste compacte des {len(articles)} articles avec titres + liens]

---

Ton : professionnel mais accessible. Focus sur l'actionnable pour les consultants.
Format : Markdown avec emojis."""

        digest = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=3000,
        )

        print("   ✅ Digest généré")

        return {
            'content': digest,
            'period': period,
            'num_articles': len(articles),
            'generated_at': datetime.now().isoformat(),
        }

    def run(
        self,
        sources: List[str] = None,
        keywords: List[str] = None,
        days: int = 7,
        period: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Pipeline complet: collecte -> analyse -> digest

        Args:
            sources: URLs RSS (None = sources par défaut)
            keywords: Filtrer par mots-clés
            days: Articles des X derniers jours
            period: "weekly" ou "monthly"

        Returns:
            Résultat complet
        """
        print(f"\n{'='*50}")
        print(f"📡 VEILLE TECHNOLOGIQUE - {period.upper()}")
        print(f"{'='*50}\n")

        articles = self.collect_articles(sources=sources, keywords=keywords, days=days)

        if not articles:
            print("⚠️  Aucun article collecté")
            return {
                'digest': "# ⚠️ Aucun article trouvé\n\nAucun article correspondant aux critères n'a été trouvé pour cette période.",
                'num_articles': 0,
                'articles': [],
            }

        trends = self.analyze_trends(articles)
        result = self.generate_digest(articles, trends, period=period)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, f"tech_digest_{period}_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Veille Technologique {period.capitalize()}\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"**Période:** {days} derniers jours\n")
            f.write(f"**Articles:** {len(articles)}\n\n")
            f.write("---\n\n")
            f.write(result['content'])

        # Sauvegarder le digest dans la base de données
        digest_id = self.db.save_digest(
            period=period,
            content=result['content'],
            num_articles=len(articles),
            file_path=md_path
        )

        result['md_path'] = md_path
        result['digest_id'] = digest_id
        result['articles'] = articles[:10]  # Limiter pour la réponse

        print(f"\n✅ Digest sauvegardé: {md_path}")
        print(f"   💾 Digest sauvegardé en BDD (ID: {digest_id})")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Veille technologique automatisée')
    parser.add_argument('--keywords', nargs='+', help='Mots-clés à filtrer (ex: GPT, transformer, RAG)')
    parser.add_argument('--days', type=int, default=7, help='Articles des X derniers jours (défaut: 7)')
    parser.add_argument('--period', choices=['weekly', 'monthly'], default='weekly')

    args = parser.parse_args()

    agent = TechMonitorAgent()
    result = agent.run(keywords=args.keywords, days=args.days, period=args.period)

    print(f"\n{'='*50}")
    print("DIGEST GÉNÉRÉ")
    print(f"{'='*50}\n")
    print(result['content'][:1000] + "...")
    print(f"\n📊 {result['num_articles']} articles analysés")


if __name__ == '__main__':
    main()
