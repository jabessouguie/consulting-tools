# Consulting Tools Consulting Tools

Suite d'outils intelligents pour créer automatiquement des présentations et contenus professionnels.

## À quoi ça sert ?

Ces outils vous permettent de créer rapidement et automatiquement :

**Des présentations PowerPoint** :
- Présentations commerciales classiques
- Modules de formation professionnelle
- Propositions commerciales en réponse à des appels d'offre
- Retours d'expérience (REX)

**Des documents texte** :
- Articles de blog professionnels
- Publications LinkedIn
- Comptes rendus de réunion
- Retours d'expérience structurés

## Comment ça marche ?

1. **Vous décrivez ce que vous voulez** : Tapez le sujet, le contexte, l'audience visée
2. **L'outil génère automatiquement** : Création de slides ou de texte complet en quelques secondes
3. **Vous pouvez corriger** : Demandez des modifications en langage naturel ("rends la slide 3 plus technique")

### Exemple d'utilisation

**Pour une formation** :
```
Je veux : "Une formation de 2 jours sur l'intelligence artificielle"
Audience : "Managers et chefs de projet"
Résultat : Présentation complète générée automatiquement avec le bon nombre de slides
```

**Pour un article** :
```
Je veux : "Un article sur les bénéfices de l'IA en entreprise"
Audience : "Décideurs et directeurs"
Résultat : Article professionnel de 1500 mots avec structure complète
```

## Fonctionnalités principales

### Éditeur de présentations

