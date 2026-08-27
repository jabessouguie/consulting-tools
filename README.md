# 🎨 Consulting Tools

Suite d'outils IA pour consultants : génération de contenus, automatisation, et intégrations cloud.

![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![Tests](https://img.shields.io/badge/tests-1777%20passing-success.svg)
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

```bash
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
.venv/bin/python3 -m uvicorn app:app --reload
```

Application accessible : **http://localhost:8000**
(ou **https://localhost:8443** si les certificats SSL sont présents dans `ssl/`)

---

## ⚙️ Configuration

### Variables d'Environnement (.env)

```bash
CONSULTANT_NAME="Votre Nom"
COMPANY_NAME="Votre Entreprise"
ANTHROPIC_API_KEY=votre_cle_claude
GOOGLE_APPLICATION_CREDENTIALS=config/google_credentials.json
LINKEDIN_CLIENT_ID=votre_id
LINKEDIN_CLIENT_SECRET=votre_secret
```

Voir [INSTALL_GUIDE.md](INSTALL_GUIDE.md) pour la configuration complète.

---

## 🤖 Utilisation avec Antigravity

Antigravity est votre assistant de développement intégré. Vous pouvez l'utiliser pour automatiser vos tâches quotidiennes.

### Commandes Courantes
- **"Antigravity, lance l'application"** : Démarre le serveur FastAPI.
- **"Génère une proposition pour [Client] sur [Sujet]"** : Automatise la création de PPTX.
- **"Vérifie la qualité du code"** : Lance les hooks de pre-commit.
- **"Ajoute un nouvel agent pour [Fonctionnalité]"** : Aide à l'extension du framework.

### Pourquoi utiliser Antigravity ?
- **Vitesse** : Pas besoin de se souvenir des commandes Bash complexes.
- **Fiabilité** : Il respecte les standards du projet (PEP8, Pre-commit).
- **Proactivité** : Il peut suggérer des améliorations ou corriger des bugs de configuration.

---

## 💻 Utilisation Classique (Manuelle)

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
| [CLAUDE.md](CLAUDE.md) | Règles d'architecture, commandes, conventions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Comment contribuer, exigences de tests |
| [INSTALL_GUIDE.md](INSTALL_GUIDE.md) | Installation détaillée pas à pas |
| [GUIDE_UTILISATEUR.md](GUIDE_UTILISATEUR.md) | Prise en main sans compétence technique |
| [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) | Architecture interne et extension |
| [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) | Guide CI/CD |
| [SECURITY_REVIEW.md](SECURITY_REVIEW.md) | Audit de sécurité et mesures en place |
| [docs/](docs/) | Guides thématiques (images, SSL, mail, Imagen) |

Les journaux de chantier historiques (correctifs datés, récapitulatifs de
livraison) sont conservés dans [docs/archive/](docs/archive/) — ils décrivent
des états passés du projet et ne doivent pas servir de référence.

### Scripts

```bash
./validate.sh    # Validation complète
./start.sh       # Démarrage avec fix lxml
.venv/bin/python3 -m pytest tests/ -q   # Tests unitaires
```

---

## 🧪 Tests

```bash
# Suite complète
.venv/bin/python3 -m pytest tests/ -q --tb=short

# Un module ciblé
.venv/bin/python3 -m pytest tests/test_llm_client.py -v

# Avec rapport de couverture HTML
.venv/bin/python3 -m pytest tests/ --cov=agents --cov=utils --cov-report=html
```

**Résultats au 27/08/2026** : 1777 tests passent, 7 échouent.

> ⚠️ La couverture affichée (87 %) ne porte que sur `agents/` et `utils/`.
> La couche HTTP (`routers/`, `app.py` — ~9 500 lignes) n'est pas encore
> instrumentée : voir `pytest.ini`. Le chiffre global réel est donc plus bas.

Les 7 échecs connus : dépendance `openpyxl` absente (2), tests lisant le `.env`
réel au lieu d'un environnement isolé (4), collecte veille (1).

---

## 🐛 Dépannage

### Génération slides ne fonctionne plus

**Cause** : Python 3.14 + lxml incompatibilité

**Solution** :
```bash
brew install python@3.13
mv .venv .venv_backup
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google API non configurée

1. Télécharger google_credentials.json depuis GCP
2. Placer dans config/google_credentials.json
3. Supprimer config/token.pickle
4. Re-authentifier

### LinkedIn pas connecté

```bash
open http://localhost:8000/auth/linkedin
# Copier token dans .env
```

---

## 🏗️ Architecture

**Stack** : FastAPI + Jinja2 + Tailwind CSS + Claude AI + Gemini

**Structure** :
```
consulting-tools/
├── app.py                 # Assemblage FastAPI + middlewares (216 lignes)
├── routers/               # Toutes les routes, par domaine (26 modules)
│   └── shared.py          # jobs, limiter, templates, helpers communs
├── agents/                # Agents IA (23 modules)
├── utils/                 # Clients et outils (Gmail, LinkedIn, Google, LLM, DB)
├── config/                # Configuration consultant
├── templates/             # 29 templates Jinja2
├── static/                # CSS/JS
├── tests/                 # 53 fichiers de tests
├── .github/workflows/     # CI/CD (2 workflows)
└── docs/                  # Documentation thématique
```

> Toute nouvelle route va dans `routers/<domaine>.py`, jamais dans `app.py`.
> Voir [CLAUDE.md](CLAUDE.md) pour les règles d'architecture.

---

## 📊 Statistiques

```
📁 Fichiers suivis : 283
📝 Code applicatif : ~29 700 lignes (agents, utils, routers, app)
🧪 Tests : 1777 passent / 7 échouent — 53 fichiers, ~23 400 lignes
🎨 Templates : 29 écrans Jinja2
📚 Docs : 6 guides thématiques dans docs/
⚙️ GitHub Actions : 2 workflows
🔗 APIs : Gmail, LinkedIn, Google Docs/Slides, Microsoft Graph
```

*Chiffres mesurés le 27/08/2026.*

---

## 📄 License

MIT License

---

## 📞 Support

- **Documentation** : [docs/](docs/)
- **Issues** : GitHub Issues

---

Développé avec ❤️ pour **Consulting Tools**
