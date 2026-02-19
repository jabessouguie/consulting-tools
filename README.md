# 🚀 Agents Wenvision

Agents d'Intelligence Artificielle pour automatiser les tâches de conseil en stratégie data et IA chez Wenvision.

## 📋 Vue d'ensemble

Ce projet contient deux agents intelligents:

### 1. 📄 Agent de Propositions Commerciales
Génère automatiquement des propositions commerciales personnalisées à partir d'appels d'offre en utilisant:
- Les références et projets Wenvision (NotebookLM + fichiers PPTX)
- Un template PowerPoint professionnel (WENVISION_Template_Palette 2026)
- CVs adaptés depuis Biographies - CV All WEnvision.pptx
- Diagrammes automatiques (flow, cycle, pyramid, timeline, matrix)
- **Diagrammes d'architecture via Claude + Mermaid** (gratuit, précis)
- Images générées par IA (DALL-E 3, optionnel)
- Bibliothèque d'images réutilisables
- L'expertise et le style de Jean-Sébastien Abessouguie

**Formats de sortie:**
- 📊 PowerPoint (.pptx) - Présentation complète avec slides professionnelles
- 📝 Markdown (.md) - Version texte lisible
- 📋 JSON (.json) - Données structurées

### 2. 🔍 Agent de Veille LinkedIn
Effectue une veille technologique multi-sources et génère des posts LinkedIn engageants sur:
- Flux RSS (blogs tech, IA, data)
- Recherche web sur mots-clés
- LinkedIn et réseaux sociaux
- Newsletters

## 🏗️ Architecture

```
wenvision-agents/
├── agents/                     # Agents intelligents
│   ├── proposal_generator.py  # Génération propositions
│   └── linkedin_monitor.py    # Veille et posts LinkedIn
├── utils/                      # Utilitaires
│   ├── google_api.py          # Client Google API
│   ├── llm_client.py          # Client LLM (Claude Opus 4.6)
│   ├── monitoring.py          # Outils de veille
│   ├── pptx_generator.py      # Génération PowerPoint
│   ├── pptx_reader.py         # Lecture de fichiers PPTX
│   └── image_generator.py     # Génération d'images (DALL-E) et bibliothèque
├── config/                     # Configuration
│   ├── google_credentials.json # Credentials Google (à créer)
│   └── token.pickle           # Token OAuth (auto-généré)
├── data/                       # Données
│   ├── notebooklm/            # Références exportées
│   ├── references/            # Fichiers PPTX de références
│   ├── monitoring/            # Résultats de veille
│   ├── images/                # Images et diagrammes
│   │   ├── generated/         # Images générées par DALL-E
│   │   └── library/           # Bibliothèque d'images réutilisables
│   └── examples/              # Exemples d'appels d'offre
├── output/                     # Sorties générées
├── requirements.txt            # Dépendances Python
├── .env.example               # Variables d'environnement
└── README.md                  # Ce fichier
```

## 🚀 Installation

### 1. Prérequis

