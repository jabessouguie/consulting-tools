# 📚 Guide Utilisateur - Consulting Tools Agents IA

**Version 1.0 - Février 2026**

Bienvenue ! Ce guide vous explique comment utiliser les agents IA de Consulting Tools **sans aucune compétence en programmation**.

---

## 🚀 Démarrage rapide

### Lancer l'application

1. **Ouvrez le Terminal** (sur Mac) ou **Invite de commandes** (sur Windows)
2. **Naviguez vers le dossier** du projet :
   ```bash
   cd /chemin/vers/consulting-tools
   ```
3. **Lancez l'application** :
   ```bash
   python3.12 app.py
   ```
4. **Ouvrez votre navigateur** et allez sur : `http://localhost:5678`

🎉 **C'est tout !** L'interface web est maintenant accessible.

---

## 🤖 Les Agents disponibles

### 1. 📝 **Article Generator** - Générer des articles de blog

**À quoi ça sert ?**
Transforme une simple idée en article de blog complet, rédigé avec le style Consulting Tools.

**Comment l'utiliser ?**

1. Cliquez sur **"Article"** dans la barre de navigation
2. **Décrivez votre idée** dans la zone de texte (exemple : _"L'IA générative va-t-elle remplacer les data scientists ?"_)
3. Cliquez sur **"Générer l'article"**
4. Attendez quelques secondes ⏳
5. **Téléchargez le résultat** :
   - **📥 .md** : Fichier Markdown (texte brut)
   - **📄 .pdf** : Version PDF (nécessite LibreOffice installé)

**Astuces** :
- ✅ Soyez spécifique dans votre idée
- ✅ Donnez du contexte (public cible, angle, etc.)
- ✅ Utilisez le feedback pour régénérer avec des modifications

---

### 2. 🎓 **Formation Generator** - Créer des programmes de formation

**À quoi ça sert ?**
Génère un programme de formation complet à partir d'un besoin client.

**Comment l'utiliser ?**

1. Cliquez sur **"Formation"** dans la barre de navigation
2. **Décrivez le besoin** du client (exemple : _"Formation introduction à l'IA pour managers, 2 jours, niveau débutant"_)
3. Cliquez sur **"Générer le programme"**
4. Le programme sera généré avec :
   - Objectifs pédagogiques
   - Modules et contenu détaillé
   - Ateliers pratiques
   - Planning

**Télécharger en différents formats** :
- **📥 .md** : Markdown
- **📄 .pdf** : PDF (avec pandoc installé)
- **📤 Google Docs** : Export direct vers Google Docs (nécessite configuration API Google)

---

### 3. 🎨 **Training Slides Generator** - Créer des slides de formation

**À quoi ça sert ?**
Transforme un programme de formation en slides PowerPoint professionnelles.

**Comment l'utiliser ?**

1. Cliquez sur **"Slides Formation"** dans la barre de navigation
2. **Fournissez le programme** de deux façons :
   - **Coller le texte** directement dans la zone de texte
   - **Uploader un fichier** : .md, .txt, .docx, ou .pdf
3. Cliquez sur **"Générer toutes les slides"**
4. **Téléchargez** :
   - **📥 .pptx** : PowerPoint
   - **📄 .pdf** : PDF des slides (nécessite LibreOffice)
   - **📤 Google Slides** : Export vers Google Slides

**Formats d'entrée supportés** :
- ✅ Markdown (.md)
- ✅ Texte brut (.txt)
- ✅ Word (.docx) - nécessite python-docx
- ✅ PDF (.pdf) - nécessite PyPDF2

---

### 4. 💼 **Proposal Generator** - Générer des propositions commerciales

**À quoi ça sert ?**
Crée des propositions commerciales professionnelles avec slides PowerPoint.

**Comment l'utiliser ?**

