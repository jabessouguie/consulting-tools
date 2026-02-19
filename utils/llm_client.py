"""
Client LLM pour interagir avec Claude (Anthropic) ou Gemini (Google)
"""
import os
import time
from typing import Optional, List, Dict, Any
from anthropic import Anthropic, RateLimitError
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

from pathlib import Path
SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"


def _get_gemini_model_from_settings():
    """Lit le modele Gemini depuis settings.json"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            return settings.get("gemini_model")
    except Exception:
        pass
    return None


class LLMClient:
    """Client pour interagir avec les LLM (Claude ou Gemini)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        max_tokens: int = 4096,
        provider: str = None
    ):
        """
        Initialise le client LLM

        Args:
            api_key: Clé API (Anthropic ou Google)
            model: Modèle à utiliser (auto-détecté selon le provider)
            max_tokens: Nombre maximum de tokens
            provider: 'claude' ou 'gemini' (auto-détecté si None)
        """
        # Détecter le provider
        use_gemini = os.getenv('USE_GEMINI', 'false').lower() == 'true'
        self.provider = provider or ('gemini' if use_gemini else 'claude')

        # Configuration selon le provider
        if self.provider == 'gemini':
            self.api_key = api_key or os.getenv('GEMINI_API_KEY')
            self.model = model or _get_gemini_model_from_settings() or os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
            genai.configure(api_key=self.api_key)
            self.client = None
            print(f"  [Gemini] {self.model}")
        else:
            self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
            self.model = model or "claude-opus-4-6"
            self.client = Anthropic(api_key=self.api_key)
            print(f"  [Claude] {self.model}")

        self.max_tokens = max_tokens

    def _retry_with_backoff(self, func, *args, max_retries=5, **kwargs):
        """
        Execute une fonction avec retry exponentiel en cas de rate limit

        Args:
            func: Fonction à exécuter
            max_retries: Nombre maximum de tentatives
            *args, **kwargs: Arguments de la fonction

        Returns:
            Résultat de la fonction
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise

                # Backoff exponentiel: 2^attempt secondes (2, 4, 8, 16, 32)
                wait_time = 2 ** attempt
                print(f"   ⏳ Rate limit atteint. Attente de {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)
            except Exception as e:
                # Pour les autres erreurs, ne pas retry
                raise

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Génère une réponse depuis le LLM (Claude ou Gemini)

        Args:
            prompt: Le prompt utilisateur
            system_prompt: Le prompt système (optionnel)
            temperature: Température de génération
            **kwargs: Arguments supplémentaires

        Returns:
            La réponse générée
        """
        if self.provider == 'gemini':
            return self._generate_gemini(prompt, system_prompt, temperature, **kwargs)
        else:
            return self._generate_claude(prompt, system_prompt, temperature, **kwargs)

    def _generate_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """Génère une réponse avec Claude"""
        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.model,
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "temperature": temperature,
            "messages": messages
        }

        if system_prompt:
            params["system"] = system_prompt

        response = self._retry_with_backoff(self.client.messages.create, **params)
        return response.content[0].text

    def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """Génère une réponse avec Gemini"""
        # Construire le prompt complet
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # Configuration de génération
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": kwargs.get('max_tokens', self.max_tokens),
        }

        # Créer le modèle et générer
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        return response.text

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        **kwargs
    ):
        """Yields text chunks as they arrive from the LLM"""
        if self.provider == 'gemini':
            yield from self._stream_gemini(prompt, system_prompt, temperature, **kwargs)
        else:
            yield from self._stream_claude(prompt, system_prompt, temperature, **kwargs)

    def _stream_claude(self, prompt, system_prompt=None, temperature=1.0, **kwargs):
        """Stream response from Claude"""
        messages = [{"role": "user", "content": prompt}]
        params = {
            "model": self.model,
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "temperature": temperature,
            "messages": messages
        }
        if system_prompt:
            params["system"] = system_prompt

        with self.client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                yield text

    def _stream_gemini(self, prompt, system_prompt=None, temperature=1.0, **kwargs):
        """Stream response from Gemini"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": kwargs.get('max_tokens', self.max_tokens),
        }

        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
            stream=True
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Génère une réponse avec un contexte de conversation

        Args:
            messages: Liste des messages (format [{"role": "user/assistant", "content": "..."}])
            system_prompt: Le prompt système
            **kwargs: Arguments supplémentaires

        Returns:
            La réponse générée
        """
        if self.provider == 'gemini':
            # Pour Gemini, convertir le format de messages
            chat_history = []
            for msg in messages[:-1]:  # Tous sauf le dernier
                role = "user" if msg["role"] == "user" else "model"
                chat_history.append({"role": role, "parts": [msg["content"]]})

            # Créer le modèle avec le system prompt
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_prompt if system_prompt else None
            )

            # Démarrer le chat
            chat = model.start_chat(history=chat_history)

            # Envoyer le dernier message
            last_message = messages[-1]["content"]
            response = chat.send_message(
                last_message,
                generation_config={
                    "temperature": kwargs.get('temperature', 1.0),
                    "max_output_tokens": kwargs.get('max_tokens', self.max_tokens)
                }
            )

            return response.text
        else:
            # Claude
            params = {
                "model": self.model,
                "max_tokens": kwargs.get('max_tokens', self.max_tokens),
                "temperature": kwargs.get('temperature', 1.0),
                "messages": messages
            }

            if system_prompt:
                params["system"] = system_prompt

            response = self._retry_with_backoff(self.client.messages.create, **params)
            return response.content[0].text

    def extract_structured_data(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extrait des données structurées depuis le LLM

        Args:
            prompt: Le prompt
            output_schema: Schéma JSON de la sortie attendue
            **kwargs: Arguments supplémentaires

        Returns:
            Dictionnaire avec les données structurées
        """
        system_prompt = f"""Tu dois répondre uniquement avec un JSON valide qui respecte ce schéma:
{json.dumps(output_schema, indent=2)}

Ne fournis aucune explication, uniquement le JSON."""

        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            **kwargs
        )

        # Nettoyer la réponse pour extraire le JSON
        response = response.strip()
        
        # Suppr les blocs Markdown
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
            
        response = response.strip()
        
        # Sanitization basique (control chars)
        import re
        response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', response)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON dans extract_structured_data: {e}")
            print(f"Contenu reçu (début): {response[:200]}...")
            # Tentative de réparation naïve : échapper les newlines dans les strings ?
            # Souvent le modèle met des \n réels au lieu de \\n dans les valeurs JSON
            try:
                # On essaie de remplacer les newlines par \\n si ce n'est pas déjà fait
                # C'est risqué mais peut sauver des cas simples
                fixed = response.replace('\n', '\\n')
                return json.loads(fixed)
            except:
                pass
            return {}  # Retour vide en cas d'échec total pour éviter le crash 500


    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        Résume un texte

        Args:
            text: Texte à résumer
            max_length: Longueur maximale du résumé (en mots)

        Returns:
            Le résumé
        """
        prompt = f"""Résume le texte suivant en maximum {max_length} mots, en français, de manière claire et concise:

{text}"""

        return self.generate(prompt=prompt, temperature=0.5)

    def translate(self, text: str, target_lang: str = "fr") -> str:
        """
        Traduit un texte

        Args:
            text: Texte à traduire
            target_lang: Langue cible

        Returns:
            Le texte traduit
        """
        prompt = f"""Traduis le texte suivant en {target_lang}:

{text}"""

        return self.generate(prompt=prompt, temperature=0.3)
