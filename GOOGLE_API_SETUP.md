# Configuration des API Google

Ce guide vous explique comment configurer l'accès aux API Google pour utiliser les agents Consulting Tools.

## Prérequis

- Un compte Google
- Accès à [Google Cloud Console](https://console.cloud.google.com/)

## Étape 1: Créer un projet Google Cloud

1. Accédez à [Google Cloud Console](https://console.cloud.google.com/)
2. Cliquez sur le sélecteur de projet en haut de la page
3. Cliquez sur "Nouveau projet"
4. Nommez votre projet (ex: "Consulting Tools-Agents")
5. Cliquez sur "Créer"

## Étape 2: Activer les API nécessaires

Dans Google Cloud Console, activez les API suivantes:

1. **Google Drive API**
   - Permet de lire les fichiers sur Drive
   - URL: https://console.cloud.google.com/apis/library/drive.googleapis.com

2. **Google Slides API**
   - Permet de lire les présentations
   - URL: https://console.cloud.google.com/apis/library/slides.googleapis.com

3. **Google Docs API**
   - Permet de lire les documents
   - URL: https://console.cloud.google.com/apis/library/docs.googleapis.com

Pour chaque API:
- Recherchez l'API dans la bibliothèque
- Cliquez sur l'API
- Cliquez sur "Activer"

## Étape 3: Créer des identifiants OAuth 2.0

1. Dans Google Cloud Console, allez dans **APIs & Services > Credentials**
2. Cliquez sur "Créer des identifiants"
3. Sélectionnez "ID client OAuth"
4. Configuration:
   - Type d'application: **Application de bureau**
   - Nom: "Consulting Tools Agents Client"
5. Cliquez sur "Créer"
6. Téléchargez le fichier JSON des identifiants
7. Renommez le fichier en `google_credentials.json`
8. Placez-le dans le dossier `config/` du projet

```bash
mv ~/Downloads/client_secret_*.json config/google_credentials.json
```

## Étape 4: Configurer l'écran de consentement OAuth

Si c'est votre première fois:

1. Allez dans **APIs & Services > OAuth consent screen**
2. Sélectionnez "Externe" (ou "Interne" si vous avez Google Workspace)
3. Remplissez les informations:
   - Nom de l'application: "Consulting Tools Agents"
   - Email d'assistance utilisateur: votre email
   - Domaine autorisé: (laisser vide pour usage local)
4. Cliquez sur "Enregistrer et continuer"
5. Scopes: passez cette étape (les scopes sont déjà définis dans le code)
6. Testeurs: ajoutez votre adresse email
7. Cliquez sur "Enregistrer et continuer"

## Étape 5: Premier lancement et authentification

La première fois que vous utilisez un agent, vous devrez vous authentifier:

```bash
# Depuis le dossier Consulting Tools-agents
python agents/proposal_generator.py data/examples/appel_offre_example.txt
```

1. Une fenêtre de navigateur s'ouvrira
2. Connectez-vous avec votre compte Google
3. Autorisez l'accès aux API demandées
4. Un fichier `config/token.pickle` sera créé automatiquement
5. Les prochaines exécutions n'auront plus besoin d'authentification

## Étape 6: Partager vos documents avec l'application

Pour que les agents puissent accéder à vos documents Google:

### Option A: Rendre les documents publics (lecture seule)
1. Ouvrez votre document/présentation
2. Cliquez sur "Partager"
3. Changez l'accès à "Tous les utilisateurs ayant le lien peuvent consulter"

### Option B: Partager avec votre email (recommandé)
1. Les documents seront automatiquement accessibles si vous êtes authentifié avec le bon compte

## Configuration NotebookLM

⚠️ **Important**: NotebookLM n'a pas d'API publique pour le moment.

### Solution temporaire: Export manuel

1. Ouvrez votre notebook NotebookLM
2. Exportez le contenu (copier-coller ou screenshot)
3. Créez un fichier JSON structuré:

```json
{
  "projects": [
    {
      "title": "Projet 1",
      "client": "Client A",
      "description": "Description du projet",
      "technologies": ["Python", "Azure", "ML"],
      "results": "Résultats obtenus"
    }
  ],
  "expertise": [
    "Data Science",
    "Machine Learning",
    "Cloud Azure/AWS"
  ],
  "methodologies": [
    "Agile",
    "Design Sprint",
    "POC/MVP"
  ]
}
```

4. Sauvegardez dans `data/notebooklm/references.json`

### Solution future

Lorsque Google publiera une API pour NotebookLM, le code sera mis à jour automatiquement.

## Vérification de la configuration

Testez votre configuration:

```bash
# Installer les dépendances
pip install -r requirements.txt

# Tester l'accès Google API
python -c "from utils.google_api import GoogleAPIClient; client = GoogleAPIClient(); print('✅ Configuration OK')"
```

## Dépannage

### Erreur "credentials not found"
- Vérifiez que `config/google_credentials.json` existe
- Vérifiez les chemins dans votre `.env`

### Erreur "insufficient permissions"
- Vérifiez que les API sont bien activées dans Google Cloud Console
- Supprimez `config/token.pickle` et réauthentifiez-vous

### Erreur "access denied"
- Vérifiez que vous êtes authentifié avec le bon compte Google
- Vérifiez que les documents sont bien partagés ou publics

## Sécurité

⚠️ **Important**:
- Ne committez JAMAIS `google_credentials.json` dans Git
- Ne partagez JAMAIS `token.pickle`
- Ces fichiers sont déjà dans `.gitignore`
- Utilisez des variables d'environnement pour les données sensibles

## Ressources

- [Documentation Google Drive API](https://developers.google.com/drive/api/guides/about-sdk)
- [Documentation Google Slides API](https://developers.google.com/slides/api/guides/concepts)
- [OAuth 2.0 pour applications de bureau](https://developers.google.com/identity/protocols/oauth2/native-app)