1. Cliquez sur **"Propositions"** dans la barre de navigation
2. **Collez le texte** de l'appel d'offres
3. Cliquez sur **"Analyser"**
4. **Générez chaque section** individuellement (Contexte, Approche, Planning, Budget, CVs...)
5. **Téléchargez** :
   - **📥 .pptx** : Présentation PowerPoint
   - **📄 .pdf** : Version PDF

**Sections disponibles** :
- 📊 **Contexte** : Enjeux et objectifs
- 🎯 **Approche** : Vision et méthodologie
- 📅 **Planning** : Phases du projet
- 💰 **Chiffrage** : Estimation budgétaire
- 📚 **Références** : Projets similaires
- 👤 **CVs** : Équipe adaptée au projet

---

### 5. 📧 **Meeting Summarizer** - Résumer des réunions

**À quoi ça sert ?**
Analyse un transcript de réunion et génère un compte rendu structuré + email de partage.

**Comment l'utiliser ?**

1. Cliquez sur **"Compte Rendu"** dans la barre de navigation
2. **Collez le transcript** de la réunion (ou uploadez un fichier .txt, .pdf)
3. Cliquez sur **"Générer le compte rendu"**
4. Vous obtenez :
   - ✅ **Compte rendu** structuré avec décisions, actions, et prochaines étapes
   - ✅ **Email de partage** prêt à envoyer

---

### 6. 💬 **LinkedIn Tools** - Gérer votre présence LinkedIn

#### **Veille LinkedIn** (LinkedIn Monitor)

**À quoi ça sert ?**
Surveille des mots-clés sur LinkedIn et génère des posts à partir d'articles pertinents.

**Comment l'utiliser ?**

1. Cliquez sur **"LinkedIn"** dans la barre de navigation
2. **Entrez vos mots-clés** (exemple : _"IA générative, data science, transformation digitale"_)
3. Ajustez le **nombre d'articles** à analyser
4. Choisissez le **ton** du post (professionnel, technique, inspirant)
5. Cliquez sur **"Lancer la veille + génération"**
6. **Copiez les posts** générés et publiez-les sur LinkedIn !

#### **Article → Post LinkedIn** (Article to Post)

**À quoi ça sert ?**
Transforme un article web en post LinkedIn engageant.

**Comment l'utiliser ?**

1. Cliquez sur **"Post"** dans la barre de navigation
2. **Collez l'URL** de l'article
3. Choisissez le **ton** du post
4. Cliquez sur **"Générer le post"**
5. Vous obtenez 2 versions :
   - **Version longue** (3-4 paragraphes)
   - **Version courte** (2-3 lignes)

#### **Commentaire LinkedIn** (LinkedIn Commenter)

**À quoi ça sert ?**
Génère des commentaires pertinents et constructifs pour des posts LinkedIn.

**Comment l'utiliser ?**

1. Cliquez sur **"Commentaire"** dans la barre de navigation
2. **Collez le contenu** du post LinkedIn
3. Choisissez le **type de commentaire** :
   - 👍 Approbation
   - 💡 Complément d'information
   - ❓ Question ouverte
   - 📊 Partage d'expérience
4. Cliquez sur **"Générer les commentaires"**

---

### 7. 📊 **Dataset Analyzer** - Analyser des données

**À quoi ça sert ?**
Analyse un fichier CSV et génère des insights, visualisations, et recommandations.

**Comment l'utiliser ?**

1. Cliquez sur **"Analyse Data"** dans la barre de navigation
2. **Uploadez votre fichier CSV**
3. **Décrivez votre objectif** (exemple : _"Identifier les tendances de ventes par région"_)
4. Cliquez sur **"Analyser le dataset"**
5. Vous obtenez :
   - 📊 **Statistiques descriptives**
   - 📈 **Visualisations** (graphiques PNG)
   - 💡 **Insights et recommandations**

---

### 8. 🔍 **Tech Watch** - Veille technologique

**À quoi ça sert ?**
Génère un digest de veille technologique à partir de mots-clés.

