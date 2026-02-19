"""
Module d'authentification pour Wenvision Agents
Gère les sessions utilisateur et la vérification des credentials
"""
import os
import secrets
from typing import Optional
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from starlette.middleware.sessions import SessionMiddleware

# Configuration du hashage de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash un mot de passe"""
    return pwd_context.hash(password)


def get_user_credentials() -> dict:
    """
    Récupère les credentials depuis les variables d'environnement

    Returns:
        Dict avec username et hashed_password
    """
    username = os.getenv("AUTH_USERNAME", "admin")
    # Le mot de passe peut être en clair dans .env (sera hashé à la volée)
    # ou déjà hashé (commence par $2b$)
    password = os.getenv("AUTH_PASSWORD", "wenvision2026")

    # Si le mot de passe n'est pas déjà hashé, le hasher
    if not password.startswith("$2b$"):
        hashed_password = get_password_hash(password)
    else:
        hashed_password = password

    return {
        "username": username,
        "hashed_password": hashed_password
    }


def authenticate_user(username: str, password: str) -> bool:
    """
    Vérifie les credentials d'un utilisateur

    Args:
        username: Nom d'utilisateur
        password: Mot de passe en clair

    Returns:
        True si les credentials sont valides
    """
    credentials = get_user_credentials()

    if username != credentials["username"]:
        return False

    return verify_password(password, credentials["hashed_password"])


def get_current_user(request: Request) -> Optional[str]:
    """
    Récupère l'utilisateur courant depuis la session

    Args:
        request: FastAPI Request

    Returns:
        Username si authentifié, None sinon
    """
    return request.session.get("user")


def require_auth(request: Request) -> str:
    """
    Dépendance FastAPI pour protéger les routes
    Lève une exception si l'utilisateur n'est pas authentifié

    Args:
        request: FastAPI Request

    Returns:
        Username de l'utilisateur authentifié

    Raises:
        HTTPException: Si non authentifié
    """
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié. Veuillez vous connecter.",
        )

    return user


def generate_session_secret() -> str:
    """Génère une clé secrète pour les sessions"""
    return secrets.token_urlsafe(32)


def get_session_secret() -> str:
    """
    Récupère ou génère la clé secrète pour les sessions

    Returns:
        Clé secrète
    """
    secret = os.getenv("SESSION_SECRET")

    if not secret:
        # Générer une clé par défaut (à remplacer en production)
        secret = generate_session_secret()
        print(f"⚠️  Aucune SESSION_SECRET définie dans .env")
        print(f"   Utilisez cette clé générée: {secret}")

    return secret
