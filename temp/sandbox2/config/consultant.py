"""
Configuration centralisee du consultant
Evite les fallbacks hardcodes et force la configuration via .env
"""
import os
from typing import Dict, Any
from pathlib import Path


class ConsultantConfig:
    """Configuration centralisee du consultant depuis .env"""

    _instance = None
    _config = None

    def __new__(cls):
        """Singleton pour eviter de recharger la config"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get(cls) -> Dict[str, Any]:
        """
        Charge et retourne la configuration du consultant

        Returns:
            Dict avec name, title, company, profile

        Raises:
            ValueError: Si CONSULTANT_NAME n est pas configure dans .env
        """
        # Cache la config pour eviter de relire .env a chaque appel
        if cls._config is not None:
            return cls._config

        # Charger depuis .env
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

        # CONSULTANT_NAME est OBLIGATOIRE (pas de fallback)
        name = os.getenv('CONSULTANT_NAME')
        if not name:
            raise ValueError(
                "\n"
                "="*60 + "\n"
                "❌ ERREUR DE CONFIGURATION\n"
                "="*60 + "\n"
                "CONSULTANT_NAME non configure dans votre fichier .env\n\n"
                "SOLUTION :\n"
                "1. Copiez .env.example vers .env si ce n est pas deja fait\n"
                "2. Editez .env et configurez :\n"
                "   CONSULTANT_NAME=Votre Nom Complet\n"
                "   CONSULTANT_TITLE=Votre titre professionnel\n"
                "   COMPANY_NAME=Votre entreprise\n\n"
                "="*60 + "\n"
            )

        # Config complete
        cls._config = {
            'name': name,
            'title': os.getenv('CONSULTANT_TITLE', 'Consultant'),
            'company': os.getenv('COMPANY_NAME', 'Company'),
            'profile': os.getenv('CONSULTANT_PROFILE', ''),
            'linkedin_email': os.getenv('LINKEDIN_EMAIL', ''),
        }

        return cls._config

    @classmethod
    def reset(cls):
        """Reset le cache (utile pour tests)"""
        cls._config = None


# Fonction helper pour utilisation simple
def get_consultant_info() -> Dict[str, Any]:
    """
    Fonction helper pour recuperer la config du consultant

    Returns:
        Dict avec name, title, company, profile
    """
    return ConsultantConfig.get()


if __name__ == "__main__":
    # Test de la configuration
    try:
        config = get_consultant_info()
        print("\n✅ Configuration chargee avec succes :")
        print(f"   Nom     : {config['name']}")
        print(f"   Titre   : {config['title']}")
        print(f"   Company : {config['company']}")
        print(f"   Profile : {config['profile'][:50]}..." if config['profile'] else "   Profile : (vide)")
    except ValueError as e:
        print(str(e))
