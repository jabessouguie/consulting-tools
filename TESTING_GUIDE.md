# 🧪 Guide de Testing - Consulting Tools Consulting Tools

## Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Installation](#installation)
- [Exécuter les tests](#exécuter-les-tests)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Couverture de code](#couverture-de-code)
- [Tests de sécurité](#tests-de-sécurité)
- [CI/CD](#cicd)

---

## Vue d'ensemble

### Statistiques de Tests

```
📊 Tests Totaux : 150+
📁 Fichiers de tests : 10
✅ Couverture : 70%+ minimum
🔒 Tests de sécurité : 30+
🚀 Tests d'intégration : 40+
```

### Structure des Tests

```
tests/
├── test_llm_client.py           # Tests LLM client (12 tests)
├── test_validation.py           # Tests validation (35 tests)
├── test_document_parser.py      # Tests parsing documents (15 tests)
├── test_google_api.py           # Tests Google API (10 tests)
├── test_gmail_client.py         # Tests Gmail (25 tests)
├── test_linkedin_client.py      # Tests LinkedIn (25 tests)
├── test_formation_generator.py  # Tests agent formation (8 tests)
├── test_meeting_summarizer.py   # Tests agent meeting (7 tests)
├── test_api_endpoints.py        # Tests intégration API (40 tests)
└── test_security.py             # Tests sécurité (30 tests)
```

---

## Installation

### 1. Installer les dépendances de test

```bash
# Activer venv
source .venv/bin/activate

# Installer dépendances de développement
pip install -r requirements-dev.txt
```

### 2. Configurer pre-commit hooks

```bash
# Installer pre-commit
make setup-hooks

# Ou manuellement
pre-commit install
pre-commit install --hook-type commit-msg
```

---

## Exécuter les Tests

### Tous les tests

```bash
# Via Makefile (recommandé)
make test

# Ou directement avec pytest
pytest tests/ -v
```

### Tests par catégorie

```bash
# Tests unitaires
make test-unit

# Tests d'intégration
make test-integration

# Tests de sécurité
make test-security
```

### Tests spécifiques

```bash
# Un fichier de test
pytest tests/test_llm_client.py -v

# Une classe de test
pytest tests/test_validation.py::TestValidateEmail -v

# Un test spécifique
pytest tests/test_validation.py::TestValidateEmail::test_valid_email -v
```

### Tests avec marqueurs

```bash
# Tests marqués "unit"
pytest -m unit

# Tests marqués "integration"
pytest -m integration

# Tests marqués "security"
pytest -m security

# Exclure tests lents
pytest -m "not slow"
```

---

## Pre-commit Hooks

### Configuration

Le fichier `.pre-commit-config.yaml` configure les hooks suivants :

1. **Black** - Formatage automatique du code
2. **isort** - Tri des imports
3. **flake8** - Linting
4. **Bandit** - Analyse de sécurité
5. **mypy** - Type checking
6. **detect-secrets** - Détection de secrets
7. **safety** - Vérification vulnérabilités
8. **pytest** - Tests unitaires (sur commit)
9. **pytest-cov** - Couverture de code (sur push)

### Utilisation

```bash
# Exécuter tous les hooks sur tous les fichiers
pre-commit run --all-files

# Exécuter un hook spécifique
pre-commit run black --all-files
pre-commit run pytest

# Skip hooks pour un commit (à éviter)
git commit -m "message" --no-verify
```

### Hooks Automatiques

#### Sur `git commit` :
- ✅ Formatage du code (black, isort)
- ✅ Linting (flake8)
- ✅ Type checking (mypy)
- ✅ Security scan (bandit)
- ✅ Détection de secrets
- ✅ Tests unitaires

#### Sur `git push` :
- ✅ Tous les hooks du commit
- ✅ Vérification couverture de code (≥70%)
- ✅ Vérification vulnérabilités (safety)

---

## Couverture de Code

### Générer rapport de couverture

```bash
# HTML + Terminal
make test-cov

# Seulement terminal
pytest tests/ --cov=agents --cov=utils --cov-report=term-missing

# Seulement HTML
pytest tests/ --cov=agents --cov=utils --cov-report=html
```

### Visualiser le rapport

```bash
# Ouvrir rapport HTML
open htmlcov/index.html
```

### Objectifs de Couverture

| Module | Objectif | Actuel |
|--------|----------|--------|
| **agents/** | 70% | 75% |
| **utils/** | 80% | 82% |
| **Global** | 70% | 78% |

### Améliorer la couverture

```bash
# Identifier fichiers non couverts
pytest --cov=agents --cov=utils --cov-report=term-missing | grep "TOTAL"

# Générer rapport détaillé
pytest --cov=agents --cov=utils --cov-report=html
```

---

## Tests de Sécurité

### Scans de sécurité automatiques

```bash
# Scan complet
make security-scan

# Bandit (code Python)
bandit -r agents utils app.py -ll

# Safety (dépendances)
safety check

# Detect-secrets (clés API, tokens)
detect-secrets scan
```

### Tests de sécurité inclus

#### XSS Prevention
- ✅ Injection de scripts dans formulaires
- ✅ Sanitization des entrées utilisateur

#### SQL Injection Prevention
- ✅ Injection SQL dans paramètres
- ✅ Validation des requêtes

#### Path Traversal Prevention
- ✅ Téléchargement de fichiers système
- ✅ Upload de fichiers malveillants

#### CSRF Protection
- ✅ Tokens CSRF sur formulaires
- ✅ Validation des origines

#### Rate Limiting
- ✅ Protection contre abus
- ✅ Limitation requêtes par IP

#### Input Validation
- ✅ Validation emails
- ✅ Validation URLs
- ✅ Validation tailles de fichiers
- ✅ Validation types de fichiers

---

## Linting et Formatage

### Formater le code

```bash
# Formater tout le code
make format

# Seulement black
black agents utils app.py tests --line-length=100

# Seulement isort
isort agents utils app.py tests --profile=black
```

### Vérifier la qualité

```bash
# Linting complet
make lint

# Flake8 uniquement
flake8 agents utils app.py --max-line-length=100

# MyPy uniquement
mypy agents utils app.py --ignore-missing-imports

# Bandit uniquement
bandit -r agents utils app.py
```

---

## CI/CD

### GitHub Actions

Les tests sont exécutés automatiquement via GitHub Actions :

**Sur chaque push/PR** :
- ✅ Tests unitaires (Python 3.13)
- ✅ Tests d'intégration
- ✅ Linting (flake8, black, isort)
- ✅ Security scan (bandit, safety)
- ✅ Couverture de code (≥70%)

**Configuration** : `.github/workflows/ci.yml`

### Simulation locale du CI

```bash
# Simuler pipeline CI
make ci

# Validation complète
make validate
```

---

## Bonnes Pratiques

### 1. Écrire des tests

```python
# ✅ BON - Test clair et spécifique
def test_validate_email_returns_true_for_valid_email():
    """Test que validate_email retourne True pour email valide"""
    assert validate_email("user@example.com") == True

# ❌ MAUVAIS - Test vague
def test_email():
    assert validate_email("user@example.com")
```

### 2. Utiliser des mocks

```python
from unittest.mock import patch, MagicMock

@patch('agents.formation_generator.LLMClient')
def test_generate_formation(mock_llm):
    """Test génération avec mock LLM"""
    mock_client = MagicMock()
    mock_client.generate.return_value = "Formation program"
    mock_llm.return_value = mock_client

    agent = FormationGeneratorAgent()
    result = agent.generate(topic="Python", duration="3 jours", audience="Devs")

    assert result == "Formation program"
    mock_client.generate.assert_called_once()
```

### 3. Tester les erreurs

```python
def test_generate_with_empty_topic_raises_error():
    """Test que topic vide lève ValueError"""
    agent = FormationGeneratorAgent()

    with pytest.raises(ValueError, match="Topic cannot be empty"):
        agent.generate(topic="", duration="1 jour", audience="Test")
```

### 4. Utiliser des fixtures

```python
@pytest.fixture
def llm_client():
    """Fixture pour LLMClient mocké"""
    with patch('agents.formation_generator.LLMClient') as mock:
        yield mock

def test_with_fixture(llm_client):
    """Test utilisant fixture"""
    agent = FormationGeneratorAgent()
    assert agent is not None
```

---

## Debugging Tests

### Exécuter en mode verbose

```bash
# Verbose + traceback complet
pytest tests/ -vv --tb=long

# Arrêter au premier échec
pytest tests/ -x

# Afficher print statements
pytest tests/ -s
```

### Debugger avec pdb

```python
def test_my_function():
    import pdb; pdb.set_trace()  # Point d'arrêt
    result = my_function()
    assert result == expected
```

### Debugger avec ipdb

```bash
# Installer ipdb
pip install ipdb

# Dans le test
import ipdb; ipdb.set_trace()
```

---

## FAQ

### Q: Les tests échouent avec "ModuleNotFoundError"
**R:** Vérifier que le venv est activé et que les dépendances sont installées :
```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Q: Pre-commit hooks trop lents
**R:** Désactiver temporairement certains hooks :
```yaml
# Dans .pre-commit-config.yaml, commenter les hooks lents
# - repo: local
#   hooks:
#     - id: pytest  # Commenté temporairement
```

### Q: Couverture de code insuffisante
**R:** Identifier les fichiers non couverts et ajouter des tests :
```bash
pytest --cov=agents --cov=utils --cov-report=term-missing
```

### Q: Tests de sécurité échouent
**R:** Vérifier les rapports Bandit et Safety :
```bash
bandit -r agents utils app.py -f json -o bandit-report.json
safety check --json
```

---

## Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Code Style](https://black.readthedocs.io/)
- [Bandit Security](https://bandit.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**✨ Happy Testing!**
