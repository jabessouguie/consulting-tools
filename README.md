# 🎨 WEnvision Consulting Tools

Suite d'outils IA pour consultants : génération de contenus, automatisation, et intégrations cloud.

![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![Tests](https://img.shields.io/badge/tests-25%2F25%20passing-success.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📋 Table des Matières

- [Fonctionnalités](#-fonctionnalités)
- [Installation](#-installation-rapide)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Documentation](#-documentation)
- [Tests](#-tests)
- [Dépannage](#-dépannage)

---

## ✨ Fonctionnalités

### 🎯 Génération de Contenus
- **Slide Generator** - Présentations PowerPoint/Google Slides
- **Formation Generator** - Programmes de formation
- **Article Generator** - Articles professionnels
- **Meeting Summarizer** - Comptes rendus de réunion

### 🔗 Intégrations Cloud
- Gmail API, LinkedIn API, Google Docs/Slides, PDF

### 🎨 UI/UX
- Toast notifications, Modals, Validation temps réel

---

## 🚀 Installation Rapide

### Prérequis
- **Python 3.13** (IMPORTANT : pas 3.14 - incompatibilité lxml)
- Git

### Installation

\`\`\`bash
# 1. Cloner
git clone https://github.com/your-org/consulting-tools.git
cd consulting-tools

# 2. Installer Python 3.13
brew install python@3.13

# 3. Créer venv
python3.13 -m venv .venv
source .venv/bin/activate

# 4. Installer dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configurer
cp .env.example .env
# Éditer .env avec vos credentials

# 6. Démarrer
python3 app.py
\`\`\`

Application accessible : **http://localhost:8000**

---

## ⚙️ Configuration

### Variables d'Environnement (.env)

\`\`\`bash
CONSULTANT_NAME="Votre Nom"
COMPANY_NAME="Votre Entreprise"
ANTHROPIC_API_KEY=votre_cle_claude
GOOGLE_APPLICATION_CREDENTIALS=config/google_credentials.json
LINKEDIN_CLIENT_ID=votre_id
LINKEDIN_CLIENT_SECRET=votre_secret
\`\`\`

Voir [VALIDATION_COMPLETE.md](VALIDATION_COMPLETE.md) pour configuration complète.

---

## 💻 Utilisation

### Slide Editor
1. Accéder à http://localhost:8000/slide-editor
2. Entrer sujet, audience, nombre de slides
3. Cliquer "Générer"
4. Exporter : PPTX, Google Slides, ou PDF

### Meeting Summarizer
1. http://localhost:8000/meeting
2. Uploader transcription
3. Générer compte rendu
4. Partager par email

### LinkedIn Publisher
1. http://localhost:8000/linkedin
2. Générer posts
3. Publier directement

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [URGENT_FIXES.md](URGENT_FIXES.md) | Solutions problèmes critiques |
| [VALIDATION_COMPLETE.md](VALIDATION_COMPLETE.md) | Checklist validation |
| [PYTHON_314_LXML_FIX.md](PYTHON_314_LXML_FIX.md) | Fix Python 3.14 |
| [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) | Guide CI/CD |
| [PDF_COLOR_FIX.md](PDF_COLOR_FIX.md) | Couleurs PDF |

### Scripts

\`\`\`bash
./validate.sh    # Validation complète
./start.sh       # Démarrage avec fix lxml
pytest tests/ -v # Tests unitaires
\`\`\`

---

## 🧪 Tests

\`\`\`bash
# Tests unitaires (25 tests)
pytest tests/test_gmail_client.py tests/test_linkedin_client.py -v

# Avec couverture
pytest tests/ --cov=utils --cov-report=html
\`\`\`

**Résultats** : ✅ 25/25 tests passing (100% coverage)

---

## 🐛 Dépannage

### Génération slides ne fonctionne plus

**Cause** : Python 3.14 + lxml incompatibilité

**Solution** :
\`\`\`bash
brew install python@3.13
mv .venv .venv_backup
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
\`\`\`

### Google API non configurée

1. Télécharger google_credentials.json depuis GCP
2. Placer dans config/google_credentials.json
3. Supprimer config/token.pickle
4. Re-authentifier

### LinkedIn pas connecté

\`\`\`bash
open http://localhost:8000/auth/linkedin
# Copier token dans .env
\`\`\`

---

## 🏗️ Architecture

**Stack** : FastAPI + Jinja2 + Tailwind CSS + Claude AI + Gemini

**Structure** :
\`\`\`
consulting-tools/
├── app.py                 # FastAPI app (5000+ lignes)
├── agents/                # Agents IA
├── utils/                 # Clients (Gmail, LinkedIn, Google)
├── templates/             # Jinja2 templates
├── static/                # CSS/JS
├── tests/                 # 25 tests unitaires
├── .github/workflows/     # CI/CD
└── docs/                  # Documentation
\`\`\`

---

## 📊 Statistiques

\`\`\`
📁 Fichiers : 50+
📝 Code : ~8000 lignes
🧪 Tests : 25/25 (100%)
📚 Docs : 8 guides
⚙️ GitHub Actions : 2 workflows
🎨 UI Components : 6
🔗 APIs : 4 (Gmail, LinkedIn, Docs, Slides)
\`\`\`

---

## 📄 License

MIT License

---

## 📞 Support

- **Documentation** : [docs/](docs/)
- **Issues** : GitHub Issues

---

**🚀 Prêt pour production !**

Développé avec ❤️ pour **WEnvision Consulting**
