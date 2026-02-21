# 🚀 GitHub Actions - Guide Complet

## 📊 Workflows Implémentés

### 1. **CI/CD Pipeline** (.github/workflows/ci.yml)

Exécuté automatiquement sur chaque push et pull request.

#### Jobs Inclus

| Job | Description | Durée | Critique |
|-----|-------------|-------|----------|
| **test** | Tests unitaires (25 tests) | ~2min | ✅ Oui |
| **lint** | Code quality (flake8, black, isort) | ~1min | ⚠️ Warning only |
| **security** | Scan sécurité (bandit) | ~1min | ⚠️ Warning only |
| **dependencies** | Vulnerabilités dépendances (safety) | ~1min | ⚠️ Warning only |
| **build** | Validation build + imports | ~2min | ✅ Oui |
| **docker** | Build image Docker (main only) | ~3min | ❌ Non |
| **notify** | Notification status | ~10s | ❌ Non |

**Total** : ~7-10 minutes par run

### 2. **Deployment Pipeline** (.github/workflows/deploy.yml)

Exécuté manuellement ou lors d'une release GitHub.

#### Steps

1. Checkout code
2. Setup Python 3.13
3. Install dependencies
4. Run tests (validation)
5. Deploy via SSH
6. Restart service

---

## ⚙️ Configuration Requise

### Secrets GitHub à configurer

Aller dans : **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Description | Exemple |
|--------|-------------|---------|
| `CODECOV_TOKEN` | Token Codecov pour coverage | `abc123...` |
| `DEPLOY_HOST` | IP/hostname serveur production | `192.168.1.100` |
| `DEPLOY_USER` | User SSH pour déploiement | `wenvision` |
| `DEPLOY_SSH_KEY` | Clé SSH privée pour déploiement | `-----BEGIN RSA PRIVATE KEY-----...` |

### Variables d'environnement (optionnel)

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `PYTHON_VERSION` | Version Python pour CI | `3.13` |
| `CODECOV_THRESHOLD` | Seuil minimum coverage | `80%` |

---

## 🔧 Setup Initial

### 1. Activer GitHub Actions

```bash
# 1. Push workflows vers GitHub
git add .github/workflows/
git commit -m "Add GitHub Actions CI/CD"
git push origin main

# 2. Vérifier que les workflows sont activés
# Aller sur GitHub → Actions
```

### 2. Configurer Codecov (Coverage Reports)

```bash
# 1. Créer compte sur codecov.io
# 2. Lier repo GitHub
# 3. Copier token
# 4. Ajouter secret CODECOV_TOKEN dans GitHub
```

### 3. Configurer SSH pour Deployment

```bash
# 1. Générer clé SSH
ssh-keygen -t rsa -b 4096 -C "deploy@wenvision-tools"

# 2. Copier clé publique sur serveur
ssh-copy-id wenvision@your-server.com

# 3. Ajouter clé privée dans DEPLOY_SSH_KEY (GitHub secret)
cat ~/.ssh/id_rsa | pbcopy  # macOS
cat ~/.ssh/id_rsa | xclip   # Linux

# 4. Tester connexion
ssh wenvision@your-server.com
```

---

## 📖 Utilisation

### Trigger automatique (CI)

```bash
# 1. Créer branche
git checkout -b feature/new-feature

# 2. Faire modifications
git add .
git commit -m "Add new feature"

# 3. Push (déclenche CI automatiquement)
git push origin feature/new-feature

# 4. Créer Pull Request sur GitHub
# → CI s'exécute automatiquement
# → Tous les checks doivent passer avant merge
```

### Trigger manuel (Deployment)

```bash
# Option 1 : Via interface GitHub
# 1. Aller sur Actions → Deploy to Production
# 2. Cliquer "Run workflow"
# 3. Sélectionner branche (main)
# 4. Cliquer "Run workflow"

# Option 2 : Via release GitHub
# 1. Créer tag
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 2. Créer release sur GitHub
# → Deployment se déclenche automatiquement
```

### Monitoring

```bash
# Voir status workflows
# GitHub → Actions → Recent workflow runs

# Télécharger artifacts (rapports)
# GitHub → Actions → Workflow run → Artifacts

# Voir logs détaillés
# GitHub → Actions → Workflow run → Job → Step
```

---

## 🎯 Best Practices

### 1. Branches

```
main (protected)
├── develop (protected)
│   ├── feature/gmail-integration
│   ├── feature/linkedin-api
│   └── bugfix/pdf-colors
└── hotfix/critical-bug
```