**Types de présentations disponibles** :
- Présentations classiques
- Formations (l'outil détermine automatiquement le nombre de slides nécessaires)
- Propositions commerciales (l'outil adapte le nombre de slides au besoin)
- Retours d'expérience

**12 types de slides différents** :
- Page de couverture
- Séparateurs de sections
- Contenu principal
- Statistiques et chiffres
- Citations
- Points clés
- Diagrammes
- Images
- Tableaux
- Deux colonnes
- CV de consultants
- Page de conclusion

**Affichage en temps réel** :
Les slides apparaissent progressivement pendant leur création, vous voyez le résultat immédiatement.

**Corrections en langage naturel** :
Demandez des modifications simplement : "Simplifie le vocabulaire" ou "Ajoute un exemple concret"

### Éditeur de documents

**Types de documents disponibles** :
- Articles de blog (1000-2000 mots)
- Publications LinkedIn (format court optimisé)
- Retours d'expérience détaillés
- Comptes rendus de réunion

**Le texte s'affiche en direct** :
Le contenu apparaît progressivement pendant sa création.

## Installation et configuration (Guide pour débutants)

Vous n'avez pas besoin d'être développeur pour utiliser cet outil. Suivez simplement ces étapes une par une :

### 1. Installer Python
Python est le moteur qui fait tourner l'application.
1. Allez sur le site officiel : https://www.python.org/downloads/
2. Cliquez sur le bouton jaune "Download Python"
3. Lancez le fichier téléchargé
4. **TRÈS IMPORTANT** : Lors de l'installation, cochez bien la case "Add Python.exe to PATH" en bas de la fenêtre avant de cliquer sur "Install Now".

### 2. Télécharger le projet
Pas besoin d'utiliser de lignes de commande complexes :
1. Allez sur la page du projet (le dépôt où vous avez trouvé ce fichier)
2. Cliquez sur le bouton vert **"Code"** en haut à droite
3. Choisissez **"Download ZIP"**
4. Une fois téléchargé, faites un clic droit sur le fichier ZIP et choisissez **"Extraire tout"** 
5. Placez le dossier extrait où vous le souhaitez (par exemple, dans vos Documents).

### 3. Obtenir une clé d'Intelligence Artificielle (Gratuit)
L'outil a besoin du "cerveau" de Google (Gemini) pour fonctionner.
1. Allez sur : https://aistudio.google.com/app/apikey
2. Connectez-vous avec votre compte Google (Gmail)
3. Cliquez sur le bouton **"Create API key"**
4. Cliquez sur **"Create API key in a new project"**
5. Copiez la longue suite de caractères qui s'affiche (c'est votre clé secrète).

### 4. Configurer l'application
1. Ouvrez le dossier fraîchement extrait sur votre ordinateur.
2. Cherchez le fichier nommé `.env.example` (ou juste `.env` si votre ordinateur masque les extensions).
3. Faites-en une copie et renommez cette copie en `.env` (exactement comme ça, avec un point au début).
4. Ouvrez ce fichier `.env` avec le Bloc-notes (Windows) ou TextEdit (Mac).
5. Modifiez le fichier pour y coller votre clé et activer Gemini :
   ```text
   GEMINI_API_KEY=collez-votre-clé-ici
   USE_GEMINI=true
   ```
6. **Sécurité :** Modifiez également la ligne `AUTH_PASSWORD=` pour définir votre mot de passe d'accès à l'application.
7. Enregistrez et fermez le fichier.

### 5. Lancer l'application la première fois
1. Ouvrez l'outil de commande de votre ordinateur :
   - Sur Windows : Cherchez **"Invite de commandes"** ou **"cmd"** dans le menu Démarrer.
   - Sur Mac : Cherchez **"Terminal"** avec Spotlight.
2. Tapez `cd ` (avec un espace après le cd) puis glissez-déposez le dossier de l'application dans la fenêtre. Appuyez sur Entrée.
3. Tapez la commande suivante pour installer les composants nécessaires, et appuyez sur Entrée (selon votre version de Python, utilisez `pip` ou `pip3`) :
   ```bash
   pip install -r requirements.txt
   ```
   *(Attendez que le texte défile et que l'installation se termine)*
4. Une fois terminé, lancez l'application en tapant :
   ```bash
   python app.py
   ```
5. Ouvrez votre navigateur internet (Chrome, Safari, etc.) et tapez cette adresse : `http://localhost:8000`
   *(Note: Si vous avez activé le mode sécurisé SSL, l'adresse sera `https://localhost:8443`)*

L'application est prête à être utilisée !

## Configuration avancée

### Choix de l'intelligence artificielle

**Claude (Anthropic)** - Recommandé :
- Meilleure qualité de rédaction
- Excellente compréhension du contexte
- Nécessite une clé API Anthropic

**Gemini (Google)** - Alternative gratuite :
- Version gratuite disponible
- Bonne qualité
- Nécessite une clé API Google

Configuration dans le fichier `.env` :
```bash
# Pour Claude
ANTHROPIC_API_KEY=votre-clé
USE_GEMINI=false

# Pour Gemini
GEMINI_API_KEY=votre-clé
USE_GEMINI=true
```

### Ajouter vos références d'entreprise

Pour que l'outil utilise vos projets et expertises dans les propositions commerciales :

**1. Créer le fichier de références**

Créez `data/notebooklm/references.json` avec vos informations :
```json
{
  "projects": [
    {
      "title": "Nom du projet",
      "client": "Nom du client",
      "description": "Description du projet",
      "technologies": ["Technologie 1", "Technologie 2"],
      "results": "Résultats obtenus"
    }
  ],
  "expertise": [
    "Domaine d'expertise 1",
    "Domaine d'expertise 2"
  ],
  "methodologies": [
    "Méthodologie 1",
    "Méthodologie 2"
  ]
}
```

**2. Ajouter les CV consultants**

Placez le fichier PowerPoint `Biographies - CV All Consulting Tools.pptx` à la racine du projet.
Les CV seront automatiquement utilisés dans les propositions commerciales.

## Génération d'images (optionnel)

### État actuel

La génération d'images n'est actuellement pas active car le service Google Imagen ne fonctionne pas correctement.

### Solution recommandée : DALL-E (OpenAI)

Pour activer la génération automatique d'illustrations :

**1. Obtenir une clé OpenAI**
- Créer un compte sur https://platform.openai.com
- Créer une clé API

**2. Installer le package**
```bash
pip install openai
```

**3. Configurer**
```bash
# Dans .env
OPENAI_API_KEY=votre-clé-openai
```

**4. Suivre le guide d'intégration**

Le fichier `docs/DALLE_INTEGRATION.md` contient toutes les instructions détaillées pour activer la génération d'images.

**Coûts** :
- Article : environ 8 centimes par image
- Présentation 10 slides : environ 32 centimes pour 4 images
- Formation 20 slides : environ 56 centimes pour 7 images

## Types de slides générées

| Type | Description | Avec image |
|------|-------------|------------|
| Page de couverture | Première page avec titre | Non |
| Séparateur | Transition entre sections | Non |
| Contenu | Texte principal et points clés | Oui |
| Points clés | Informations importantes à retenir | Oui |
| Statistiques | Chiffres et données | Oui |
| Diagramme | Schémas et processus | Oui |
| Image | Slide principalement visuelle | Oui |
| Tableau | Données organisées | Non |
| Deux colonnes | Comparaison ou liste | Oui |
| Citation | Témoignage ou phrase marquante | Non |
| CV | Présentation d'un consultant | Non |
| Conclusion | Dernière slide avec contacts | Non |

## Utilisation quotidienne

### Créer une présentation

1. Ouvrir l'application dans le navigateur
2. Cliquer sur "Slide Editor"
3. Choisir le type (Présentation, Formation, Proposition, REX)
4. Remplir les champs :
   - Sujet principal
   - Audience visée
   - Contexte ou informations complémentaires
5. Cliquer sur "Générer"
6. Attendre quelques secondes : les slides apparaissent en temps réel
7. Si besoin, demander des corrections

### Créer un document

1. Ouvrir l'application dans le navigateur
2. Cliquer sur "Document Editor"
3. Choisir le type (Article, LinkedIn, REX, Compte Rendu)
4. Remplir les champs :
   - Titre ou sujet
   - Audience visée
   - Points clés à couvrir
5. Cliquer sur "Générer"
6. Le texte s'affiche progressivement
7. Si besoin, demander des modifications

### Exemples de corrections

**Pour une présentation** :
- "Simplifie la slide 3 pour un public non-technique"
- "Ajoute plus de détails techniques sur la slide 5"
- "Réduis le texte de la slide 2, c'est trop dense"
- "Ajoute un exemple concret sur la méthodologie"

**Pour un document** :
- "Rend l'introduction plus percutante"
- "Ajoute des exemples chiffrés"
- "Simplifie le vocabulaire"
- "Développe la section sur les bénéfices"

## Architecture du projet

```
consulting-tools/
├── app.py                      Application web principale
├── templates/                  Pages web de l'interface
│   ├── index.html             Page d'accueil
│   ├── slide-editor.html      Éditeur de présentations
│   └── document-editor.html   Éditeur de documents
├── agents/                     Modules de génération spécialisés
├── utils/                      Outils techniques
├── data/                       Données (références, images)
├── output/                     Fichiers générés
├── docs/                       Documentation technique
└── requirements.txt            Liste des composants nécessaires
```

## Problèmes fréquents et solutions

### L'application ne démarre pas

**Vérifier** :
- Python est bien installé : `python --version`
- Les composants sont installés : `pip install -r requirements.txt`
- Le fichier `.env` est configuré avec les clés d'accès

### Les slides ne se génèrent pas

**Vérifier** :
- La clé API (ANTHROPIC_API_KEY ou GEMINI_API_KEY) est valide
- Vous avez une connexion Internet
- Le message d'erreur affiché pour plus de détails

### La qualité n'est pas satisfaisante

**Améliorer les résultats** :
- Donnez plus de détails dans votre description initiale
- Précisez bien l'audience et le contexte
- Utilisez les corrections en langage naturel pour affiner
- Essayez Claude (Anthropic) si vous utilisez Gemini

## Notes techniques importantes

### Version Python

L'application fonctionne avec Python 3.12 ou plus récent. Les versions plus anciennes peuvent causer des erreurs.

### Service d'intelligence artificielle déprécié

Le service Google "google-generativeai" utilisé initialement ne reçoit plus de mises à jour. C'est pourquoi la génération d'images n'est temporairement pas disponible. La solution recommandée est d'utiliser DALL-E (OpenAI) à la place.

## Évolutions futures

**Fonctionnalités prévues** :
- Export des présentations en format PowerPoint
- Export des documents en PDF
- Bibliothèque d'images réutilisables
- Publication automatique sur LinkedIn
- Tableau de bord de veille technologique
- Templates de slides personnalisables
- Édition collaborative en temps réel

**Intégrations prévues** :
- Outils de gestion client (CRM)
- Calendriers et agendas
- Services de stockage cloud
- Plateformes de visioconférence

## Support et documentation

**Documentation technique** :
- `docs/DALLE_INTEGRATION.md` : Guide complet pour activer les images
- `docs/FEATURES_IMAGES.md` : Documentation sur la génération d'images
- `docs/SETUP_IMAGEN.md` : (Déprécié - ne plus utiliser)

**Obtenir de l'aide** :
- Créer un ticket sur le dépôt GitHub
- Contacter l'équipe support Consulting Tools
- Consulter la documentation dans le dossier `docs/`

## Licence et droits

Propriété de Consulting Tools - Tous droits réservés

---

**Développé par Consulting Tools** - Conseil en stratégie data et intelligence artificielle
