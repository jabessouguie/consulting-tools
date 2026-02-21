"""
Agent de generation de posts LinkedIn a partir d'un article web
Fetch un article, l'analyse et genere un post LinkedIn engageant pour le partager
"""
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import requests
from bs4 import BeautifulSoup
import html2text

from utils.llm_client import LLMClient
from config import get_consultant_info


class ArticleToPostAgent:
    """Agent qui genere un post LinkedIn a partir d'un lien vers un article"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.body_width = 0

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()

    def fetch_article(self, url: str) -> Dict[str, Any]:
        """
        Recupere et extrait le contenu d'un article web

        Args:
            url: URL de l'article

        Returns:
            Dictionnaire avec titre, contenu, meta
        """
        print(f"🌐 Recuperation de l'article: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraire le titre
        title = ''
        if soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.find('title'):
            title = soup.find('title').get_text(strip=True)

        # Extraire la meta description
        meta_desc = ''
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            meta_desc = meta.get('content', '')

        # Extraire le contenu principal
        # Essayer plusieurs selecteurs courants pour le corps de l'article
        article_body = None
        for selector in ['article', '.post-content', '.article-content',
                         '.entry-content', 'main', '.content', '#content',
                         '.blog-post', '.post-body']:
            article_body = soup.select_one(selector)
            if article_body:
                break

        if not article_body:
            article_body = soup.find('body')

        # Supprimer les elements non pertinents
        if article_body:
            for tag in article_body.find_all(['script', 'style', 'nav',
                                               'footer', 'header', 'aside',
                                               'form', 'iframe']):
                tag.decompose()

        raw_html = str(article_body) if article_body else str(soup)
        text_content = self.html_converter.handle(raw_html)

        # Limiter la longueur pour le LLM
        text_content = text_content[:6000]

        print(f"   ✅ Article recupere: {title[:80]}")

        return {
            'url': url,
            'title': title,
            'meta_description': meta_desc,
            'content': text_content,
            'fetched_at': datetime.now().isoformat(),
        }

    def generate_post(
        self,
        article: Dict[str, Any],
        tone: str = "expert",
        include_emoji: bool = True,
    ) -> Dict[str, Any]:
        """
        Genere un post LinkedIn a partir du contenu de l'article

        Args:
            article: Donnees de l'article (sortie de fetch_article)
            tone: Ton du post (expert, casual, provocateur)
            include_emoji: Inclure des emojis

        Returns:
            Dictionnaire avec le post et les variantes
        """
        print("✍️  Generation du post LinkedIn...")

        tone_instructions = {
            "expert": "Ton professionnel et analytique. Tu apportes ta perspective d'expert avec des insights concrets.",
            "casual": "Ton decontracte et accessible. Tu partages une decouverte de maniere conversationnelle.",
            "provocateur": "Ton interpellant et engageant. Tu poses des questions qui font reflechir et challenges les idees recues.",
        }

        # Charger le persona depuis le fichier
        persona_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "linkedin_persona.md")
        persona_style = ""
        if os.path.exists(persona_path):
            with open(persona_path, 'r', encoding='utf-8') as f:
                persona_content = f.read()
                persona_style = "\n\nSTYLE 'PARISIEN GENZ' A APPLIQUER:\n" + persona_content[persona_content.find("### ✨ Ton & Style"):persona_content.find("### 🎨 Thématiques favorites")]

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Base : Paris | Génération Z assumée
{persona_style}

Tu dois creer un post LinkedIn pour partager un article. Le post doit:
- Etre authentique et refléter ta voix de consultant data/IA
- Apporter de la valeur en reformulant les points cles avec ta perspective de consultant, SANS inventer d'exemples ou d'anecdotes
- Donner envie de lire l'article SANS simplement le resumer
- {'Utiliser des emojis avec moderation pour structurer' if include_emoji else 'Ne PAS utiliser d emojis'}
- Faire entre 1000 et 1500 caracteres
- Se terminer par une question d engagement

REGLES IMPERATIVES:
- Base-toi UNIQUEMENT sur le contenu de l'article. Ne fabrique aucun fait, chiffre ou exemple.
- Ne JAMAIS inventer d'anecdotes personnelles ou d'experiences fictives
- Ta "perspective" = ton analyse des faits de l'article, PAS une histoire inventee

{tone_instructions.get(tone, tone_instructions['expert'])}"""

        prompt = f"""Genere un post LinkedIn pour partager cet article:

TITRE: {article['title']}
URL: {article['url']}

CONTENU DE L'ARTICLE:
{article['content']}

Structure du post:
1. HOOK (1-2 lignes percutantes qui captent l'attention - NE PAS commencer par "Je viens de lire...")
2. TA PERSPECTIVE (2-3 phrases avec ton analyse personnelle, un enseignement ou une experience en lien)
3. POINTS CLES (2-3 elements cles de l'article, reformules avec ta vision)
4. APPEL A L'ACTION (invitation a lire + question d'engagement)
5. HASHTAGS (3-5 hashtags pertinents)

IMPORTANT:
- Le lien vers l'article sera ajoute automatiquement, NE PAS l'inclure dans le texte du post
- NE PAS ecrire "Lien en commentaire" ou "Article en commentaire"
- Sois specifique sur le contenu, pas generique
- Ecris en francais"""

        main_post = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=1500,
        )

        # Generer une variante courte
        short_prompt = f"""A partir de ce post LinkedIn, cree une version courte (400-600 caracteres max) qui va droit au point.
Garde le hook et la question finale, compresse le milieu.

Post original:
{main_post}

{'Utilise des emojis' if include_emoji else 'Pas d emojis'}.
NE PAS inclure le lien de l'article dans le texte.
NE PAS inventer d'anecdotes ou d'exemples qui ne sont pas dans le post original."""

        short_version = self.llm_client.generate(
            prompt=short_prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=600,
        )

        print("   ✅ Post genere avec variante courte")

        return {
            'main_post': main_post,
            'short_version': short_version,
            'tone': tone,
            'article_title': article['title'],
            'article_url': article['url'],
            'generated_at': datetime.now().isoformat(),
            'consultant': self.consultant_info,
        }

    def run(
        self,
        url: str,
        tone: str = "expert",
        include_emoji: bool = True,
    ) -> Dict[str, Any]:
        """
        Pipeline complet: fetch article -> genere post

        Args:
            url: URL de l'article
            tone: Ton du post
            include_emoji: Inclure des emojis

        Returns:
            Resultat complet
        """
        print(f"\n{'='*50}")
        print("📝 GENERATION DE POST LINKEDIN")
        print(f"{'='*50}\n")

        article = self.fetch_article(url)
        result = self.generate_post(article, tone=tone, include_emoji=include_emoji)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, f"article_post_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Post LinkedIn - Partage d'article\n\n")
            f.write(f"**Article:** [{article['title']}]({url})\n")
            f.write(f"**Ton:** {tone}\n")
            f.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("## Post Principal\n\n")
            f.write(result['main_post'])
            f.write(f"\n\n🔗 {url}\n")
            f.write("\n\n---\n\n## Version Courte\n\n")
            f.write(result['short_version'])
            f.write(f"\n\n🔗 {url}\n")

        result['md_path'] = md_path
        print(f"\n✅ Post sauvegarde: {md_path}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generer un post LinkedIn a partir d\'un article')
    parser.add_argument('url', help='URL de l\'article')
    parser.add_argument('--tone', choices=['expert', 'casual', 'provocateur'], default='expert')
    parser.add_argument('--no-emoji', action='store_true')

    args = parser.parse_args()

    agent = ArticleToPostAgent()
    result = agent.run(url=args.url, tone=args.tone, include_emoji=not args.no_emoji)

    print(f"\n{'='*50}")
    print("POST GENERE")
    print(f"{'='*50}\n")
    print(result['main_post'])
    print(f"\n🔗 {args.url}")


if __name__ == '__main__':
    main()
