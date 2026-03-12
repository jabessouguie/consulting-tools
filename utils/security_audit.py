"""
Script d'audit de sécurité pour Consulting Tools Agents
Vérifie la configuration des variables d'environnement et la sécurité du code
"""

import re
from pathlib import Path
from typing import Dict, List

# Couleurs pour l'affichage
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_env_file() -> Dict[str, any]:
    """Vérifie que le fichier .env existe et contient les variables nécessaires"""
    print(f"\n{BOLD}1. Vérification du fichier .env{RESET}")

    base_dir = Path(__file__).parent.parent
    env_file = base_dir / ".env"
    base_dir / ".env.example"

    results = {"status": "ok", "issues": []}

    # Vérifier que .env existe
    if not env_file.exists():
        results["status"] = "error"
        results["issues"].append("Fichier .env manquant")
        print(f"  {RED}✗{RESET} Fichier .env introuvable")
        return results
    else:
        print(f"  {GREEN}✓{RESET} Fichier .env trouvé")

    # Vérifier les permissions du fichier .env
    env_stat = env_file.stat()
    if oct(env_stat.st_mode)[-3:] not in ["600", "640"]:
        results["issues"].append("Permissions .env trop permissives")
        print(
            f"  {YELLOW}⚠{RESET}  Permissions .env: {oct(env_stat.st_mode)[-3:]} (recommandé: 600)"
        )

    # Lire les variables
    with open(env_file, "r") as f:
        env_content = f.read()

    # Variables critiques requises
    required_vars = [
        "ANTHROPIC_API_KEY",
        "AUTH_USERNAME",
        "AUTH_PASSWORD",
        "SESSION_SECRET",
    ]

    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)

    if missing_vars:
        results["status"] = "warning"
        results["issues"].extend([f"Variable manquante: {v}" for v in missing_vars])
        missing_list = ", ".join(missing_vars)
        print(f"  {YELLOW}⚠{RESET}  Variables manquantes: {missing_list}")
    else:
        print(f"  {GREEN}✓{RESET} Toutes les variables critiques sont présentes")

    # Vérifier que les valeurs ne sont pas les valeurs par défaut
    if "your_anthropic_api_key_here" in env_content:
        results["issues"].append("ANTHROPIC_API_KEY non configurée")
        print(f"  {YELLOW}⚠{RESET}  ANTHROPIC_API_KEY utilise encore la valeur par défaut")

    if "consultingtools2026" in env_content.lower().replace(" ", ""):
        results["issues"].append("Mot de passe par défaut utilisé")
        print(f"  {YELLOW}⚠{RESET}  AUTH_PASSWORD utilise le mot de passe par défaut")

    if "generate_with_secrets.token_urlsafe" in env_content:
        results["issues"].append("SESSION_SECRET pas générée")
        print(f"  {YELLOW}⚠{RESET}  SESSION_SECRET n'a pas été générée")

    return results


def check_gitignore() -> Dict[str, any]:
    """Vérifie que les fichiers sensibles sont dans .gitignore"""
    print(f"\n{BOLD}2. Vérification du .gitignore{RESET}")

    base_dir = Path(__file__).parent.parent
    gitignore_file = base_dir / ".gitignore"

    results = {"status": "ok", "issues": []}

    if not gitignore_file.exists():
        results["status"] = "error"
        results["issues"].append(".gitignore manquant")
        print(f"  {RED}✗{RESET} Fichier .gitignore introuvable")
        return results

    with open(gitignore_file, "r") as f:
        gitignore_content = f.read()

    # Fichiers sensibles qui doivent être ignorés
    sensitive_files = [
        ".env",
        "*.pem",
        "*.key",
        "ssl/",
    ]

    missing = []
    for pattern in sensitive_files:
        if pattern not in gitignore_content:
            missing.append(pattern)

    if missing:
        results["status"] = "warning"
        results["issues"].extend([f"Pattern manquant dans .gitignore: {p}" for p in missing])
        print(f"  {YELLOW}⚠{RESET}  Patterns manquants: {', '.join(missing)}")
    else:
        print(f"  {GREEN}✓{RESET} Tous les fichiers sensibles sont ignorés")

    return results


