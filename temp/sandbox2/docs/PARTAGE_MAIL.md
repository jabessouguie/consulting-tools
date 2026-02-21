# 📧 Fonctionnalité de Partage par Mail

## Vue d'ensemble

La fonctionnalité **"Partager par mail"** permet d'envoyer rapidement le mail de compte rendu généré via le client mail par défaut de l'utilisateur.

## Comment ça fonctionne

### 1. Interface utilisateur

Sur la page **Compte Rendu** ([/meeting](http://localhost:8000/meeting)), après la génération d'un compte rendu, deux boutons sont disponibles dans la section "Mail de partage" :

- **📋 Copier** : Copie le contenu du mail dans le presse-papier
- **📧 Partager par mail** : Ouvre le client mail avec le contenu pré-rempli

### 2. Fonctionnement technique

#### Parsing du mail
La fonction `shareByEmail()` dans [`app.js`](../static/app.js) :
1. Récupère le contenu du mail généré
2. Extrait l'**objet** (format: `**Objet :** ...` ou `Objet: ...`)
3. Extrait le **corps** du mail (tout ce qui suit l'objet)
4. Nettoie les séparateurs markdown (`---`)

#### Génération du lien mailto
```javascript
const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
window.location.href = mailtoLink;
```

Le lien `mailto:` ouvre le client mail par défaut avec :
- **Sujet** pré-rempli
- **Corps** pré-rempli
- **Destinataires** à compléter par l'utilisateur

### 3. Avantages

✅ **Simple** : Un seul clic pour préparer l'email
✅ **Flexible** : L'utilisateur peut modifier le contenu avant d'envoyer
✅ **Universel** : Fonctionne avec tous les clients mail (Outlook, Gmail, Thunderbird, Apple Mail, etc.)
✅ **Sécurisé** : Pas besoin de configurer SMTP, utilise le client local

### 4. Exemple de mail généré

```
**Objet :** CR - Réunion de suivi projet migration data TotalEnergies - 12/02/2026

---

Bonjour à tous,

Merci pour votre participation à notre réunion de suivi de cet après-midi.

**Résumé exécutif :**
L'audit des systèmes existants avance bien (85% réalisé)...

**Décisions clés :**
• Report du kick-off phase 2 de 2 semaines
• Validation du budget de 180 000 €

**Actions prioritaires :**
• **Sophie** : Transmettre la liste des participants (demain)
• **Jean-Sébastien** : Préparer le plan de formation (vendredi)

Bien cordialement,

Jean-Sébastien Abessouguie Bayiha
Consultant en stratégie data et IA
Consulting Tools
```

### 5. Limitations connues

⚠️ **Longueur du corps** : Certains clients mail peuvent limiter la longueur des liens `mailto:` (généralement 2000 caractères). Pour les mails très longs, utiliser le bouton "Copier" puis coller manuellement.

⚠️ **Client mail requis** : Un client mail doit être configuré sur l'ordinateur de l'utilisateur.

## Code source

### HTML ([templates/meeting.html](../templates/meeting.html))
```html
<button class="btn btn-secondary" onclick="shareByEmail()" title="Ouvrir dans votre client mail">
    📧 Partager par mail
</button>
```

### JavaScript ([static/app.js](../static/app.js))
```javascript
function shareByEmail() {
    const content = document.getElementById('email-content').innerText;

    // Extraire l'objet et le corps
    let subject = 'Compte rendu de réunion';
    let body = content;

    const lines = content.split('\n');
    for (let i = 0; i < Math.min(lines.length, 5); i++) {
        const line = lines[i].trim();
        const match = line.match(/^\*?\*?(Objet|Subject)\s*:?\*?\*?\s*(.+)$/i);
        if (match) {
            subject = match[2].trim();
            let bodyStartIdx = i + 1;
            while (bodyStartIdx < lines.length && lines[bodyStartIdx].trim() === '') {
                bodyStartIdx++;
            }
            body = lines.slice(bodyStartIdx).join('\n').trim();
            break;
        }
    }

    body = body.replace(/^---+$/gm, '').trim();

    const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailtoLink;
}
```

## Alternative : Envoi SMTP direct

Si l'utilisateur souhaite une fonctionnalité d'envoi d'email direct (sans ouvrir le client mail), il est possible d'implémenter une solution SMTP côté serveur :

1. Ajouter une route API `/api/meeting/send-email`
2. Configurer les credentials SMTP dans `.env`
3. Utiliser une bibliothèque Python comme `smtplib` ou `sendgrid`

Cette approche nécessite cependant :
- Configuration SMTP (serveur, port, credentials)
- Gestion des erreurs d'envoi
- Respect des règles anti-spam
- Saisie des destinataires par l'utilisateur

La solution actuelle (mailto) est plus simple et couvre la majorité des cas d'usage.
