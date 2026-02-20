# 📦 Données personnelles - Guide d'onboarding

Bienvenue ! Ce dossier contient vos données personnelles pour personnaliser les agents IA.

## 🎯 Fichiers à personnaliser

### 1. **personality.md** (OBLIGATOIRE)
Vos convictions, votre style d'écriture, vos thèmes de prédilection.

**Structure recommandée** :
```markdown
# Personnalité et Convictions

## Vision
- Votre philosophie sur la data/IA
- Vos valeurs professionnelles

## Style d'écriture
- Ton (expert, accessible, etc.)
- Approche (pragmatique, critique, pédagogique)

## Convictions clés
- Vos croyances fortes sur l'IA/data
- Ce qui vous différencie

## Thèmes de prédilection
- ROI de l'IA
- Gouvernance
- etc.
```

### 2. **linkedin_profile.json** (OPTIONNEL)
Vos informations LinkedIn de base.

**Structure** :
```json
{
  "name": "Votre nom",
  "title": "Votre titre",
  "company": "Votre entreprise",
  "bio": "Votre bio courte",
  "experiences": [
    {
      "title": "Poste",
      "company": "Entreprise",
      "description": "Description"
    }
  ],
  "recent_posts": []
}
```

### 3. **linkedin_persona.md** (OPTIONNEL - AVANCÉ)
Votre style de communication LinkedIn détaillé.

Définissez :
- Ton et style (ex: "Parisien GenZ", "Expert corporate", etc.)
- Expressions typiques
- Structure de vos posts
- Thématiques favorites
- Exemples de posts

**⚠️ Ces fichiers ne seront JAMAIS poussés sur Git** (protégés par `.gitignore`)

## 🚀 Démarrage rapide

### Option A : Utilisation par défaut
Ne rien faire ! L'application créera des templates automatiquement.

### Option B : Personnalisation rapide (5 min)
1. Ouvrez `personality.md`
2. Modifiez les sections Vision, Style, Convictions
3. Sauvegardez

### Option C : Personnalisation complète (30 min)
1. Remplissez `personality.md` avec vos vraies convictions
2. Créez `linkedin_profile.json` avec vos expériences
3. (Optionnel) Créez `linkedin_persona.md` pour affiner votre style LinkedIn

## 📝 Comment ces données sont utilisées

### Dans le **générateur d'articles** (checkbox "Contexte enrichi") :
- `personality.md` → Ton, style, convictions injectés dans le prompt
- `linkedin_persona.md` → Style de communication LinkedIn
- Articles précédents → Analyse de votre vocabulaire habituel
- Veille tech → Tendances actuelles pour rester à jour

### Dans les **autres agents** :
- Formation Generator → Adapte le ton pédagogique
- Article Generator → Garantit la cohérence de voix
- (À venir) LinkedIn Post Generator → Utilise persona + posts récents

## 🔒 Sécurité

✅ **Fichiers protégés par .gitignore** :
- `data/linkedin_profile.json`
- `data/linkedin_persona.md`
- `data/linkedin_profile/` (dossier entier)

❌ **NE JAMAIS commiter** :
- Vos vraies données LinkedIn
- Vos informations personnelles

## 🆘 Besoin d'aide ?

**Créer personality.md** :
```bash
# L'application le créera automatiquement au premier lancement
# Ou copiez le template ci-dessus
```

**Créer linkedin_profile.json** :
```bash
# Copiez la structure JSON ci-dessus
# Ou laissez l'application créer un template par défaut
```

**Tester vos données** :
```bash
python utils/consultant_profile.py
# Affiche le contexte chargé
```

---

**💡 Astuce** : Commencez simple ! Remplissez juste `personality.md` avec 3-4 convictions clés. Vous affinerez au fur et à mesure.
