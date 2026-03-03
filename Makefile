.PHONY: help install test test-unit test-integration test-security test-cov lint format clean pre-commit setup-hooks

help:
	@echo "Commandes disponibles:"
	@echo "  make install         - Installer toutes les dépendances"
	@echo "  make setup-hooks     - Configurer pre-commit hooks"
	@echo "  make test            - Exécuter tous les tests"
	@echo "  make test-unit       - Exécuter tests unitaires uniquement"
	@echo "  make test-integration- Exécuter tests d'intégration uniquement"
	@echo "  make test-security   - Exécuter tests de sécurité uniquement"
	@echo "  make test-cov        - Exécuter tests avec rapport de couverture"
	@echo "  make lint            - Vérifier qualité du code (flake8, mypy, bandit)"
	@echo "  make format          - Formater le code (black, isort)"
	@echo "  make clean           - Nettoyer fichiers temporaires"
	@echo "  make security-scan   - Scanner vulnérabilités (bandit + safety)"

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup-hooks:
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installés"

test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

test-security:
	pytest tests/test_security.py -v

test-cov:
	pytest tests/ --cov=agents --cov=utils --cov-report=html --cov-report=term-missing
	@echo "✅ Rapport de couverture généré dans htmlcov/index.html"

lint:
	@echo "🔍 Linting avec flake8..."
	flake8 agents utils app.py --max-line-length=100 --extend-ignore=E203,W503
	@echo "🔍 Type checking avec mypy..."
	mypy agents utils app.py --ignore-missing-imports --python-version=3.13
	@echo "🔍 Security scan avec bandit..."
	bandit -r agents utils app.py -ll
	@echo "✅ Linting terminé"

format:
	@echo "🎨 Formatage avec black..."
	black agents utils app.py tests --line-length=100
	@echo "🎨 Tri des imports avec isort..."
	isort agents utils app.py tests --profile=black --line-length=100
	@echo "✅ Formatage terminé"

security-scan:
	@echo "🔒 Scan de sécurité avec bandit..."
	bandit -r agents utils app.py -ll -f json -o bandit-report.json
	@echo "🔒 Vérification vulnérabilités avec safety..."
	safety check --json
	@echo "✅ Security scan terminé"

clean:
	@echo "🧹 Nettoyage..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf build/ dist/
	@echo "✅ Nettoyage terminé"

validate:
	@echo "✅ Validation complète du projet..."
	make format
	make lint
	make test-cov
	make security-scan
	@echo "✅✅✅ Validation terminée avec succès !"

ci:
	@echo "🚀 Simulation CI/CD..."
	make lint
	make test
	@echo "✅ CI simulation terminée"
