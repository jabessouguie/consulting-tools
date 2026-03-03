#!/usr/bin/env python3
"""
Code Review Tool - Analyse les fichiers modifies avant commit/push
Utilise le LLM pour detecter bugs, vulnerabilites et problemes de style.

Usage:
    python review.py                  # Review le git diff staged
    python review.py --file app.py    # Review un fichier specifique
    python review.py --all            # Review tous les fichiers modifies (staged + unstaged)
"""
import argparse
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from utils.llm_client import LLMClient

# Setup path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")


SEVERITY_COLORS = {
    "CRITICAL": "\033[91m",  # Rouge
    "WARNING": "\033[93m",  # Jaune
    "INFO": "\033[96m",  # Cyan
    "OK": "\033[92m",  # Vert
}
RESET = "\033[0m"


def get_git_diff(staged_only=True):
    """Recupere le diff git"""
    cmd = ["git", "dif", "--cached"] if staged_only else ["git", "diff"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
        return result.stdout
    except Exception as e:
        print(f"Erreur git: {e}")
        return ""


def get_file_content(filepath):
    """Lit le contenu d'un fichier"""
    path = BASE_DIR / filepath
    if not path.exists():
        print(f"Fichier non trouve: {filepath}")
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def review_code(code: str, context: str = "git diff") -> str:
    """Envoie le code au LLM pour review"""
    llm = LLMClient(max_tokens=4096)

    system_prompt = """Tu es un expert en code review pour une application web Python/FastAPI avec frontend JavaScript.

Analyse le code fourni et identifie :
1. CRITICAL : Bugs, vulnerabilites de securite (injection, XSS, SQL injection), erreurs logiques
2. WARNING : Problemes de performance, mauvaises pratiques, code mort, erreurs potentielles
3. INFO : Suggestions d'amelioration, lisibilite, conventions

Pour chaque probleme trouve, indique :
- [SEVERITE] Fichier:ligne - Description du probleme
- Suggestion de correction

Si le code est bon, indique [OK] avec un bref resume.

Sois concis et actionnable. Ne commente pas le style ou le formatage sauf si c'est un vrai probleme."""

    prompt = """Review ce {context} :

```
{code[:12000]}
```

Donne ton analyse structuree."""

    return llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.3)


def colorize(text):
    """Ajoute des couleurs aux severites dans le texte"""
    for severity, color in SEVERITY_COLORS.items():
        text = text.replace(f"[{severity}]", f"{color}[{severity}]{RESET}")
    return text


def main():
    parser = argparse.ArgumentParser(description="Code Review Tool")
    parser.add_argument("--file", "-", help="Fichier specifique a reviewer")
    parser.add_argument(
        "--all", "-a", action="store_true", help="Review tous les changements (staged + unstaged)"
    )
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("  CODE REVIEW - WEnvision Agents")
    print(f"{'=' * 60}\n")

    if args.file:
        # Review un fichier specifique
        content = get_file_content(args.file)
        if not content:
            sys.exit(1)
        print(f"  Analyse de {args.file} ({len(content.splitlines())} lignes)...\n")
        result = review_code(content, context=f"fichier {args.file}")
    else:
        # Review le diff git
        diff = get_git_diff(staged_only=not args.all)
        if not diff:
            print("  Aucun changement a reviewer.")
            if not args.all:
                print(
                    "  Tip: Utilisez 'git add' pour stager des fichiers, ou --all pour tout reviewer.\n"
                )
            sys.exit(0)

        # Compter les fichiers modifies
        files = [
            line.split(" b/")[-1] for line in diff.split("\n") if line.startswith("diff --git")
        ]
        print(f"  {len(files)} fichier(s) modifie(s):")
        for f in files:
            print(f"    - {f}")
        print("\n  Analyse en cours...\n")

        result = review_code(diff, context="git diff")

    # Afficher le resultat
    print(colorize(result))

    # Compter les problemes
    criticals = result.count("[CRITICAL]")
    warnings = result.count("[WARNING]")

    print(f"\n{'=' * 60}")
    if criticals > 0:
        print(
            f"  {
                SEVERITY_COLORS['CRITICAL']}BLOQUE : {criticals} probleme(s) critique(s) detecte(s){RESET}"
        )
        print("  Corrigez les problemes CRITICAL avant de commit.\n")
        sys.exit(1)
    elif warnings > 0:
        print(
            f"  {
                SEVERITY_COLORS['WARNING']}ATTENTION : {warnings} warning(s) detecte(s){RESET}"
        )
        print("  Verifiez les warnings avant de commit.\n")
        sys.exit(0)
    else:
        print(
            f"  {
                SEVERITY_COLORS['OK']}OK : Code review passee avec succes{RESET}\n"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