def check_hardcoded_secrets() -> Dict[str, any]:
    """Vérifie qu'il n'y a pas de secrets hardcodés dans le code"""
    print(f"\n{BOLD}3. Recherche de secrets hardcodés{RESET}")

    base_dir = Path(__file__).parent.parent
    results = {"status": "ok", "issues": []}

    # Patterns à rechercher
    secret_patterns = [
        (r"sk-ant-[a-zA-Z0-9\-_]+", "Clé API Anthropic"),
        (r"sk-[a-zA-Z0-9]{48}", "Clé API OpenAI"),
        (r'password\s*=\s*["\'][^"\']{8,}["\']', "Mot de passe en dur"),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Clé API en dur"),
    ]

    # Fichiers à analyser
    py_files = list(base_dir.glob("**/*.py"))
    # Exclure les fichiers tests (fixtures) et le script lui-même
    excluded_dirs = {"security_audit.py", "venv", "__pycache__", "tests", ".venv"}

    issues_found = []

    for py_file in py_files:
        # Exclure certains fichiers/dossiers
        if any(excluded in str(py_file) for excluded in excluded_dirs):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()

            # Exclure les lignes d'exemples doctest (>>>) et les commentaires
            filtered = [
                ln for ln in raw_lines
                if not ln.strip().startswith(">>>")
                and not ln.strip().startswith("#")
            ]
            content = "".join(filtered)

            for pattern, description in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        match_str = match if isinstance(match, str) else match[0]
                        # Filtrer les faux positifs :
                        # - valeurs d'exemple ou de template
                        # - patterns regex (contiennent des métacaractères)
                        if (
                            "example" in match_str.lower()
                            or "your_" in match_str.lower()
                            or re.search(r"[+*?\[\]\\{]", match_str)
                        ):
                            continue
                        issue = f"{description} trouvé dans {py_file.name}"
                        if issue not in issues_found:
                            issues_found.append(issue)
                            print(f"  {RED}✗{RESET} {issue}")

        except Exception:
            pass

    if not issues_found:
        print(f"  {GREEN}✓{RESET} Aucun secret hardcodé détecté")
    else:
        results["status"] = "error"
        results["issues"].extend(issues_found)

    return results


def check_ssl_config() -> Dict[str, any]:
    """Vérifie la configuration SSL"""
    print(f"\n{BOLD}4. Vérification SSL{RESET}")

    base_dir = Path(__file__).parent.parent
    ssl_dir = base_dir / "ssl"

    results = {"status": "ok", "issues": []}

    if not ssl_dir.exists():
        results["status"] = "warning"
        results["issues"].append("Dossier SSL manquant")
        print(f"  {YELLOW}⚠{RESET}  Dossier ssl/ non trouvé")
        return results

    cert_file = ssl_dir / "cert.pem"
    key_file = ssl_dir / "key.pem"

    if not cert_file.exists() or not key_file.exists():
        results["status"] = "warning"
        results["issues"].append("Certificats SSL manquants")
        print(f"  {YELLOW}⚠{RESET}  Certificats SSL manquants")
    else:
        print(f"  {GREEN}✓{RESET} Certificats SSL trouvés")

        # Vérifier les permissions de la clé privée
        key_stat = key_file.stat()
        if oct(key_stat.st_mode)[-3:] != "600":
            results["issues"].append("Permissions clé privée trop permissives")
            print(
                f"  {YELLOW}⚠{RESET}  Permissions key.pem: {oct(key_stat.st_mode)[-3:]} (recommandé: 600)"
            )
        else:
            print(f"  {GREEN}✓{RESET} Permissions clé privée correctes")

    return results


def generate_report(all_results: List[Dict]) -> None:
    """Génère un rapport final"""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}RAPPORT D'AUDIT DE SÉCURITÉ{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    total_issues = sum(len(r["issues"]) for r in all_results)
    errors = sum(1 for r in all_results if r["status"] == "error")
    warnings = sum(1 for r in all_results if r["status"] == "warning")

    if total_issues == 0:
        print(f"{GREEN}{BOLD}✓ Aucun problème de sécurité détecté !{RESET}\n")
        print("L'application est correctement sécurisée.")
    else:
        if errors > 0:
            print(f"{RED}{BOLD}✗ {errors} erreur(s) critique(s) détectée(s){RESET}")
        if warnings > 0:
            print(f"{YELLOW}{BOLD}⚠ {warnings} avertissement(s){RESET}")

        print(f"\n{BOLD}Actions recommandées :{RESET}")
        for result in all_results:
            for issue in result["issues"]:
                severity = "🔴" if result["status"] == "error" else "🟡"
                print(f"  {severity} {issue}")

    print(f"\n{BOLD}Recommandations générales :{RESET}")
    print("  • Changer AUTH_PASSWORD régulièrement")
    print("  • Générer une nouvelle SESSION_SECRET unique")
    print("  • Ne jamais commiter le fichier .env")
    print("  • Utiliser un certificat SSL valide en production")
    print("  • Activer le monitoring des logs d'authentification")


def main():
    print(f"\n{BOLD}🔒 AUDIT DE SÉCURITÉ - Consulting Tools AGENTS{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    results = []

    # Exécuter tous les checks
    results.append(check_env_file())
    results.append(check_gitignore())
    results.append(check_hardcoded_secrets())
    results.append(check_ssl_config())

    # Générer le rapport final
    generate_report(results)

    # Exit code basé sur le résultat
    if any(r["status"] == "error" for r in results):
        exit(1)
    elif any(r["status"] == "warning" for r in results):
        exit(0)  # Warnings mais pas d'erreurs critiques
    else:
        exit(0)


if __name__ == "__main__":
    main()