- Python 3.9+
- pip
- Compte Google (pour l'accès aux API)
- Clé API Anthropic (Claude)

### 2. Cloner et installer

```bash
# Aller dans le dossier
cd wenvision-agents

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos informations
nano .env
```

Variables importantes dans `.env`:
```bash
# LLM (Obligatoire)
ANTHROPIC_API_KEY=sk-ant-xxx...  # API Claude Opus 4.6

# Google API (pour certaines fonctionnalités)
GOOGLE_SLIDES_ID=1uN1pSE6j...    # ID de votre template

# Génération d'images (Optionnel)
OPENAI_API_KEY=sk-...            # Pour DALL-E 3
USE_DALLE_IMAGES=true            # Activer la génération d'images

# Veille LinkedIn
RSS_FEEDS=https://feed1.com,https://feed2.com
VEILLE_KEYWORDS=IA,Data Science,GenAI

# Consultant (Personnalisation)
CONSULTANT_NAME=Jean-Sébastien Abessouguie Bayiha
CONSULTANT_TITLE=Consultant en stratégie data et IA
COMPANY_NAME=Wenvision
```

### 4. Configurer les API Google

Suivez le guide détaillé: [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)

Résumé rapide:
1. Créer un projet Google Cloud
2. Activer les API (Drive, Slides, Docs)
3. Créer des credentials OAuth 2.0
4. Télécharger `google_credentials.json` dans `config/`

### 5. Préparer les données NotebookLM

Comme NotebookLM n'a pas d'API publique:

```bash
# Créer le dossier
mkdir -p data/notebooklm

# Créer le fichier de références
nano data/notebooklm/references.json
```

Structure du fichier `references.json`:
```json
{
  "projects": [
    {
      "title": "Projet exemple",
      "client": "Client A",
      "description": "Description du projet",
      "technologies": ["Python", "Azure", "ML"],
      "results": "ROI de 30%, temps de traitement divisé par 3"
    }
  ],
  "expertise": [
    "Stratégie Data & IA",
    "Machine Learning",
    "Cloud (Azure, AWS)"
  ],
  "methodologies": [
    "Design Sprint",
    "Agile",
    "POC/MVP"
  ]
}
```

## 📖 Utilisation

### Agent 1: Génération de Propositions Commerciales

#### Utilisation basique

```bash
python agents/proposal_generator.py data/examples/appel_offre.txt
```

#### Avec chemin de sortie personnalisé

```bash
python agents/proposal_generator.py data/examples/appel_offre.txt \
  -o output/proposition_client_xyz.json
```

#### Résultat

L'agent génère:
- `proposition_client_xyz.pptx`: 📊 **PowerPoint professionnel** avec:
  - Slides structurées selon le template Wenvision
  - Diagrammes automatiques (flow, cycle, pyramid, timeline, matrix)
  - CVs adaptés au contexte de l'appel d'offre
  - Tableaux (planning, budget)
  - Palette de couleurs Wenvision (terracotta, anthracite, rose poudré)
- `proposition_client_xyz.json`: Contenu structuré complet
- `proposition_client_xyz.md`: Version markdown lisible

**Diagrammes automatiques inclus:**
- 🔄 Flow: processus séquentiels (méthodologie, phases)
- 🔁 Cycle: processus itératifs (facteurs de succès)
- 🔺 Pyramid: hiérarchies (priorités, niveaux)
- ⏱️ Timeline: chronologies (roadmap, jalons)
- ⊞ Matrix: catégorisations 2x2 (décisions, priorisation)

### Agent 2: Veille et Posts LinkedIn

#### Cycle complet (veille + génération de 3 posts)

```bash
python agents/linkedin_monitor.py
```

#### Veille uniquement (sans générer de posts)

```bash
python agents/linkedin_monitor.py --no-posts
```

#### Générer un seul post d'un type spécifique

```bash
# Post type "insight"
python agents/linkedin_monitor.py --post-type insight

# Post type "curation"
python agents/linkedin_monitor.py --post-type curation

# Post type "opinion"
python agents/linkedin_monitor.py --post-type opinion
```

#### Générer 5 posts

```bash
python agents/linkedin_monitor.py --num-posts 5
```

#### Résultat

L'agent génère:
- `linkedin_cycle_YYYYMMDD_HHMMSS.json`: Données complètes
- `linkedin_post_YYYYMMDD_HHMMSS_1.md`: Post principal
- `linkedin_post_YYYYMMDD_HHMMSS_2.md`: Variante 2
- etc.

Chaque fichier markdown contient:
- Le post principal
- Des variantes (court, storytelling)
- Les sources utilisées

## 🎨 Illustrations et Diagrammes

Les propositions incluent automatiquement des diagrammes visuels pour améliorer la compréhension:

### Types de diagrammes disponibles

1. **Flow (flux séquentiel)** → Processus linéaires, méthodologies
2. **Cycle (cyclique)** → Processus itératifs, amélioration continue
3. **Pyramid (pyramidal)** → Hiérarchies, priorités, niveaux
4. **Timeline (chronologie)** → Roadmaps, jalons, planning
5. **Matrix (matrice)** → Catégorisation 2x2/2x3, quadrants de décision

### Génération automatique

Le système analyse le contenu et ajoute **1-3 diagrammes par proposition** là où c'est pertinent:
- Méthodologie → Diagramme flow
- Facteurs de succès → Diagramme cycle
- Priorisation → Diagramme pyramid ou matrix
- Roadmap → Timeline

### Génération de diagrammes d'architecture (Claude + Mermaid)

**NOUVEAU** : Génération automatique de diagrammes d'architecture et d'infrastructure via **Claude + Mermaid** (gratuit, sans clé API supplémentaire) !

#### Installation de Mermaid CLI

```bash
# Installer mermaid-cli (nécessite Node.js)
npm install -g @mermaid-js/mermaid-cli

# Vérifier l'installation
mmdc --version
```

#### Activation

```bash
# Dans .env
USE_DALLE_IMAGES=true  # Active les diagrammes Claude/Mermaid
```

Le système génère automatiquement des diagrammes pour:
- **Architectures techniques** → Diagrammes de composants avec flux
- **Infrastructures** → Schémas cloud/on-premise
- **Flux de données** → Flowcharts ETL/pipelines

**Exemple généré** :
```
API Gateway → Microservices → Base de données → Analytics
```

### Génération d'images par IA (DALL-E - optionnel)

DALL-E 3 est maintenant **optionnel** et utilisé uniquement en fallback si Mermaid échoue.

```bash
# Dans .env (optionnel)
OPENAI_API_KEY=sk-...
USE_DALLE_IMAGES=true
```

### Bibliothèque d'images

Gérez une bibliothèque d'images réutilisables:

```python
from utils.image_generator import ImageLibrary

library = ImageLibrary()

# Ajouter une image
library.add_image(
    image_path="path/to/image.png",
    category="architecture",
    tags=["cloud", "microservices"],
    description="Architecture microservices"
)

# Rechercher
images = library.search_images(category="architecture")
stats = library.get_statistics()
```

**Catégories disponibles:** architecture, process, dashboard, team, technology, data, success, methodology, infrastructure, mockup

📚 **Documentation complète:** [ILLUSTRATIONS_GUIDE.md](docs/ILLUSTRATIONS_GUIDE.md)

## 🔧 Configuration avancée

### Personnaliser les sources de veille

Dans `.env`:
```bash
# Flux RSS personnalisés
RSS_FEEDS=https://blog.google/technology/ai/rss/,https://openai.com/blog/rss.xml,https://www.anthropic.com/news/rss.xml

# Mots-clés de veille
VEILLE_KEYWORDS=GenAI,LLM,RAG,Azure OpenAI,MLOps,Data Mesh

# Fréquence de veille (heures)
VEILLE_FREQUENCY_HOURS=24
```

### Personnaliser le consultant

Dans `.env`:
```bash
CONSULTANT_NAME=Votre Nom
CONSULTANT_TITLE=Votre titre
COMPANY_NAME=Votre entreprise
CONSULTANT_PROFILE=https://linkedin.com/in/votre-profil
```

## 🤖 Intégration avec Antigravity

Ces agents peuvent être utilisés avec [Google Antigravity](https://antigravity.im) ou [Open-Antigravity](https://github.com/ishandutta2007/open-antigravity).

### Configuration pour Antigravity

Créez un fichier `antigravity.config.json`:

```json
{
  "agents": [
    {
      "name": "proposal-generator",
      "command": "python agents/proposal_generator.py",
      "description": "Génère des propositions commerciales",
      "triggers": ["new_tender", "rfp_received"]
    },
    {
      "name": "linkedin-monitor",
      "command": "python agents/linkedin_monitor.py",
      "description": "Veille et génération de posts LinkedIn",
      "schedule": "0 9 * * *",
      "triggers": ["daily_monitoring"]
    }
  ]
}
```

### Utilisation dans Antigravity

```python
# Dans votre workflow Antigravity
from antigravity import Agent

# Charger l'agent de proposition
proposal_agent = Agent.load("proposal-generator")

# Exécuter
result = proposal_agent.run(
    tender_file="path/to/tender.txt"
)
```

## 📊 Exemples de résultats

### Proposition commerciale générée

```markdown
# Proposition Commerciale - Transformation Data & IA

**Client:** Entreprise XYZ
**Consultant:** Jean-Sébastien Abessouguie Bayiha
**Date:** 12/02/2026

## 1. Résumé Exécutif

Nous avons identifié 3 enjeux majeurs dans votre appel d'offre...

[Contenu détaillé généré automatiquement]
```

### Post LinkedIn généré

```markdown
🎯 L'IA générative redéfinit la stratégie data en 2026

Après avoir analysé 50+ cas clients, une tendance claire émerge:
les entreprises qui réussissent leur transformation IA ne commencent
pas par la tech, mais par les cas d'usage métier.

3 apprentissages clés:
1. [...]
2. [...]
3. [...]

Et vous, par quoi avez-vous commencé votre transformation IA? 🤔

#IA #DataStrategy #GenAI #Transformation
```

## 🛠️ Développement

### Structure du code

```python
# Exemple d'utilisation des modules

from utils.llm_client import LLMClient
from utils.google_api import GoogleAPIClient

# Client LLM
llm = LLMClient()
response = llm.generate("Votre prompt")

# Client Google
google = GoogleAPIClient()
slides = google.get_slides_content("presentation_id")
```

### Tests

```bash
# Tester la connexion LLM
python -c "from utils.llm_client import LLMClient; print(LLMClient().generate('Hello'))"

# Tester Google API
python -c "from utils.google_api import GoogleAPIClient; GoogleAPIClient()"

# Tester la veille
python -c "from utils.monitoring import MonitoringTool; print(len(MonitoringTool().web_search(['IA'])))"
```

## 📈 Roadmap

### ✅ Complété
- [x] Export des propositions en PowerPoint (PPTX)
- [x] Diagrammes automatiques (flow, cycle, pyramid, timeline, matrix)
- [x] **Génération de diagrammes d'architecture via Claude + Mermaid** (nouveau !)
- [x] Intégration DALL-E pour génération d'images (optionnel)
- [x] Bibliothèque d'images réutilisables
- [x] Adaptation des CVs au contexte de l'appel d'offre
- [x] Modèle Claude Opus 4.6

### 🔄 En cours / À venir
- [ ] Support de l'API NotebookLM quand elle sera disponible
- [ ] Intégration LinkedIn officielle pour publication automatique
- [ ] Dashboard web pour visualiser les résultats
- [ ] Agent de suivi des opportunités commerciales
- [ ] Agent de compte rendu de réunion (transcript → CR + email)
- [ ] Support multilingue (EN, FR)
- [ ] Intégration avec CRM (HubSpot, Salesforce)
- [ ] Édition interactive des diagrammes dans l'interface web

## 🤝 Contribution

Ce projet est développé pour Wenvision. Pour toute suggestion:

1. Créer une issue avec la description
2. Fork le projet
3. Créer une branche (`git checkout -b feature/AmazingFeature`)
4. Commit les changements (`git commit -m 'Add AmazingFeature'`)
5. Push vers la branche (`git push origin feature/AmazingFeature`)
6. Ouvrir une Pull Request

## 📄 Licence

Propriétaire - Wenvision © 2026

## 🆘 Support

Pour toute question:
- 📧 Email: [Votre email support]
- 💬 Slack: #wenvision-agents
- 📚 Documentation: [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)

## 🙏 Remerciements

- [Anthropic Claude](https://www.anthropic.com) pour l'API LLM
- [Google Cloud](https://cloud.google.com) pour les API
- [Open-Antigravity](https://github.com/ishandutta2007/open-antigravity) pour l'inspiration

---

Développé avec ❤️ par Wenvision
