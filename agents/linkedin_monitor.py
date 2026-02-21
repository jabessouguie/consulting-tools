"""
Agent de veille et génération de posts LinkedIn
Collecte des informations depuis diverses sources et génère des posts LinkedIn engageants
"""
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.monitoring import MonitoringTool, extract_key_insights
from utils.llm_client import LLMClient
from config import get_consultant_info


class LinkedInMonitorAgent:
    """Agent pour la veille et génération de posts LinkedIn"""

    def __init__(self):
        """Initialise l'agent"""
        self.monitoring = MonitoringTool()
        self.llm_client = LLMClient()

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()
        # Ajouter expertise (specifique a cet agent)
        self.consultant_info['expertise'] = [
            'Intelligence Artificielle',
            'Data Science',
            'GenAI',
            'Stratégie Data',
            'Cloud (Azure, AWS)',
            'MLOps'
        ]

        # Configuration veille
        self.rss_feeds = os.getenv('RSS_FEEDS', '').split(',')
        self.rss_feeds = [f.strip() for f in self.rss_feeds if f.strip()]

        self.keywords = os.getenv('VEILLE_KEYWORDS', 'IA,Data,GenAI,ML').split(',')
        self.keywords = [k.strip() for k in self.keywords if k.strip()]

    def collect_monitoring_data(self) -> Dict[str, Any]:
        """
        Collecte les données de veille depuis toutes les sources

        Returns:
            Données de veille collectées
        """
        print(f"\n{'='*60}")
        print("🔍 COLLECTE DE VEILLE TECHNOLOGIQUE")
        print(f"{'='*60}\n")

        # Configurer les feeds par défaut si nécessaire
        default_feeds = [
            'https://feeds.feedburner.com/blogspot/gJZg',  # AI Google Blog
            'https://openai.com/blog/rss.xml',  # OpenAI Blog
            'https://www.anthropic.com/news/rss.xml',  # Anthropic Blog
            'https://aws.amazon.com/blogs/machine-learning/feed/',  # AWS ML Blog
            'https://azure.microsoft.com/en-us/blog/feed/',  # Azure Blog
        ]

        feeds_to_use = self.rss_feeds if self.rss_feeds else default_feeds

        # Collecter
        results = self.monitoring.collect_all_sources(
            rss_feeds=feeds_to_use,
            search_keywords=self.keywords
        )

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/monitoring/veille_{timestamp}.json"
        self.monitoring.save_monitoring_results(results, output_path)

        return results

    def analyze_trends(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse les tendances depuis les articles collectés

        Args:
            articles: Liste d'articles

        Returns:
            Analyse des tendances
        """
        print("\n📊 Analyse des tendances...")

        # Préparer le contexte pour l'analyse
        articles_summary = []
        for i, article in enumerate(articles[:10], 1):
            full_content = article.get('full_content', '')
            if full_content:
                articles_summary.append(
                    f"{i}. {article.get('title')}\n"
                    f"   Source: {article.get('source')}\n"
                    f"   Contenu: {full_content[:500]}"
                )
            else:
                articles_summary.append(
                    f"{i}. {article.get('title')}\n"
                    f"   Source: {article.get('source')}\n"
                    f"   Résumé: {article.get('summary', '')[:200]}..."
                )

        context = "\n\n".join(articles_summary)

        prompt = f"""Analyse ces articles récents du domaine IA/Data et identifie les tendances clés:

{context}

Identifie:
1. Les 3 tendances principales émergentes
2. Les technologies/concepts les plus mentionnés
3. Les enjeux business associés
4. Les opportunités pour un consultant en stratégie data et IA

Format ta réponse de manière structurée."""

        analysis = self.llm_client.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=2000
        )

        print("✅ Analyse des tendances terminée")

        return {
            'analysis': analysis,
            'articles_analyzed': len(articles),
            'analyzed_at': datetime.now().isoformat()
        }

    def generate_linkedin_post(
        self,
        trends_analysis: Dict[str, Any],
        top_articles: List[Dict[str, Any]],
        post_type: str = "insight"
    ) -> Dict[str, Any]:
        """
        Génère un post LinkedIn basé sur la veille

        Args:
            trends_analysis: Analyse des tendances
            top_articles: Articles les plus pertinents
            post_type: Type de post (insight, curation, opinion)

        Returns:
            Post LinkedIn généré
        """
        print("\n✍️  Génération du post LinkedIn...")

        # Contexte articles (avec contenu complet si disponible)
        articles_context = []
        for i, article in enumerate(top_articles[:3], 1):
            full_content = article.get('full_content', '')
            if full_content:
                articles_context.append(
                    f"Article {i}: {article.get('title')}\n"
                    f"Lien: {article.get('link')}\n"
                    f"Contenu:\n{full_content[:2000]}"
                )
            else:
                articles_context.append(
                    f"Article {i}: {article.get('title')}\n"
                    f"Lien: {article.get('link')}\n"
                    f"Résumé: {article.get('summary', '')[:300]}"
                )

        # Charger le persona depuis le fichier
        persona_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "linkedin_persona.md")
        persona_style = ""
        if os.path.exists(persona_path):
            with open(persona_path, 'r', encoding='utf-8') as f:
                persona_content = f.read()
                # Extraire les sections pertinentes (Ton & Style, Structure, Expressions)
                persona_style = "\n\nSTYLE 'PARISIEN GENZ' A APPLIQUER:\n" + persona_content[persona_content.find("### ✨ Ton & Style"):persona_content.find("### 🎨 Thématiques favorites")]

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Base : Paris | Génération Z assumée

Ton expertise: {', '.join(self.consultant_info['expertise'])}
{persona_style}

Tu dois créer des posts LinkedIn qui:
- Apportent de la valeur et des insights concrets
- Sont authentiques et reflètent ton expertise
- Engagent la conversation
- Sont bien structurés et lisibles
- Incluent des émojis pertinents (mais avec modération)
- Font environ 1200-1500 caractères
- Se terminent par un call-to-action sous forme de question

REGLES IMPERATIVES:
- Ne JAMAIS inventer d'anecdotes, d'exemples fictifs ou d'experiences personnelles
- Ne JAMAIS fabriquer de chiffres, statistiques ou citations
- Chaque affirmation doit etre tracable a un article source fourni
- Si tu donnes un exemple, il doit provenir des articles fournis
- Ta "perspective" = ton analyse des faits, PAS une histoire inventee"""

        post_types_prompts = {
            "insight": "Partage un insight ou une analyse personnelle sur une tendance",
            "curation": "Partage et commente des ressources pertinentes",
            "opinion": "Partage ton point de vue sur un sujet d'actualité"
        }

        prompt = f"""Crée un post LinkedIn de type '{post_type}' basé sur cette veille:

ANALYSE DES TENDANCES:
{trends_analysis.get('analysis')}

ARTICLES SOURCES:
{chr(10).join(articles_context)}

Objectif: {post_types_prompts.get(post_type, post_types_prompts['insight'])}

Le post doit:
1. Commencer par un hook accrocheur
2. Développer un point clé avec ta perspective
3. Donner des implications business concretes TIREES DES ARTICLES (pas d'exemples inventes)
4. Se terminer par une question pour engager la discussion
5. Inclure des hashtags pertinents (3-5 max)

Structure recommandée:
- Hook (1 ligne percutante)
- Contexte (2-3 phrases)
- Insight principal (développement)
- Implication/Action (que faut-il retenir ?)
- Question d'engagement
- Hashtags

Important:
- Le post doit sonner naturel et authentique, pas marketing.
- Base-toi UNIQUEMENT sur les articles fournis. Ne fabrique aucun fait, chiffre ou exemple."""

        post_content = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=2000
        )

        # Générer aussi des variantes
        print("   Génération de variantes...")

        variation_prompt = f"""Génère 2 variantes courtes (500-800 caractères) du post suivant, avec des angles différents:

{post_content}

Variante 1: Plus direct et actionable
Variante 2: Reformulation synthetique et analytique

IMPORTANT: Ne PAS inventer d'anecdotes ou d'exemples fictifs. Reste factuel."""

        variations = self.llm_client.generate(
            prompt=variation_prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=1500
        )

        print("✅ Post LinkedIn généré avec variantes")

        return {
            'main_post': post_content,
            'variations': variations,
            'post_type': post_type,
            'source_articles': [
                {
                    'title': a.get('title'),
                    'link': a.get('link'),
                    'source': a.get('source')
                }
                for a in top_articles[:3]
            ],
            'generated_at': datetime.now().isoformat(),
            'consultant': self.consultant_info
        }

    def generate_multiple_posts(
        self,
        trends_analysis: Dict[str, Any],
        top_articles: List[Dict[str, Any]],
        num_posts: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Génère plusieurs posts LinkedIn de types différents

        Args:
            trends_analysis: Analyse des tendances
            top_articles: Articles pertinents
            num_posts: Nombre de posts à générer

        Returns:
            Liste de posts générés
        """
        post_types = ["insight", "curation", "opinion"]
        posts = []

        for i in range(min(num_posts, len(post_types))):
            post = self.generate_linkedin_post(
                trends_analysis,
                top_articles,
                post_type=post_types[i]
            )
            posts.append(post)

        return posts

    def run_monitoring_cycle(
        self,
        generate_posts: bool = True,
        num_posts: int = 3
    ) -> Dict[str, Any]:
        """
        Execute un cycle complet de veille et génération de posts

        Args:
            generate_posts: Générer des posts LinkedIn
            num_posts: Nombre de posts à générer

        Returns:
            Résultats complets du cycle
        """
        print(f"\n{'='*60}")
        print("🚀 CYCLE DE VEILLE ET GÉNÉRATION LINKEDIN")
        print(f"{'='*60}\n")

        # 1. Collecter les données
        monitoring_data = self.collect_monitoring_data()

        # 2. Analyser les tendances
        trends = self.analyze_trends(monitoring_data['articles'])

        # 3. Générer les posts si demandé
        posts = []
        if generate_posts and monitoring_data['articles']:
            posts = self.generate_multiple_posts(
                trends,
                monitoring_data['articles'],
                num_posts=num_posts
            )

        # 4. Préparer le résultat complet
        result = {
            'monitoring_data': monitoring_data,
            'trends_analysis': trends,
            'generated_posts': posts,
            'cycle_completed_at': datetime.now().isoformat()
        }

        # 5. Sauvegarder les résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/linkedin_cycle_{timestamp}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Sauvegarder les posts en markdown
        if posts:
            for i, post in enumerate(posts, 1):
                md_path = f"output/linkedin_post_{timestamp}_{i}.md"
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Post LinkedIn - {post['post_type'].title()}\n\n")
                    f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                    f.write(f"**Type:** {post['post_type']}\n\n")
                    f.write("## Post Principal\n\n")
                    f.write(post['main_post'])
                    f.write("\n\n---\n\n## Variantes\n\n")
                    f.write(post['variations'])
                    f.write("\n\n---\n\n## Sources\n\n")
                    for article in post['source_articles']:
                        f.write(f"- [{article['title']}]({article['link']})\n")

        print(f"\n✅ Cycle terminé avec succès!")
        print(f"   📊 {monitoring_data['total_relevant']} articles pertinents analysés")
        print(f"   📝 {len(posts)} posts LinkedIn générés")
        print(f"   💾 Résultats: {output_path}")
        print(f"\n{'='*60}\n")

        return result


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Agent de veille et génération de posts LinkedIn'
    )
    parser.add_argument(
        '--no-posts',
        action='store_true',
        help='Ne pas générer de posts, seulement collecter la veille'
    )
    parser.add_argument(
        '--num-posts',
        type=int,
        default=3,
        help='Nombre de posts à générer (défaut: 3)'
    )
    parser.add_argument(
        '--post-type',
        choices=['insight', 'curation', 'opinion'],
        help='Générer un seul post d\'un type spécifique'
    )

    args = parser.parse_args()

    # Créer l'agent
    agent = LinkedInMonitorAgent()

    if args.post_type:
        # Générer un seul post d'un type spécifique
        monitoring_data = agent.collect_monitoring_data()
        trends = agent.analyze_trends(monitoring_data['articles'])
        post = agent.generate_linkedin_post(
            trends,
            monitoring_data['articles'],
            post_type=args.post_type
        )
        print(f"\n{'='*60}")
        print(f"POST GÉNÉRÉ ({args.post_type.upper()})")
        print(f"{'='*60}\n")
        print(post['main_post'])
    else:
        # Cycle complet
        agent.run_monitoring_cycle(
            generate_posts=not args.no_posts,
            num_posts=args.num_posts
        )


if __name__ == '__main__':
    main()
