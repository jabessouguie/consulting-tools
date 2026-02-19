# 🚀 Guide de Démarrage Rapide

Ce guide vous permet de démarrer avec les agents Wenvision en moins de 15 minutes.

## ✅ Checklist de démarrage

- [ ] Python 3.9+ installé
- [ ] Clé API Anthropic (Claude)
- [ ] Compte Google

## 🏃 Installation Express

```bash
# 1. Aller dans le dossier
cd wenvision-agents

# 2. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables
cp .env.example .env
nano .env  # Éditer avec votre clé API
```

## 🔑 Configuration minimale

Dans `.env`, ajoutez au minimum:

```bash
ANTHROPIC_API_KEY=sk-ant-votre-cle-ici
```

C'est tout pour démarrer ! Les autres configurations sont optionnelles.

## 🎯 Premier test: Agent de Veille LinkedIn

Le plus simple pour commencer:

```bash
python agents/linkedin_monitor.py --no-posts
```

Ce que fait cette commande:
- ✅ Collecte des articles depuis des flux RSS publics
- ✅ Fait une recherche web sur les mots-clés IA/Data
- ✅ Analyse les tendances
- ❌ Ne génère pas de posts (mode veille uniquement)

**Résultat:** Un fichier JSON dans `data/monitoring/` avec les articles collectés.

## 🎯 Deuxième test: Génération de Post LinkedIn

```bash
python agents/linkedin_monitor.py --num-posts 1
```

Ce que fait cette commande:
- ✅ Collecte des articles (comme avant)
- ✅ Analyse les tendances
- ✅ Génère 1 post LinkedIn avec variantes

**Résultat:**
- `output/linkedin_cycle_*.json`: Données complètes
- `output/linkedin_post_*.md`: Post prêt à publier

## 🎯 Troisième test: Génération de Proposition

Pour tester l'agent de propositions, nous avons inclus un exemple:

```bash
python agents/proposal_generator.py data/examples/appel_offre_example.txt
```

**Important:** Cette commande nécessite l'accès aux Google API. Si vous n'avez pas encore configuré Google, vous verrez un message d'avertissement mais l'agent fonctionnera quand même en mode dégradé (sans le template Slides).

**Résultat:**
- `output/proposal_*.json`: Proposition complète
- `output/proposal_*.md`: Version markdown lisible

## 🔧 Configuration avancée (optionnelle)

### Pour l'agent de propositions

Si vous voulez utiliser vos propres documents Google:

1. Suivre le guide complet: [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)
2. Configurer dans `.env`:
   ```bash
   GOOGLE_SLIDES_ID=votre-id-presentation
   ```

### Pour la veille personnalisée

Personnalisez les sources dans `.env`:

```bash
# Flux RSS personnalisés
RSS_FEEDS=https://blog1.com/rss,https://blog2.com/rss

# Mots-clés de veille
VEILLE_KEYWORDS=GenAI,LLM,MLOps,Azure AI
```

## 📊 Vérifier que tout fonctionne

```bash
# Test API Claude
python -c "from utils.llm_client import LLMClient; print(LLMClient().generate('Dis bonjour!'))"

# Test veille web
python -c "from utils.monitoring import MonitoringTool; m = MonitoringTool(); print(f'{len(m.web_search([\"AI\"]))} résultats trouvés')"
```

Si ces commandes fonctionnent, vous êtes prêt ! 🎉

## 🎨 Exemples de commandes utiles

### Veille uniquement (pas de post)
```bash
python agents/linkedin_monitor.py --no-posts
```

### Un seul post type "insight"
```bash
python agents/linkedin_monitor.py --post-type insight --num-posts 1
```

### 5 posts variés
```bash
python agents/linkedin_monitor.py --num-posts 5
```

### Proposition avec chemin personnalisé
```bash
python agents/proposal_generator.py mon_appel_offre.txt -o propositions/client_xyz.json
```

## 🆘 Problèmes courants

### "No module named 'anthropic'"
```bash
# Vérifier que vous êtes dans l'environnement virtuel
source venv/bin/activate
pip install -r requirements.txt
```

### "API key not found"
```bash
# Vérifier que .env existe et contient ANTHROPIC_API_KEY
cat .env | grep ANTHROPIC
```

### "Google credentials not found"
C'est normal si vous n'avez pas encore configuré Google API. L'agent fonctionnera en mode dégradé.

Pour configurer: suivre [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)

## 📚 Prochaines étapes

1. ✅ Vous avez testé les agents de base
2. 📖 Lire le [README.md](README.md) complet pour plus de détails
3. 🔧 Configurer les Google API si besoin: [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)
4. 🤖 Explorer l'intégration Antigravity dans [README.md](README.md)

## 🎓 Tutoriels pas-à-pas

### Créer un post LinkedIn en 2 minutes

```bash
# 1. Lancer la veille
python agents/linkedin_monitor.py --post-type insight

# 2. Ouvrir le post généré
cat output/linkedin_post_*.md

# 3. Copier le post principal et le publier sur LinkedIn!
```

### Créer une proposition en 5 minutes

```bash
# 1. Créer un fichier avec l'appel d'offre
nano mon_appel_offre.txt
# [Coller le contenu de l'appel d'offre]

# 2. Générer la proposition
python agents/proposal_generator.py mon_appel_offre.txt

# 3. Ouvrir la proposition
cat output/proposal_*.md

# 4. Affiner et envoyer!
```

## 💡 Conseils

- **Démarrer simple**: Testez d'abord la veille sans génération de posts
- **Itérer**: Les posts générés sont une base, personnalisez-les
- **Configurer progressivement**: Commencez sans Google API, ajoutez-le plus tard
- **Automatiser**: Une fois rodé, utilisez Antigravity pour automatiser

## 🎉 Vous êtes prêt!

Vous pouvez maintenant:
- ✅ Faire de la veille automatisée
- ✅ Générer des posts LinkedIn
- ✅ Créer des propositions commerciales

Bon travail! 🚀

---

**Besoin d'aide?** Consultez le [README.md](README.md) complet ou [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md)
