"""
Utilitaires pour la veille technologique multi-sources
"""
import os
import feedparser
import requests
from bs4 import BeautifulSoup
import html2text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from urllib.parse import quote_plus
import re


class MonitoringTool:
    """Outil de veille multi-sources"""

    def __init__(self):
        """Initialise l'outil de veille"""
        self.keywords = os.getenv('VEILLE_KEYWORDS', '').split(',')
        self.keywords = [k.strip() for k in self.keywords if k.strip()]

    def fetch_rss_feeds(self, feed_urls: List[str], download_content: bool = True) -> List[Dict[str, Any]]:
        """
        Récupère les articles depuis des flux RSS

        Args:
            feed_urls: Liste des URLs de flux RSS
            download_content: Télécharger le contenu complet des articles (défaut: True)

        Returns:
            Liste des articles
        """
        articles = []

        for feed_url in feed_urls:
            try:
                print(f"📡 Récupération du flux RSS: {feed_url}")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:10]:  # Limiter à 10 articles par feed
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', entry.get('description', '')),
                        'published': entry.get('published', entry.get('updated', '')),
                        'source': feed.feed.get('title', feed_url),
                        'source_type': 'rss'
                    }

                    # Nettoyer le HTML dans le résumé
                    if article['summary']:
                        soup = BeautifulSoup(article['summary'], 'html.parser')
                        article['summary'] = soup.get_text().strip()

                    # Télécharger le contenu complet si demandé
                    if download_content and article['link']:
                        print(f"   📥 Téléchargement: {article['title'][:50]}...")
                        full_content = self.download_article_content(article['link'])
                        if full_content:
                            article['full_content'] = full_content

                    articles.append(article)

            except Exception as e:
                print(f"⚠️  Erreur lors de la récupération de {feed_url}: {e}")

        return articles

    def web_search(self, keywords: List[str], days_back: int = 7, download_content: bool = True) -> List[Dict[str, Any]]:
        """
        Effectue une recherche web sur des mots-clés

        Args:
            keywords: Liste de mots-clés
            days_back: Nombre de jours en arrière
            download_content: Télécharger le contenu complet des articles (défaut: True)

        Returns:
            Liste de résultats
        """
        results = []

        # Note: Cette fonction utilise DuckDuckGo pour éviter les API payantes
        # Pour une solution production, considérer Google Custom Search API ou Bing API

        for keyword in keywords:
            try:
                print(f"🔎 Recherche web: {keyword}")

                # Utiliser DuckDuckGo HTML (pas d'API key nécessaire)
                query = quote_plus(f"{keyword} {datetime.now().year}")
                url = f"https://html.duckduckgo.com/html/?q={query}"

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }

                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Parser les résultats
                    for result in soup.find_all('div', class_='result')[:5]:  # Top 5 résultats
                        title_elem = result.find('a', class_='result__a')
                        snippet_elem = result.find('a', class_='result__snippet')

                        if title_elem:
                            article = {
                                'title': title_elem.get_text().strip(),
                                'link': title_elem.get('href', ''),
                                'summary': snippet_elem.get_text().strip() if snippet_elem else '',
                                'keyword': keyword,
                                'source_type': 'web_search',
                                'published': datetime.now().isoformat()
                            }

                            # Télécharger le contenu complet si demandé
                            if download_content and article['link']:
                                print(f"   📥 Téléchargement: {article['title'][:50]}...")
                                full_content = self.download_article_content(article['link'])
                                if full_content:
                                    article['full_content'] = full_content

                            results.append(article)

            except Exception as e:
                print(f"⚠️  Erreur lors de la recherche de '{keyword}': {e}")

        return results

    def download_article_content(self, url: str, max_chars: int = 3000) -> str:
        """
        Telecharge et extrait le contenu textuel d'un article web

        Args:
            url: URL de l'article
            max_chars: Nombre max de caracteres a extraire

        Returns:
            Contenu textuel de l'article
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Chercher le corps de l'article
            article_body = None
            for selector in ['article', '.post-content', '.article-content',
                             '.entry-content', 'main', '.content', '#content',
                             '.blog-post', '.post-body']:
                article_body = soup.select_one(selector)
                if article_body:
                    break

            if not article_body:
                article_body = soup.find('body')

            if article_body:
                for tag in article_body.find_all(['script', 'style', 'nav',
                                                   'footer', 'header', 'aside',
                                                   'form', 'iframe']):
                    tag.decompose()

            converter = html2text.HTML2Text()
            converter.ignore_links = True
            converter.ignore_images = True
            converter.body_width = 0

            raw_html = str(article_body) if article_body else ''
            text = converter.handle(raw_html).strip()

            return text[:max_chars]

        except Exception as e:
            print(f"      ⚠️  Impossible de telecharger {url}: {e}")
            return ''

    def fetch_linkedin_posts(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère des posts LinkedIn (nécessite authentification)

        Note: Cette fonction nécessite soit:
        - Les cookies de session LinkedIn
        - L'API LinkedIn (limitée)
        - Une alternative comme Phantombuster

        Args:
            keywords: Mots-clés à surveiller
            limit: Nombre de posts maximum

        Returns:
            Liste de posts
        """
        # Note: Implémentation simplifiée
        # Pour une solution production, utiliser linkedin-api ou un scraper

        print("ℹ️  Récupération de posts LinkedIn (nécessite configuration)")
        print("   Voir documentation pour configurer l'accès LinkedIn")

        return []

    def analyze_article_relevance(
        self,
        article: Dict[str, Any],
        keywords: List[str]
    ) -> float:
        """
        Calcule un score de pertinence pour un article

        Args:
            article: Article à analyser
            keywords: Mots-clés de référence

        Returns:
            Score de pertinence (0-1)
        """
        score = 0.0
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

        # Vérifier la présence de mots-clés
        for keyword in keywords:
            if keyword.lower() in text:
                score += 0.3

        # Bonus pour les sources connues
        trusted_sources = ['techcrunch', 'medium', 'towardsdatascience', 'openai', 'anthropic']
        source = article.get('source', '').lower()
        if any(ts in source for ts in trusted_sources):
            score += 0.2

        # Pénalité pour les articles anciens
        try:
            published = article.get('published', '')
            if published:
                # Tenter de parser la date
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                days_old = (datetime.now() - pub_date.replace(tzinfo=None)).days
                if days_old > 7:
                    score *= 0.8
        except:
            pass

        return min(score, 1.0)

    def filter_and_rank_articles(
        self,
        articles: List[Dict[str, Any]],
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Filtre et classe les articles par pertinence

        Args:
            articles: Liste d'articles
            min_score: Score minimum de pertinence

        Returns:
            Articles filtrés et classés
        """
        # Calculer les scores
        for article in articles:
            article['relevance_score'] = self.analyze_article_relevance(
                article,
                self.keywords
            )

        # Filtrer et trier
        filtered = [a for a in articles if a['relevance_score'] >= min_score]
        filtered.sort(key=lambda x: x['relevance_score'], reverse=True)

        return filtered

    def collect_all_sources(
        self,
        rss_feeds: Optional[List[str]] = None,
        search_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Collecte les informations de toutes les sources

        Args:
            rss_feeds: Liste de flux RSS
            search_keywords: Mots-clés pour la recherche web

        Returns:
            Dictionnaire avec tous les articles collectés
        """
        print("\n🌐 COLLECTE DE VEILLE MULTI-SOURCES\n")

        all_articles = []

        # RSS (sans téléchargement initial - on télécharge après filtrage)
        if rss_feeds:
            rss_articles = self.fetch_rss_feeds(rss_feeds, download_content=False)
            all_articles.extend(rss_articles)
            print(f"✅ RSS: {len(rss_articles)} articles collectés")

        # Recherche web (sans téléchargement initial - on télécharge après filtrage)
        if search_keywords:
            web_articles = self.web_search(search_keywords or self.keywords, download_content=False)
            all_articles.extend(web_articles)
            print(f"✅ Web: {len(web_articles)} articles collectés")

        # LinkedIn (placeholder)
        # linkedin_posts = self.fetch_linkedin_posts(search_keywords or self.keywords)
        # all_articles.extend(linkedin_posts)

        # Filtrer et classer
        ranked_articles = self.filter_and_rank_articles(all_articles)

        # Telecharger le contenu complet des top articles
        print(f"\n📥 Telechargement du contenu des articles les plus pertinents...")
        downloaded = 0
        for article in ranked_articles[:10]:
            link = article.get('link', '')
            if link:
                content = self.download_article_content(link)
                if content:
                    article['full_content'] = content
                    downloaded += 1
        print(f"   ✅ {downloaded} articles telecharges")

        print(f"\n📊 Total: {len(all_articles)} articles collectés")
        print(f"   📌 {len(ranked_articles)} articles pertinents après filtrage\n")

        return {
            'articles': ranked_articles,
            'total_collected': len(all_articles),
            'total_relevant': len(ranked_articles),
            'collected_at': datetime.now().isoformat(),
            'keywords': search_keywords or self.keywords
        }

    def save_monitoring_results(
        self,
        results: Dict[str, Any],
        output_path: str = None
    ):
        """
        Sauvegarde les résultats de veille

        Args:
            results: Résultats de la veille
            output_path: Chemin de sortie
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"data/monitoring/veille_{timestamp}.json"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"💾 Résultats sauvegardés: {output_path}")


def extract_key_insights(articles: List[Dict[str, Any]], top_n: int = 5) -> List[str]:
    """
    Extrait les insights clés des articles

    Args:
        articles: Liste d'articles
        top_n: Nombre d'articles à analyser

    Returns:
        Liste d'insights
    """
    insights = []

    for article in articles[:top_n]:
        insight = f"📰 {article.get('title')}\n   {article.get('summary', '')[:200]}...\n   🔗 {article.get('link')}"
        insights.append(insight)

    return insights
