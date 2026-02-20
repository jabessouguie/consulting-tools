# 🚀 WEnvision Consulting Tools

Suite d'outils d'Intelligence Artificielle pour automatiser la création de contenus et présentations professionnelles chez WEnvision.

## 📋 Vue d'ensemble

Application web FastAPI avec agents IA pour la génération automatique de :

### 🎯 Fonctionnalités principales

#### 1. **Slide Editor** - Génération de présentations
- ✅ **Présentations classiques** : Pitch, réunions clients
- ✅ **Formations** : Modules pédagogiques interactifs (le LLM détermine le nombre de slides)
- ✅ **Propositions commerciales** : Réponses aux appels d'offre (le LLM détermine le nombre de slides)
- ✅ **REX** : Retours d'expérience structurés
- 🎨 **12 types de slides** : cover, section, content, stat, quote, highlight, diagram, image, table, two_column, cv, closing
- 📊 **Streaming progressif** : Les slides apparaissent en temps réel pendant la génération
- 🔄 **Feedback naturel** : Corrections conversationnelles en langage naturel

#### 2. **Document Editor** - Génération de contenus
- ✅ **Articles de blog** : Articles professionnels complets
- ✅ **Posts LinkedIn** : Publications optimisées pour l'engagement
- ✅ **REX (Retours d'expérience)** : Documentation structurée
- ✅ **Compte rendu** : Synthèses de réunions
- 📝 **Streaming progressif** : Le contenu s'affiche en temps réel
- 🎨 **Illustrations** : Génération d'images via DALL-E (optionnel)

#### 3. **Intégrations**
- 🤖 **LLM** : Claude Sonnet 4.5 (Anthropic) ou Gemini 2.5 Flash (Google)
- 📚 **Références** : Intégration NotebookLM et CVs WEnvision
- 🎨 **Design** : Palette WEnvision (White/Rose Poudré, Noir/Gris, Corail/Terracotta)
- 🖼️ **Images** : Support DALL-E 3 pour illustrations (optionnel)

## 🏗️ Architecture

```
consulting-tools/
├── app.py                      # 🌐 Application FastAPI principale (5000+ lignes)
├── templates/                  # 📄 Interface web (Jinja2 + Tailwind CSS)
│   ├── index.html             # Page d'accueil
│   ├── slide-editor.html      # Éditeur de slides
│   ├── document-editor.html   # Éditeur de documents
│   └── monitoring.html        # Dashboard de veille
├── agents/                     # 🤖 Agents IA spécialisés
│   ├── formation_generator.py # Génération de formations
│   ├── article_generator.py   # Génération d'articles
│   └── meeting_summarizer.py  # Résumés de réunions
├── utils/                      # 🛠️ Utilitaires
│   ├── llm_client.py          # Client LLM (Claude + Gemini)
│   ├── image_generator.py     # Génération d'images (DALL-E)
│   └── monitoring.py          # Veille technologique
├── data/                       # 📊 Données
│   ├── notebooklm/            # Références WEnvision
│   │   └── references.json    # Projets, expertise, méthodologies
│   └── images/                # Images et illustrations
├── output/                     # 📤 Sorties générées
│   └── images/                # Images générées
├── docs/                       # 📚 Documentation
│   ├── DALLE_INTEGRATION.md   # Guide intégration DALL-E
│   ├── FEATURES_IMAGES.md     # Documentation génération d'images
│   └── SETUP_IMAGEN.md        # (Déprécié - Imagen non supporté)
├── requirements.txt            # 📦 Dépendances Python
└── .env.example               # ⚙️ Configuration
```

## 🚀 Installation

### 1. Prérequis

- **Python 3.12+** (Testé avec Python 3.13/3.14)
- **pip**
- **Clé API Anthropic** (Claude) ou **Clé API Google** (Gemini)
- **Clé API OpenAI** (optionnel, pour DALL-E)

### 2. Installation

```bash
# Cloner le projet
cd consulting-tools

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer avec vos clés API
nano .env
```

**Variables obligatoires** :
```bash
# LLM Principal (Anthropic - recommandé)
ANTHROPIC_API_KEY=sk-ant-xxx...

# OU Gemini (Google)
GEMINI_API_KEY=AIza...
USE_GEMINI=true
GEMINI_MODEL=models/gemini-2.5-flash

# Consultant
CONSULTANT_NAME=Jean-Sébastien Abessouguie Bayiha
COMPANY_NAME=WEnvision
```

**Variables optionnelles** :
```bash
# Génération d'images DALL-E (optionnel)
OPENAI_API_KEY=sk-...

# Google Workspace (optionnel)
GOOGLE_APPLICATION_CREDENTIALS=./config/google_credentials.json
GOOGLE_NOTEBOOKLM_ID=fb7f6ad8-...
```

### 4. Lancer l'application

```bash
# Démarrer le serveur
python app.py

# Ou avec uvicorn
uvicorn app:app --reload --port 8000
```

Accédez à : **http://localhost:8000**

## 📖 Utilisation

### Slide Editor

1. **Choisir le type** : Présentation, Formation, Proposition, REX
2. **Renseigner le brief** : Sujet, audience, contexte
3. **Options** :
   - Modèle LLM (Claude/Gemini)
   - Document source (texte libre)
   - Nombre de slides (pour présentations uniquement, formations/propositions déterminent eux-mêmes)
4. **Générer** : Les slides apparaissent en temps réel (streaming)
5. **Corriger** : Feedback en langage naturel ("Rend la slide 3 plus technique")

### Document Editor

1. **Choisir le type** : Article, LinkedIn, REX, Compte Rendu
2. **Renseigner le sujet** : Titre, contexte, audience
3. **Générer** : Le contenu s'affiche progressivement (streaming)
4. **Illustration** : Image générée automatiquement si DALL-E configuré
5. **Corriger** : Feedback pour améliorer le contenu

### Exemples de prompts

**Formation** :
```
Formation complète sur l'IA générative pour des managers.
Audience : Directeurs et chefs de projet
Durée : 2 jours
```

**Proposition commerciale** :
```
Répondre à l'appel d'offre pour la transformation data d'une banque.
Périmètre : Migration cloud + Data Lake + Gouvernance
Budget : 500K€
```

## 🎨 Génération d'images

### État actuel

⚠️ **Imagen (Google) non supporté** : Le SDK `google-generativeai` est déprécié et Imagen n'est pas accessible via l'API publique.

✅ **Solution recommandée : DALL-E 3 (OpenAI)**

### Activer DALL-E

**1. Installation** :
```bash
pip install openai
```

**2. Configuration** :
```bash
# Dans .env
OPENAI_API_KEY=sk-your-openai-key
```

**3. Intégration** :
Suivez le guide complet : **[docs/DALLE_INTEGRATION.md](docs/DALLE_INTEGRATION.md)**

**Coûts** :
- Article : 1 image = **$0.08** (1792x1024)
- Présentation 10 slides : ~4 images = **$0.32**
- Formation 20 slides : ~7 images = **$0.56**

### Alternative économique

**Replicate + Stable Diffusion** : ~$0.0025/image (30x moins cher)
- Guide inclus dans [DALLE_INTEGRATION.md](docs/DALLE_INTEGRATION.md)

## ⚙️ Configuration avancée

### Changer de LLM

**Claude (Anthropic)** - Recommandé :
```bash
ANTHROPIC_API_KEY=sk-ant-...
USE_GEMINI=false
```

**Gemini (Google)** - Alternative gratuite/économique :
```bash
GEMINI_API_KEY=AIza...
USE_GEMINI=true
GEMINI_MODEL=models/gemini-2.5-flash
```

### Ajouter des références

**1. Créer `data/notebooklm/references.json`** :
```json
{
  "projects": [
    {
      "title": "Transformation Data Banque X",
      "client": "Banque X",
      "description": "Migration cloud + Data Lake",
      "technologies": ["Azure", "Databricks", "Power BI"],
      "results": "30% réduction coûts, 10x performance"
    }
  ],
  "expertise": [
    "Stratégie Data & IA",
    "Machine Learning",
    "Cloud (Azure, AWS, GCP)"
  ],
  "methodologies": [
    "Design Sprint",
    "Agile/Scrum",
    "POC/MVP"
  ]
}
```

**2. Ajouter CVs** :
- Placer `Biographies - CV All WEnvision.pptx` à la racine
- Utilisé automatiquement dans les propositions commerciales

## 📊 Fonctionnalités avancées

### Streaming progressif

- ✅ **Slide Editor** : Slides affichées une par une pendant la génération
- ✅ **Document Editor** : Texte affiché mot par mot en temps réel
- ⚡ **SSE (Server-Sent Events)** : Pas de polling, événements temps réel

### Feedback naturel

**Exemples** :
- "Rend la slide 3 plus technique avec des métriques"
- "Simplifie le vocabulaire pour un public non-tech"
- "Ajoute un exemple concret sur la slide 5"
- "Réduis le contenu de la slide 2, c'est trop dense"

### Types de slides

| Type | Usage | Illustré |
|------|-------|----------|
| **cover** | Page de couverture | ❌ |
| **section** | Séparateur de section | ❌ |
| **content** | Contenu principal | ✅ |
| **highlight** | Points clés | ✅ |
| **stat** | Statistiques/KPIs | ✅ |
| **diagram** | Diagrammes/flux | ✅ |
| **image** | Slide visuelle | ✅ |
| **table** | Tableaux de données | ❌ |
| **two_column** | Deux colonnes | ✅ |
| **quote** | Citations | ❌ |
| **cv** | CV consultant | ❌ |
| **closing** | Conclusion/contact | ❌ |

## 🔧 Développement

### Structure du code

**FastAPI Routes** :
- `GET /` : Page d'accueil
- `GET /slide-editor` : Éditeur de slides
- `GET /document-editor` : Éditeur de documents
- `POST /api/slide-editor/start-generate` : Démarrer génération slides
- `GET /api/slide-editor/stream/{job_id}` : SSE stream progression
- `POST /api/document-editor/generate` : Générer document

**Architecture SSE** :
```python
# 1. POST crée un job en background
jobs[job_id] = {"status": "running", "slides": []}
threading.Thread(target=run_generation).start()

# 2. GET stream envoie les événements
async def stream():
    while job["status"] == "running":
        yield send_sse("slide", {"slide": slide})
```

### Tests

```bash
# Test LLM
python -c "from utils.llm_client import LLMClient; print(LLMClient().generate('Hello'))"

# Test app
python app.py
# → Ouvrir http://localhost:8000
```

## 📈 Roadmap

### ✅ Complété

- [x] Application web FastAPI + Tailwind CSS
- [x] Slide Editor avec 12 types de slides
- [x] Document Editor (Article, LinkedIn, REX, CR)
- [x] Streaming progressif (SSE)
- [x] Feedback conversationnel
- [x] Support Claude Sonnet 4.5 + Gemini 2.5 Flash
- [x] Intégration références NotebookLM + CVs
- [x] Slides déterminées automatiquement (formations/propositions)

### 🚧 En cours

- [ ] Génération d'images DALL-E 3 (documentation complète)
- [ ] Export PowerPoint (.pptx)
- [ ] Export PDF
- [ ] Dashboard de veille technologique

### 🔮 À venir

- [ ] Publication LinkedIn automatique
- [ ] Intégration CRM (HubSpot, Salesforce)
- [ ] Support multilingue (EN, FR, ES)
- [ ] Édition collaborative en temps réel
- [ ] Templates de slides personnalisables
- [ ] Bibliothèque d'images réutilisables

## ⚠️ Notes importantes

### Python 3.14 - Bug f-strings

Ce projet a été testé avec **Python 3.13/3.14** qui a un parsing strict des f-strings :
- ❌ **Apostrophes françaises** dans f-strings cassent le code : `d'experience`, `l'action`
- ✅ **Solution** : Remplacer par espaces ou rephraser : `d experience`, `l action`
- ❌ **`3x`** dans f-strings cause une erreur → Utiliser `x3`

### google-generativeai déprécié

Le package `google-generativeai` est **déprécié** et ne reçoit plus de mises à jour.
- Imagen **non accessible** via ce SDK
- Solution : **DALL-E 3** (OpenAI) ou **Replicate** (Stable Diffusion)

## 🤝 Contribution

Développé pour **WEnvision** - Stratégie Data & IA

## 📄 Licence

Propriétaire - WEnvision © 2026

## 🆘 Support

- 📚 **Documentation** : [docs/](docs/)
  - [DALLE_INTEGRATION.md](docs/DALLE_INTEGRATION.md) - Guide DALL-E
  - [FEATURES_IMAGES.md](docs/FEATURES_IMAGES.md) - Génération d'images
- 💬 **Issues** : Créer une issue sur le repo
- 📧 **Email** : [Support WEnvision]

## 🙏 Technologies

- [Anthropic Claude](https://www.anthropic.com) - LLM principal
- [Google Gemini](https://ai.google.dev) - Alternative LLM
- [OpenAI DALL-E](https://openai.com) - Génération d'images (optionnel)
- [FastAPI](https://fastapi.tiangolo.com) - Framework web
- [Tailwind CSS](https://tailwindcss.com) - Design system

---

**Développé avec ❤️ par WEnvision**
