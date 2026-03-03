"""
Validation et sanitization des inputs utilisateur
Protection contre injections, uploads malicieux, etc.
"""

import re
from typing import Optional

from fastapi import HTTPException, UploadFile

# Constantes de validation
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_INPUT_LENGTH = 50000  # 50k caracteres max pour inputs texte
MAX_SHORT_INPUT_LENGTH = 500  # Pour titres, noms, etc.

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".json",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


class ValidationError(Exception):
    """Erreur de validation custom"""


async def validate_file_upload(
    file: UploadFile, allowed_extensions: Optional[set] = None, max_size: int = MAX_UPLOAD_SIZE
) -> bytes:
    """
    Valide un fichier uploade (taille, type, contenu)

    Args:
        file: Fichier uploade via FastAPI
        allowed_extensions: Extensions autorisees (si None, utilise ALLOWED_DOCUMENT_EXTENSIONS)
        max_size: Taille max en bytes

    Returns:
        Contenu du fichier en bytes

    Raises:
        HTTPException: Si validation echoue
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_DOCUMENT_EXTENSIONS

    # Verifier extension
    filename = file.filename.lower() if file.filename else ""
    extension = None
    for ext in allowed_extensions:
        if filename.endswith(ext):
            extension = ext
            break

    if not extension:
        allowed_exts_str = ', '.join(allowed_extensions)
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorise. Extensions acceptees : {allowed_exts_str}",
        )

    # Lire contenu
    content = await file.read()

    # Verifier taille
    if len(content) > max_size:
        size_mb = len(content) / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        detail_msg = f"Fichier trop volumineux ({size_mb:.1f}MB). Taille max : {max_mb:.0f}MB"
        raise HTTPException(
            status_code=413,
            detail=detail_msg,
        )

    # Verifier que le fichier n est pas vide
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    return content


def sanitize_text_input(
    text: str, max_length: int = MAX_TEXT_INPUT_LENGTH, field_name: str = "input"
) -> str:
    """
    Nettoie et valide un input texte utilisateur

    Args:
        text: Texte a valider
        max_length: Longueur max autorisee
        field_name: Nom du champ (pour message erreur)

    Returns:
        Texte nettoye

    Raises:
        ValidationError: Si validation echoue
    """
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Verifier longueur
    if len(text) > max_length:
        raise ValidationError(
            f"{field_name} trop long ({len(text)} caracteres). "
            f"Maximum : {max_length} caracteres"
        )

    # Enlever caracteres de controle dangereux (sauf \n, \t, \r)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

    return text


def sanitize_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour eviter path traversal

    Args:
        filename: Nom de fichier original

    Returns:
        Nom de fichier securise
    """
    if not filename:
        return "unknown"

    # Enlever path traversal attempts
    filename = filename.replace("../", "").replace("..\\", "")
    filename = filename.replace("/", "_").replace("\\", "_")

    # Garder seulement caracteres safe
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Limiter longueur
    if len(filename) > 255:
        # Garder extension
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            filename = name[:250] + "." + ext
        else:
            filename = filename[:255]

    return filename


def validate_email(email: str) -> bool:
    """
    Valide basiquement un email

    Args:
        email: Adresse email

    Returns:
        True si valide
    """
    if not email:
        return False

    # Pattern basique mais securise
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_url(url: str) -> str:
    """
    Valide et nettoie une URL

    Args:
        url: URL a valider

    Returns:
        URL nettoyee

    Raises:
        ValidationError: Si URL invalide
    """
    if not url:
        raise ValidationError("URL vide")

    url = url.strip()

    # Verifier protocole safe
    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL doit commencer par http:// ou https://")

    # Bloquer javascript: et autres protocoles dangereux
    dangerous_protocols = ["javascript:", "data:", "vbscript:", "file:"]
    for proto in dangerous_protocols:
        if proto in url.lower():
            raise ValidationError(f"Protocole {proto} non autorise")

    # Limiter longueur
    if len(url) > 2000:
        raise ValidationError("URL trop longue (max 2000 caracteres)")

    return url


# Fonctions de validation rapide pour routes FastAPI
def validate_topic(topic: str) -> str:
    """Valide un topic/sujet"""
    return sanitize_text_input(topic, max_length=1000, field_name="topic")


def validate_description(desc: str) -> str:
    """Valide une description"""
    return sanitize_text_input(desc, max_length=5000, field_name="description")


def validate_title(title: str) -> str:
    """Valide un titre"""
    return sanitize_text_input(title, max_length=MAX_SHORT_INPUT_LENGTH, field_name="title")


# === SECRET MASKING (Phase 3 Security) ===


def mask_secret(secret: Optional[str], show_chars: int = 4) -> str:
    """
    Masque un secret pour les logs (API key, password, token)

    Args:
        secret: Le secret a masquer
        show_chars: Nombre de caracteres a montrer au debut et a la fin

    Returns:
        Secret masque (ex: "sk-a***xyz" ou "***")

    Examples:
        >>> mask_secret("sk-ant-api-key-12345")
        "sk-a***345"
        >>> mask_secret("short")
        "***"
        >>> mask_secret(None)
        "***"
    """
    if not secret:
        return "***"

    # Si le secret est trop court, tout masquer
    if len(secret) < (show_chars * 2 + 3):
        return "***"

    # Montrer debut et fin
    return f"{secret[:show_chars]}***{secret[-show_chars:]}"


def mask_api_key(api_key: Optional[str]) -> str:
    """
    Masque une API key pour les logs

    Args:
        api_key: La cle API

    Returns:
        Cle masquee

    Examples:
        >>> mask_api_key("sk-ant-api-1234567890abcdef")
        "sk-a***cdef"
        >>> mask_api_key("AIzaSyD1234567890abcdef")
        "AIza***cdef"
    """
    return mask_secret(api_key, show_chars=4)


def mask_password(password: Optional[str]) -> str:
    """
    Masque un mot de passe pour les logs

    Args:
        password: Le mot de passe

    Returns:
        Mot de passe masque (toujours "***" pour securite maximale)
    """
    # Pour les passwords, toujours tout masquer
    return "***" if password else "***"


def sanitize_error_message(error_msg: str) -> str:
    """
    Nettoie un message d erreur pour enlever les secrets potentiels

    Args:
        error_msg: Message d erreur original

    Returns:
        Message nettoye

    Examples:
        >>> sanitize_error_message("API key sk-ant-123456 is invalid")
        "API key ****** is invalid"
    """
    import re

    # Patterns de secrets courants
    patterns = [
        # API keys Anthropic
        (r"sk-ant-[a-zA-Z0-9-_]{40,}", "******"),
        # API keys OpenAI
        (r"sk-[a-zA-Z0-9]{32,}", "******"),
        # API keys Google/Gemini
        (r"AIza[a-zA-Z0-9_-]{35,}", "******"),
        # Tokens generiques
        (r"[a-zA-Z0-9_-]{40,}", lambda m: mask_secret(m.group(0), show_chars=3)),
        # Passwords dans URLs
        (r"://[^:]+:([^@]+)@", r"://*****:*****@"),
    ]

    sanitized = error_msg
    for pattern, replacement in patterns:
        if callable(replacement):
            sanitized = re.sub(pattern, replacement, sanitized)
        else:
            sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized
