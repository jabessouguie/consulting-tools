# 🎯 Getting Started - Agents Wenvision

Bienvenue ! Ce document vous guide pour démarrer avec vos agents IA Wenvision.

## 📦 Ce qui a été créé pour vous

### 🤖 Deux Agents Intelligents

#### 1. Agent de Propositions Commerciales (`agents/proposal_generator.py`)
- **Fonction**: Génère automatiquement des propositions commerciales à partir d'appels d'offre
- **Entrée**: Fichier texte contenant l'appel d'offre
- **Sortie**: Proposition complète en JSON + Markdown
- **Technologies**: Claude (Anthropic), Google Slides API, Google Docs API
- **Temps d'exécution**: ~5-10 minutes

#### 2. Agent de Veille LinkedIn (`agents/linkedin_monitor.py`)
- **Fonction**: Veille technologique multi-sources + génération de posts LinkedIn
- **Sources**: RSS, recherche web, (LinkedIn à venir)
- **Sortie**: Articles analysés + Posts LinkedIn prêts à publier
- **Technologies**: Claude (Anthropic), BeautifulSoup, feedparser
- **Temps d'exécution**: ~10-15 minutes

### 📁 Structure du Projet

```
wenvision-agents/
├── 📖 Documentation
│   ├── README.md              # Documentation complète
│   ├── QUICKSTART.md          # Démarrage rapide (15 min)
│   ├── GOOGLE_API_SETUP.md    # Configuration Google API
│   └── GETTING_STARTED.md     # Ce fichier
│
├── 🤖 Agents
│   ├── agents/
│   │   ├── proposal_generator.py   # Agent propositions
│   │   └── linkedin_monitor.py     # Agent veille
│   │
│   └── utils/
│       ├── google_api.py      # Client Google API
│       ├── llm_client.py      # Client Claude/LLM
│       └── monitoring.py      # Outils de veille
│
├── ⚙️  Configuration
│   ├── .env.example           # Template variables d'environnement
│   ├── requirements.txt       # Dépendances Python
│   ├── antigravity.config.json # Config pour Antigravity
│   └── config/                # Credentials Google (à créer)
│
├── 📊 Données
│   ├── data/
│   │   ├── examples/          # Exemples d'appels d'offre
│   │   ├── notebooklm/        # Références Wenvision
│   │   └── monitoring/        # Résultats de veille
│   │
│   └── output/                # Propositions et posts générés
│
└── 🚀 Scripts
    └── run_demo.sh            # Script de démonstration
```

## 🚀 Installation en 3 étapes

### Étape 1: Environnement Python

```bash
cd wenvision-agents

# Créer environnement virtuel
python -m venv venv

# Activer
source venv/bin/activate  # macOS/Linux
# OU
venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt
```

### Étape 2: Configuration minimale

```bash
# Copier le template
cp .env.example .env

# Éditer et ajouter votre clé API Anthropic
nano .env  # ou votre éditeur préféré
```

Dans `.env`, configurez au minimum:
```bash
ANTHROPIC_API_KEY=sk-ant-votre-clé-ici
```

### Étape 3: Premier test

```bash
# Test simple de veille
python agents/linkedin_monitor.py --no-posts
```

Si ça fonctionne, vous êtes prêt ! 🎉

## 📚 Documentation

### Pour démarrer rapidement
👉 **[QUICKSTART.md](QUICKSTART.md)** - Démarrage en 15 minutes avec exemples

### Pour une installation complète
👉 **[README.md](README.md)** - Documentation complète avec tous les détails

### Pour configurer Google API (optionnel)
👉 **[GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)** - Guide pas-à-pas Google Cloud

## 🎯 Cas d'usage

### 1. Veille quotidienne automatisée

Collectez automatiquement les dernières actualités IA/Data:

```bash
# Veille seule (pas de post)
python agents/linkedin_monitor.py --no-posts

# Résultats dans: data/monitoring/veille_*.json
```

### 2. Génération de posts LinkedIn

Créez des posts engageants basés sur la veille:

