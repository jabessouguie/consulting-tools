# 🚀 Guide d'installation - Consulting Tools Consulting Tools

**Bienvenue !** Ce guide vous aidera à installer et configurer les outils de consulting en **5 minutes**.

---

## 📋 Prérequis

- **Python 3.10+** installé ([télécharger ici](https://www.python.org/downloads/))
- **Git** installé (optionnel, pour cloner le repo)
- Compte **Anthropic** (Claude API) OU **Google** (Gemini API)

---

## ⚡ Installation rapide (5 min)

### 1. Cloner le projet

```bash
git clone https://github.com/votre-repo/consulting-tools.git
cd consulting-tools
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer vos informations personnelles

#### a) Créer votre fichier `.env`

**Sur Mac/Linux** :
```bash
cp .env.example .env
```

**Sur Windows (PowerShell)** :
```powershell
Copy-Item .env.example .env
```

**Ou manuellement** : Dupliquez le fichier `.env.example` et renommez la copie en `.env`

#### b) Éditer `.env` avec vos informations

**Avec un éditeur de texte** (choisissez selon votre système) :

**Option 1 - Éditeur en ligne de commande (nano - simple)** :
```bash
nano .env
# Éditez le fichier, puis Ctrl+X pour sauvegarder
```

**Option 2 - Éditeur système (plus visuel)** :
```bash
# Mac
open -e .env

# Linux avec gedit
gedit .env

# Windows
notepad .env
```

**Option 3 - Votre IDE favori** :
- VS Code : `code .env`
- Cursor : `cursor .env`
- Autre IDE : ouvrez le fichier `.env` depuis votre IDE

**Configurez au minimum ces variables** :

```bash
# === OBLIGATOIRE ===
CONSULTANT_NAME=Votre Nom Complet
CONSULTANT_TITLE=Votre titre professionnel (ex: Consultant Data & IA)
COMPANY_NAME=Votre entreprise

# === OBLIGATOIRE : Clé API ===
# Option 1 : Claude (recommandé)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Option 2 : Gemini (alternative gratuite)
GEMINI_API_KEY=AIzaxxxxx
USE_GEMINI=true

# === SÉCURITÉ : Changez le mot de passe ===
AUTH_PASSWORD=votre-mot-de-passe-fort-ici
```

**⚠️ IMPORTANT** : Si vous ne changez pas `AUTH_PASSWORD`, vous verrez un avertissement au démarrage.

#### c) Ajouter vos données LinkedIn (optionnel mais recommandé)

Pour que les articles générés correspondent à votre style :

**1. Créez le dossier**

**Mac/Linux** :
```bash
mkdir -p data/linkedin_profile
```

**Windows (PowerShell)** :
```powershell
New-Item -ItemType Directory -Force -Path data\linkedin_profile
```

**Ou manuellement** : Créez un dossier `linkedin_profile` dans le dossier `data`

**2. Créez votre profil LinkedIn**

**Méthode A - Ligne de commande (Mac/Linux)** :
```bash
cat > data/linkedin_profile/profile.json << 'EOF'
{
  "name": "Votre Nom",
  "title": "Votre titre LinkedIn",
  "company": "Votre entreprise",
  "bio": "Votre bio LinkedIn (1-2 phrases)",
  "experiences": [
    {
      "title": "Consultant Senior",
      "company": "Société X",
      "duration": "2020-2024",
      "description": "Description de votre rôle..."
    }
  ]
}
EOF
```

**Méthode B - Ligne de commande (Windows PowerShell)** :
```powershell
@"
{
  "name": "Votre Nom",
  "title": "Votre titre LinkedIn",
  "company": "Votre entreprise",
  "bio": "Votre bio LinkedIn (1-2 phrases)"
}
"@ | Out-File -Encoding utf8 data\linkedin_profile\profile.json
```

**Méthode C - Éditeur de texte** :
1. Créez un nouveau fichier nommé `profile.json` dans `data/linkedin_profile/`
2. Copiez-collez le contenu JSON ci-dessus
3. Remplacez "Votre Nom", "Votre titre", etc. par vos vraies informations
4. Sauvegardez

**3. Créez votre persona LinkedIn**

**Méthode A - Ligne de commande (Mac/Linux)** :
```bash
cat > data/linkedin_profile/persona.md << 'EOF'
# Mon style LinkedIn

## Ton
- Expert mais accessible
- Critique constructif
- Pédagogue

## Thématiques favorites
- ROI de l'IA
- Gouvernance des données
- GenAI en entreprise

## Expressions typiques
- "Pragmatisme avant hype"
- "L'IA n'est pas magique"
EOF
```

**Méthode B - Éditeur de texte** :
1. Créez un fichier `persona.md` dans `data/linkedin_profile/`
2. Copiez le contenu markdown ci-dessus
3. Personnalisez avec votre style
4. Sauvegardez

**4. (Optionnel) Ajoutez vos meilleurs posts**

```bash
# Mac/Linux
mkdir -p data/linkedin_profile/posts

# Windows PowerShell
New-Item -ItemType Directory -Force -Path data\linkedin_profile\posts
```

Puis créez un fichier `.md` par post (ex: `post_1.md`, `post_2.md`)

**✅ Ces fichiers sont protégés** : ils ne seront JAMAIS poussés sur Git (dans `.gitignore`)

### 4. Créer votre fichier de personnalité (optionnel)

**Note** : Ce fichier sera créé automatiquement au premier lancement avec un template par défaut. Vous pouvez le personnaliser ensuite.

**Pour le créer manuellement maintenant** :

**Méthode A - Ligne de commande (Mac/Linux)** :
```bash
cat > data/personality.md << 'EOF'
# Personnalité et Convictions

## Vision
- L'IA doit être au service de l'humain
- Pragmatisme avant hype
- Éthique et gouvernance indissociables

## Style d'écriture
- Ton expert mais accessible
- Critique constructif avec exemples réels
- Pédagogie sans simplification excessive

## Convictions clés
- L'IA générative nécessite stratégie et gouvernance
- La qualité des données est cruciale
- Le consulting doit être orienté impact
EOF
```

**Méthode B - Éditeur de texte** :
1. Créez un fichier `personality.md` dans le dossier `data/`
2. Copiez le contenu markdown ci-dessous
3. Personnalisez avec vos vraies convictions
4. Sauvegardez

**Contenu du fichier** :
```markdown
# Personnalité et Convictions

## Vision
- L'IA doit être au service de l'humain
- Pragmatisme avant hype
- Éthique et gouvernance indissociables

## Style d'écriture
- Ton expert mais accessible
- Critique constructif avec exemples réels
- Pédagogie sans simplification excessive

## Convictions clés
- L'IA générative nécessite stratégie et gouvernance
- La qualité des données est cruciale
- Le consulting doit être orienté impact
```

### 5. Vérifier l'installation (recommandé)

Avant de lancer l'app, vérifiez que tout est bien configuré :

```bash
python check_install.py
```

Ce script vérifie automatiquement :
- ✅ Version Python (3.10+)
- ✅ Dépendances installées
- ✅ Fichier `.env` existe et configuré
- ✅ Variables obligatoires présentes
- ✅ Structure des dossiers

**Si tout est OK, vous verrez** :
```
Score : 6/6
✨ Installation complète ! Vous pouvez lancer l'application
```

**Si des ❌ apparaissent** : consultez la section **Dépannage** ci-dessous.

---

### 6. Lancer l'application

**Ligne de commande** :
```bash
python app.py
```

**Ou avec python3** (si `python` ne fonctionne pas) :
```bash
python3 app.py
```

Vous devriez voir :
```
==================================================
  Consulting Tools Agents - Interface Web
  http://localhost:8000
  ⚠️  HTTP uniquement (pas de SSL)
==================================================
```

**Accéder à l'application** :
1. Ouvrez votre navigateur web (Chrome, Firefox, Safari, Edge...)
2. Allez à l'adresse : **http://localhost:8000**
3. L'interface web s'affiche ✅

**Arrêter l'application** :
- Appuyez sur `Ctrl+C` dans le terminal

---

## 🔐 Sécurité - Points importants

### ✅ Bonnes pratiques

1. **Mot de passe fort** : Changez `AUTH_PASSWORD` dans `.env`
2. **API Keys privées** : Ne commitez JAMAIS votre `.env`
3. **LinkedIn privé** : Vos données dans `data/linkedin_profile/` sont protégées

### ⚠️ Fichiers à ne JAMAIS commiter

Ces fichiers sont déjà dans `.gitignore` :
- `.env` (vos clés API)
- `data/linkedin_profile/` (vos données LinkedIn)
- `data/linkedin_profile.json`
- `data/linkedin_persona.md`

---

## 🎯 Premiers pas après l'installation

### 1. Tester la génération d'articles

1. Allez dans **Document Editor**
2. Sélectionnez "Article"
3. Entrez un sujet (ex: "ROI de l'IA en entreprise")
4. Cochez "Contexte enrichi" pour utiliser votre profil LinkedIn
5. Cliquez "Générer"

### 2. Créer une présentation

1. Allez dans **Slide Editor**
2. Choisissez le type (Formation, Proposition, REX)
3. Entrez le sujet
4. Définissez l'audience
5. Générez les slides

### 3. Générer un script de présentation

1. Allez dans **Document Editor**
2. Sélectionnez "Script de Présentation"
3. Uploadez votre PowerPoint (.pptx)
4. Obtenez le script oral pour chaque slide

---

## 🛠️ Configuration avancée

### Utiliser Gemini au lieu de Claude

Dans `.env` :
```bash
USE_GEMINI=true
GEMINI_API_KEY=AIzaxxxxx
GEMINI_MODEL=models/gemini-2.5-flash
```

### Activer HTTPS (certificat auto-signé)

```bash
mkdir ssl
# Générer certificat (commande dépend de votre OS)
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

L'app détectera automatiquement les certificats et démarrera en HTTPS.

### Configurer la veille tech

Dans `.env` :
```bash
RSS_FEEDS=https://feeds.feedburner.com/blogspot/gJZg,https://openai.com/blog/rss.xml
VEILLE_KEYWORDS=Intelligence Artificielle,Data Science,GenAI
VEILLE_FREQUENCY_HOURS=24
```

---

## ❓ Dépannage

### Erreur : "CONSULTANT_NAME non configuré"

**Symptôme** :
```
❌ ERREUR DE CONFIGURATION
CONSULTANT_NAME non configure dans votre fichier .env
```

➡️ **Solution** :
1. Ouvrez le fichier `.env` (voir section 3.b ci-dessus pour comment l'ouvrir)
2. Trouvez la ligne `CONSULTANT_NAME=...`
3. Remplacez par votre nom : `CONSULTANT_NAME=Jean Dupont`
4. Sauvegardez le fichier
5. Relancez l'application

### Erreur : "No API key found"

**Symptôme** :
```
Error: No Anthropic API key found
```

➡️ **Solution** :
1. Ouvrez `.env`
2. Ajoutez votre clé API :
   ```bash
   # Option 1 : Claude
   ANTHROPIC_API_KEY=sk-ant-xxxxx

   # Option 2 : Gemini (gratuit)
   GEMINI_API_KEY=AIzaxxxxx
   USE_GEMINI=true
   ```
3. Sauvegardez et relancez

**Comment obtenir une clé API ?**
- **Claude** : https://console.anthropic.com/settings/keys
- **Gemini** : https://aistudio.google.com/apikey

### Warning : "Mot de passe par défaut détecté"

**Symptôme** :
```
🚨 SECURITE : Mot de passe par defaut detecte !
```

➡️ **Solution** :
1. Ouvrez `.env`
2. Trouvez `AUTH_PASSWORD=CHANGE_ME_ON_FIRST_INSTALL`
3. Remplacez par un mot de passe fort : `AUTH_PASSWORD=MonMotDePasseFort2024!`
4. Sauvegardez et relancez

### L'application ne démarre pas

**1. Vérifier la version de Python**
```bash
python --version
# Ou
python3 --version
```
➡️ Doit afficher Python 3.10 ou supérieur

**Si Python n'est pas installé** :
- Téléchargez sur https://www.python.org/downloads/
- Cochez "Add Python to PATH" pendant l'installation (Windows)

**2. Réinstaller les dépendances**
```bash
pip install -r requirements.txt --upgrade
# Ou
pip3 install -r requirements.txt --upgrade
```

**3. Vérifier que le port 8000 est libre**

**Mac/Linux** :
```bash
lsof -i :8000
# Si occupé, tuez le process :
kill -9 <PID>
```

**Windows PowerShell** :
```powershell
netstat -ano | findstr :8000
# Si occupé, tuez le process :
taskkill /PID <PID> /F
```

**Ou changez le port** dans `app.py` (ligne ~5470) :
```python
port = 8080  # Au lieu de 8000
```

### Erreur : "ModuleNotFoundError"

**Symptôme** :
```
ModuleNotFoundError: No module named 'fastapi'
```

➡️ **Solution** :
```bash
pip install -r requirements.txt
```

Si ça ne fonctionne toujours pas, installez individuellement :
```bash
pip install fastapi uvicorn anthropic google-generativeai python-pptx python-docx PyPDF2 openpyxl pandas numpy feedparser beautifulsoup4 requests python-dotenv slowapi starlette
```

### Le fichier `.env` n'existe pas

➡️ **Solution** :
1. Vérifiez que vous êtes dans le bon dossier :
   ```bash
   pwd  # Mac/Linux
   cd   # Windows
   ```
   Vous devriez être dans `consulting-tools/`

2. Listez les fichiers :
   ```bash
   ls -la  # Mac/Linux
   dir     # Windows
   ```
   Vous devriez voir `.env.example`

3. Créez `.env` :
   ```bash
   cp .env.example .env  # Mac/Linux
   Copy-Item .env.example .env  # Windows PowerShell
   ```

---

## 📚 Documentation complète

- **Guide utilisateur** : `GUIDE_UTILISATEUR.md`
- **Documentation technique** : `TECHNICAL_GUIDE.md`
- **Revue de sécurité** : `SECURITY_REVIEW.md`
- **Onboarding des données** : `data/README_ONBOARDING.md`

---

## 🆘 Support

**Problème d'installation ?** Ouvrez une issue sur GitHub avec :
- Votre version de Python (`python --version`)
- Le message d'erreur complet
- Votre système d'exploitation

---

## 🎉 Félicitations !

Vous êtes prêt à utiliser les outils de consulting !

**Prochaines étapes recommandées** :
1. ✅ Remplir `data/personality.md` avec vos vraies convictions
2. ✅ Ajouter votre profil LinkedIn dans `data/linkedin_profile/`
3. ✅ Générer votre premier article pour tester
4. ✅ Explorer les différents agents (Veille, Formation, Proposition...)

**Bon consulting ! 🚀**
