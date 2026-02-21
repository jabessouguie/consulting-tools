#!/usr/bin/env python3
"""
Script de validation de l'installation
Verifie que tout est correctement configure avant de lancer l'app
"""
import sys
import os
from pathlib import Path

# Couleurs pour terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_header(msg):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{msg}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

def check_python_version():
    """Verifie la version de Python"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (requis: 3.10+)")
        print("   → Installez Python 3.10+ : https://www.python.org/downloads/")
        return False

def check_dependencies():
    """Verifie les dependances Python"""
    required = [
        'fastapi',
        'uvicorn',
        'anthropic',
        'python-dotenv',
        'pptx',
        'docx',
        'PyPDF2'
    ]

    missing = []
    for package in required:
        try:
            if package == 'python-dotenv':
                import dotenv
            elif package == 'pptx':
                import pptx
            elif package == 'docx':
                import docx
            else:
                __import__(package)
            print_ok(f"Package '{package}' installé")
        except ImportError:
            print_error(f"Package '{package}' manquant")
            missing.append(package)

    if missing:
        print(f"\n{YELLOW}Pour installer les packages manquants :{RESET}")
        print(f"  pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """Verifie le fichier .env"""
    env_path = Path('.env')
    env_example = Path('.env.example')

    if not env_path.exists():
        print_error("Fichier .env non trouvé")
        if env_example.exists():
            print(f"   → Créez-le : cp .env.example .env")
        return False

    print_ok("Fichier .env existe")

    # Charger et verifier contenu
    from dotenv import load_dotenv
    load_dotenv()

    issues = []

    # Verifier CONSULTANT_NAME
    consultant_name = os.getenv('CONSULTANT_NAME')
    if not consultant_name or consultant_name in ['Votre Nom Complet', 'CONFIGURE_CONSULTANT_NAME']:
        print_warning("CONSULTANT_NAME non configuré dans .env")
        issues.append("CONSULTANT_NAME")
    else:
        print_ok(f"CONSULTANT_NAME = {consultant_name}")

    # Verifier API Key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    use_gemini = os.getenv('USE_GEMINI', 'false').lower() == 'true'

    if use_gemini:
        if not gemini_key or gemini_key == 'your_gemini_api_key_here':
            print_error("GEMINI_API_KEY non configurée (USE_GEMINI=true)")
            issues.append("GEMINI_API_KEY")
        else:
            print_ok(f"GEMINI_API_KEY configurée (use_gemini=true)")
    else:
        if not anthropic_key or anthropic_key == 'your_anthropic_api_key_here':
            print_error("ANTHROPIC_API_KEY non configurée")
            issues.append("ANTHROPIC_API_KEY")
        else:
            print_ok(f"ANTHROPIC_API_KEY configurée")

    # Verifier password
    password = os.getenv('AUTH_PASSWORD')
    if not password or password == 'CHANGE_ME_ON_FIRST_INSTALL':
        print_warning("AUTH_PASSWORD = défaut (changez-le pour sécuriser)")
    else:
        print_ok("AUTH_PASSWORD configuré")

    return len(issues) == 0

def check_data_directory():
    """Verifie le dossier data/"""
    data_dir = Path('data')

    if not data_dir.exists():
        print_warning("Dossier 'data/' non trouvé (sera créé automatiquement)")
        data_dir.mkdir(exist_ok=True)
        print_ok("Dossier 'data/' créé")

    # Verifier personality.md (optionnel)
    personality = data_dir / 'personality.md'
    if personality.exists():
        print_ok("data/personality.md existe")
    else:
        print_warning("data/personality.md absent (sera créé automatiquement)")

    # Verifier linkedin_profile (optionnel)
    linkedin_dir = data_dir / 'linkedin_profile'
    if linkedin_dir.exists():
        print_ok("data/linkedin_profile/ existe")
        # Compter fichiers
        files = list(linkedin_dir.rglob('*'))
        print(f"   → {len(files)} fichiers trouvés")
    else:
        print_warning("data/linkedin_profile/ absent (optionnel)")

    return True

def check_config_module():
    """Verifie que le module de config fonctionne"""
    try:
        from config import get_consultant_info

        try:
            config = get_consultant_info()
            print_ok(f"Module config OK : {config['name']}")
            return True
        except ValueError as e:
            print_warning(f"Config non complète : {str(e)[:80]}...")
            return False

    except ImportError as e:
        print_error(f"Module config ne charge pas : {e}")
        return False

def check_app_syntax():
    """Verifie que app.py compile sans erreur"""
    import ast
    try:
        with open('app.py') as f:
            ast.parse(f.read())
        print_ok("app.py : syntaxe valide")
        return True
    except SyntaxError as e:
        print_error(f"app.py : erreur syntaxe ligne {e.lineno}")
        return False
    except FileNotFoundError:
        print_error("app.py non trouvé")
        return False

def main():
    print_header("🔍 Vérification de l'installation WEnvision Tools")

    checks = [
        ("Version Python", check_python_version),
        ("Dépendances Python", check_dependencies),
        ("Fichier .env", check_env_file),
        ("Dossier data/", check_data_directory),
        ("Module config", check_config_module),
        ("Syntaxe app.py", check_app_syntax),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 {BOLD}{name}{RESET}")
        result = check_func()
        results.append((name, result))

    # Resume
    print_header("📊 Résumé")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        if result:
            print_ok(name)
        else:
            print_error(name)

    print(f"\n{BOLD}Score : {passed}/{total}{RESET}")

    if passed == total:
        print(f"\n{GREEN}{BOLD}✨ Installation complète ! Vous pouvez lancer l'application :{RESET}")
        print(f"   python app.py")
        print(f"   Puis ouvrez http://localhost:8000")
        return 0
    else:
        print(f"\n{YELLOW}{BOLD}⚠️  Certaines configurations manquent{RESET}")
        print(f"   Consultez INSTALL_GUIDE.md pour plus d'aide")
        return 1

if __name__ == '__main__':
    sys.exit(main())