```bash
# 1 post type "insight"
python agents/linkedin_monitor.py --post-type insight

# 3 posts variés
python agents/linkedin_monitor.py --num-posts 3

# Résultats dans: output/linkedin_post_*.md
```

### 3. Réponse à appel d'offre

Générez une proposition commerciale en minutes:

```bash
# Avec l'exemple fourni
python agents/proposal_generator.py data/examples/appel_offre_example.txt

# Avec votre fichier
python agents/proposal_generator.py votre_appel_offre.txt

# Résultats dans: output/proposal_*.md
```

### 4. Script de démo interactif

```bash
# Lancer le menu interactif
./run_demo.sh
```

## 🔧 Personnalisation

### Personnaliser votre profil

Dans `.env`:
```bash
CONSULTANT_NAME=Votre Nom
CONSULTANT_TITLE=Votre titre
COMPANY_NAME=Votre entreprise
CONSULTANT_PROFILE=https://linkedin.com/in/votre-profil
```

### Personnaliser les sources de veille

```bash
# Flux RSS
RSS_FEEDS=https://feed1.com/rss,https://feed2.com/rss

# Mots-clés
VEILLE_KEYWORDS=GenAI,LLM,RAG,Azure,MLOps
```

### Personnaliser les références

Éditez `data/notebooklm/references.json` avec:
- Vos projets et références
- Votre expertise
- Vos méthodologies

## 🤖 Intégration Antigravity

Ces agents sont prêts pour [Google Antigravity](https://antigravity.im):

1. Ouvrir Antigravity IDE
2. Importer le projet `wenvision-agents`
3. Les agents seront détectés via `antigravity.config.json`
4. Configurer les triggers et workflows

Configuration incluse:
- ✅ Agents déclarés
- ✅ Inputs/outputs définis
- ✅ Workflows exemple
- ✅ Triggers automatiques

## ⚡ Commandes Rapides

```bash
# Veille seule
python agents/linkedin_monitor.py --no-posts

# 1 post LinkedIn
python agents/linkedin_monitor.py --num-posts 1

# Proposition commerciale
python agents/proposal_generator.py data/examples/appel_offre_example.txt

# Demo interactive
./run_demo.sh

# Tests de configuration
python -c "from utils.llm_client import LLMClient; print('✅ LLM OK')"
python -c "from utils.monitoring import MonitoringTool; print('✅ Monitoring OK')"
```

## 🆘 Besoin d'aide?

### Problèmes courants

**"No module named 'anthropic'"**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"API key not found"**
```bash
# Vérifier .env
cat .env | grep ANTHROPIC_API_KEY
```

**"Google credentials not found"**
Normal si pas encore configuré. Agent fonctionne en mode dégradé.
Voir [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md) pour configurer.

### Documentation

- 📖 [README.md](README.md) - Doc complète
- 🚀 [QUICKSTART.md](QUICKSTART.md) - Démarrage rapide
- 🔧 [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md) - Config Google
- 💬 Support: [Votre canal support]

## 🎓 Prochaines étapes recommandées

1. ✅ Tester les agents avec les exemples
2. 📝 Personnaliser votre profil dans `.env`
3. 📚 Ajouter vos références dans `data/notebooklm/references.json`
4. 🔧 Configurer Google API (optionnel): [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)
5. 🤖 Explorer l'intégration Antigravity
6. 🔄 Automatiser avec des cron jobs ou workflows

## 💡 Conseils

- **Commencez simple**: Test de veille sans posts d'abord
- **Itérez**: Les sorties sont des bases à personnaliser
- **Automatisez**: Une fois rodé, planifiez avec cron ou Antigravity
- **Personnalisez**: Adaptez les prompts à votre style dans le code

## 🎉 Vous êtes prêt!

Tout est configuré pour:
- ✅ Faire de la veille technologique automatisée
- ✅ Générer des posts LinkedIn engageants
- ✅ Créer des propositions commerciales personnalisées
- ✅ Intégrer avec Antigravity pour automatisation

**Bon travail!** 🚀

---

*Développé pour Wenvision | Consultant: Jean-Sébastien Abessouguie Bayiha*
