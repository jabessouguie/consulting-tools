# Changelog - Consulting Tools Agents

## [2026-02-12] - Nouvelles fonctionnalités

### ✅ 1. Agent de Commentaires LinkedIn

**Fonctionnalité :** Génération automatique de commentaires pertinents sur les posts LinkedIn

**Accès :** [http://localhost:8000/comment](http://localhost:8000/comment)

**Caractéristiques :**
- Accepte du texte brut ou une URL LinkedIn
- Génère 3 variantes de commentaires :
  - **Court** (50-150 caractères) : Réaction rapide et percutante
  - **Moyen** (150-300 caractères) : Perspective plus développée
  - **Long** (300-500 caractères) : Analyse approfondie avec valeur ajoutée
- 4 styles disponibles :
  - **💡 Insightful** : Apporte une perspective experte complémentaire
  - **❓ Question** : Pose une question pertinente qui prolonge la réflexion
  - **🎯 Expérience** : Partage une expérience similaire de terrain
  - **🔍 Réaction** : Analyse et réagit au contenu avec tact
- Utilise le **persona "Parisien GenZ"** :
  - Ton authentique et direct (pas de bullshit corporate)
  - Apporte de la valeur, pas du blabla générique
  - Évite les formules type "Merci pour le partage"
  - Maximum 1 emoji ou pas du tout (🎯💡🔍)
- Compteur de caractères pour chaque variante
- Bouton "Copier" pour chaque commentaire
- **Boucle de feedback** : Régénération avec corrections

**Fichiers créés :**
- `agents/linkedin_commenter.py` - Agent de génération
- `templates/comment.html` - Interface web
- Routes API dans `app.py`
- Logique frontend dans `app.js`

**Utilisation CLI :**
```bash
python agents/linkedin_commenter.py "Texte du post LinkedIn" --style insightful
```

---

### ✅ 2. Bouton "Partager par mail" (Comptes rendus)

**Fonctionnalité :** Envoi rapide du mail de compte rendu via le client mail par défaut

**Accès :** Bouton "📧 Partager par mail" dans la page [/meeting](http://localhost:8000/meeting)

**Fonctionnement :**
1. Après génération d'un compte rendu, cliquez sur "📧 Partager par mail"
2. Votre client mail s'ouvre automatiquement avec :
   - **Objet** pré-rempli (ex: "CR - Réunion de suivi projet X - 12/02/2026")
   - **Corps** pré-rempli (résumé exécutif, décisions, actions, signature)
   - **Destinataires** à compléter manuellement
3. Modifiez si besoin et envoyez

**Avantages :**
- ✅ Un seul clic pour préparer l'email
- ✅ Pas besoin de configurer SMTP
- ✅ Fonctionne avec tous les clients mail (Outlook, Gmail, Thunderbird, Apple Mail...)
- ✅ Sécurisé (utilise le client local)
- ✅ Flexible (possibilité de modifier avant envoi)

**Code modifié :**
- `templates/meeting.html` - Ajout du bouton
- `static/app.js` - Fonction `shareByEmail()`
- Parsing intelligent du format `**Objet :** ...`

**Documentation :** Voir [`docs/PARTAGE_MAIL.md`](docs/PARTAGE_MAIL.md)

---

## Backlog restant

### 🔜 3. Suite d'agents de productivité
- Agent de veille technologique automatisée
- Agent d'analyse de datasets (génération de rapports)
- Agent de préparation de workshops/formations
- Agent de réponse aux RFP (Request for Proposal)

### 🔜 4. Sécurisation du site
- Authentification (login/password)
- HTTPS avec certificat SSL
- Sécurisation des variables d'environnement
- Rate limiting pour les API

---

## Historique précédent

### [2026-02-11] - Version initiale
- ✅ Agent de propositions commerciales (PPTX avec CVs)
- ✅ Agent de veille LinkedIn (RSS + génération de posts)
- ✅ Agent Article → Post LinkedIn
- ✅ Agent de compte rendu de réunion
- ✅ Boucle de feedback sur tous les modules
- ✅ Interface web avec FastAPI + SSE
- ✅ Persona "Parisien GenZ" pour les posts LinkedIn
- ✅ Fix rate limit 429 (génération PPTX en 2 étapes)

---

## Stack technique

**Backend :**
- Python 3.12
- FastAPI
- Claude Sonnet 4.5 (Anthropic API)
- BeautifulSoup4 (scraping)
- python-pptx (génération PPTX)

**Frontend :**
- Vanilla JavaScript (ES6+)
- Server-Sent Events (SSE)
- Markdown rendering (marked.js)

**Styling :**
- CSS custom avec design system Consulting Tools
- Palette : Anthracite, Corail, Rose poudré, Gris
- Polices : Chakra Petch (titres), Inter (corps)

---

*Dernière mise à jour : 12 février 2026*