**Comment l'utiliser ?**

1. Cliquez sur **"Veille Tech"** dans la barre de navigation
2. **Entrez vos mots-clés** (exemple : _"MLOps, DataOps, Feature Store"_)
3. Choisissez le **nombre d'articles** à inclure
4. Cliquez sur **"Générer le digest"**
5. Vous obtenez un **digest structuré** avec :
   - Résumé exécutif
   - Tendances identifiées
   - Articles clés avec liens

---

## ⚙️ Configuration avancée (optionnel)

### Installer LibreOffice pour les conversions PDF

**Pourquoi ?** Pour pouvoir télécharger les PPTX et articles en PDF.

**Comment ?**

- **Mac** : `brew install --cask libreoffice`
- **Linux** : `sudo apt install libreoffice`
- **Windows** : Télécharger depuis [libreoffice.org](https://www.libreoffice.org/)

### Installer les bibliothèques pour DOCX/PDF

**Pour lire les fichiers DOCX et PDF** :

```bash
pip install python-docx PyPDF2
```

### Configurer l'API Google (pour Google Docs/Slides)

**Étapes** :

1. Créez un projet sur [Google Cloud Console](https://console.cloud.google.com)
2. Activez les APIs **Google Docs** et **Google Slides**
3. Créez des identifiants OAuth 2.0
4. Téléchargez le fichier `credentials.json` et placez-le dans le dossier du projet
5. Au premier export Google, vous devrez autoriser l'application

**Documentation complète** : [Guide Google API](https://developers.google.com/workspace/guides/create-credentials)

---

## 🎨 Personnalisation

### Modifier les informations consultant

Éditez le fichier `.env` à la racine du projet :

```env
CONSULTANT_NAME=Jean-Sébastien Abessouguie Bayiha
CONSULTANT_TITLE=Consultant en stratégie data et IA
COMPANY_NAME=Consulting Tools
```

### Ajouter votre style d'écriture

Créez un fichier `data/writing_style.md` avec des exemples de votre style :

```markdown
# Mon Style d'Écriture

- Ton expert mais accessible
- Exemples concrets et cas d'usage
- Vulgarisation sans simplification
- Questions rhétoriques pour engager le lecteur
...
```

---

## 🔧 Dépannage

### L'application ne démarre pas

**Vérifiez** :
- ✅ Python 3.12 est installé : `python3.12 --version`
- ✅ Les dépendances sont installées : `pip install -r requirements.txt`
- ✅ Le port 5678 est libre (pas utilisé par une autre application)

### "Conversion PDF échouée"

**Solution** :
- Installez LibreOffice (voir section Configuration avancée)
- Vérifiez que LibreOffice est bien dans votre PATH

### "Impossible d'extraire le texte du DOCX/PDF"

**Solution** :
- Installez les bibliothèques : `pip install python-docx PyPDF2`
- Vérifiez que le fichier n'est pas protégé par mot de passe

### "Rate limit exceeded"

**Solution** :
- Attendez quelques minutes avant de relancer
- Les agents ont des limites : 3-5 requêtes par minute
- Utilisez le feedback pour régénérer au lieu de relancer complètement

---

## 📞 Support

**Besoin d'aide ?**

- 📧 Email : [votre-email@consulting-tools.com]
- 💬 Slack : #consulting-tools
- 🐛 Bug report : [GitHub Issues](https://github.com/votre-repo/issues)

---

## 📝 Notes importantes

- 🔒 **Confidentialité** : Les données ne sont pas stockées en ligne, tout est local
- 💾 **Sauvegarde** : Les fichiers générés sont dans le dossier `output/`
- 🔄 **Feedback** : Utilisez la fonction de feedback pour améliorer les résultats
- 🎯 **Qualité** : Plus votre input est précis, meilleur sera le résultat

---

**Version** : 1.0
**Dernière mise à jour** : 17 février 2026
**Auteur** : Consulting Tools