**Règles** :
- `main` : Toujours stable, déploiement production
- `develop` : Tests d'intégration
- `feature/*` : Nouvelles fonctionnalités
- `bugfix/*` : Corrections de bugs
- `hotfix/*` : Urgences production

### 2. Protected Branches

**Settings → Branches → Add rule**

Pour `main` et `develop` :
- ✅ Require pull request before merging
- ✅ Require approvals (1+)
- ✅ Require status checks to pass
  - `test (3.13)`
  - `build`
- ✅ Require branches to be up to date
- ✅ Do not allow bypassing

### 3. Commit Messages

Suivre [Conventional Commits](https://www.conventionalcommits.org/) :

```
feat: add Gmail API integration
fix: resolve PDF color export issue
docs: update VALIDATION_COMPLETE.md
test: add LinkedInClient unit tests
chore: update dependencies
refactor: improve slide generation logic
perf: optimize LLM streaming
```

### 4. Pull Request Template

Créer `.github/pull_request_template.md` :

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist
- [ ] Tests pass locally
- [ ] Added/updated tests
- [ ] Documentation updated
- [ ] No linter errors
- [ ] Branch up-to-date with main
```

---

## 🐛 Troubleshooting

### Tests échouent sur CI mais passent localement

**Problème** : Différences Python version ou dépendances

**Solution** :
```bash
# Utiliser même Python version que CI (3.13)
python3.13 -m venv .venv_ci
source .venv_ci/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

### lxml import error sur CI

**Problème** : Python 3.14 incompatible

**Solution** : Workflow déjà configuré pour Python 3.13 ✅

### Deployment SSH timeout

**Problème** : Clé SSH invalide ou firewall

**Solution** :
```bash
# Tester connexion manuellement
ssh -v wenvision@your-server.com

# Vérifier firewall
sudo ufw status
sudo ufw allow 22/tcp
```

### Codecov upload fails

**Problème** : Token invalide

**Solution** :
```bash
# Régénérer token sur codecov.io
# Mettre à jour GitHub secret CODECOV_TOKEN
```

---

## 📊 Status Badges

Ajouter dans `README.md` :

```markdown
![CI Status](https://github.com/your-org/consulting-tools/workflows/CI%2FCD%20-%20WEnvision%20Consulting%20Tools/badge.svg)
![Tests](https://img.shields.io/github/actions/workflow/status/your-org/consulting-tools/ci.yml?label=tests)
![Coverage](https://codecov.io/gh/your-org/consulting-tools/branch/main/graph/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
```

---

## 🔄 Workflow Diagram

```
┌─────────────────┐
│   git push      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│          GitHub Actions Trigger         │
└────────┬────────────────────────────────┘
         │
         ├──► test (Python 3.13)
         │     ├─ Install deps
         │     ├─ Run pytest
         │     └─ Upload coverage
         │
         ├──► lint
         │     ├─ flake8
         │     ├─ black
         │     └─ isort
         │
         ├──► security
         │     └─ bandit scan
         │
         ├──► dependencies
         │     └─ safety check
         │
         ├──► build
         │     ├─ Syntax validation
         │     └─ Import tests
         │
         └──► notify
               └─ Status report
```

---

## 💡 Workflows Additionnels (Optionnel)

### 1. Auto-merge Dependabot PRs

`.github/workflows/auto-merge.yml`

```yaml
name: Auto-merge Dependabot PRs
on: pull_request

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - name: Merge PR
        uses: pascalgn/automerge-action@v0.15.6
        env:
          GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
```

### 2. Release Notes Generator

`.github/workflows/release-notes.yml`

```yaml
name: Generate Release Notes
on:
  release:
    types: [published]

jobs:
  release-notes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: release-drafter/release-drafter@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 3. Dependency Update Check

`.github/workflows/dependencies-update.yml`

```yaml
name: Check Dependencies
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday

jobs:
  update-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip list --outdated
```

---

## ✅ Checklist Finale

Avant de pousser en production :

- [ ] `.github/workflows/ci.yml` créé
- [ ] `.github/workflows/deploy.yml` créé
- [ ] GitHub secrets configurés (CODECOV_TOKEN, DEPLOY_*)
- [ ] Protected branches activées (main + develop)
- [ ] Pull request template créé
- [ ] Status badges ajoutés au README
- [ ] Tests passent sur CI
- [ ] Codecov configuré et fonctionnel
- [ ] Deployment testé manuellement
- [ ] Documentation à jour

---

## 📚 Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Protected Branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)

---

**✨ GitHub Actions configuré et prêt à l'emploi !**
