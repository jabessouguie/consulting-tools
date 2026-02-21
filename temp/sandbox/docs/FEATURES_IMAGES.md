# Génération d'images avec Nano Banana Pro

## Vue d'ensemble

L'application intègre maintenant **Nano Banana Pro** (Google Imagen) pour générer automatiquement des illustrations premium pour :

1. **Document Editor** : Articles de blog
2. **Slide Editor** : Présentations, formations, propositions commerciales

## 1. Document Editor - Illustrations d'articles

### Fonctionnement

Lorsque vous générez un article dans le Document Editor, le système :

1. Génère le contenu de l'article
2. Crée automatiquement une illustration premium via Nano Banana Pro
3. Sauvegarde l'image dans `output/images/`
4. Retourne le chemin de l'image avec l'article

### Types de documents

- ✅ **Articles de blog** : Illustration automatique
- ✅ **Posts LinkedIn** : Illustration automatique
- ✅ **REX (Retour d'expérience)** : Illustration automatique

### Style des illustrations

- **Aesthetic** : Unreal Engine 5 render, cinematic, 8K resolution
- **Mood** : Sophistiqué, futuriste mais ancré, "Corporate Tech"
- **Lighting** : Contraste dramatique entre bleus électriques (AI) et ambre/or (humain)
- **Format** : 16:9 paysage, JPEG optimisé

### Exemple de prompt utilisé

```python
"""Role & Objective: You are an expert Art Director for a high-end tech consultancy firm.
Your task is to generate a premium, cinematic illustration based on the Blog Post provided below.

Visual Style Guidelines:
* Aesthetic: Unreal Engine 5 render, isometric or wide-angle, 8k resolution.
* Mood: Sophisticated, futuristic but grounded, "Corporate Tech".
* Lighting: Dramatic contrast between cool electric blues (AI) and warm amber/gold (human touch).
* Composition: A central human figure controlling or structuring a massive, complex digital structure.

Input Text (The Blog Post):
{article_text[:3000]}

Action: Generate the illustration now based on this analysis."""
```

## 2. Slide Editor - Illustrations de slides

### Fonctionnement

Après la génération des slides, le système :

1. Identifie les slides qui bénéficieraient d'illustrations visuelles
2. Génère des images adaptées au contenu et au type de présentation
3. Ajoute automatiquement le chemin de l'image dans le JSON de la slide
4. Les images sont affichées dans le slide editor et exportables

### Types de présentations supportés

✅ **Présentations classiques** : Style corporate tech, moderne et sophistiqué
✅ **Formations** : Style pédagogique, engageant et clair
✅ **Propositions commerciales** : Style haut de gamme, impactant et professionnel
✅ **REX (Retours d'expérience)** : Style analytique et professionnel

### Types de slides illustrés

Le système génère des images pour ces types de slides :

- ✅ **content** : Slides de contenu principal
- ✅ **highlight** : Points clés et faits saillants
- ✅ **stat** : Statistiques et KPIs (visualisations)
- ✅ **diagram** : Diagrammes et flux (représentations visuelles)
- ✅ **image** : Slides prévues pour des images
- ✅ **two_column** : Slides à deux colonnes

### Slides NON illustrés

- ❌ **cover** : Page de couverture (design spécifique)
- ❌ **section** : Séparateurs de section (texte uniquement)
- ❌ **quote** : Citations (texte stylisé suffit)
- ❌ **cv** : CV consultants (photo déjà présente)
- ❌ **closing** : Page de conclusion/contact

### Style des illustrations slides

#### Présentations classiques
- **Format** : Wide 16:9 adapté aux présentations
- **Style** : Corporate tech aesthetic, clean et moderne
- **Palette** : Bleus froids, accents ambre/or
- **Mood** : Sophistiqué, futuriste mais ancré
- **Rendu** : Unreal Engine 5, qualité business

#### Formations
- **Format** : Wide 16:9 adapté aux formations
- **Style** : Éducationnel et professionnel, engageant
- **Palette** : Bleus accessibles, accents ambre/or chaleureux
- **Mood** : Pédagogique, inspirant, environnement d'apprentissage
- **Rendu** : Unreal Engine 5, clair et attractif

#### Propositions commerciales
- **Format** : Wide 16:9 adapté aux executive presentations
- **Style** : Haut de gamme corporate, sophistiqué et impactant
- **Palette** : Bleus premium, accents or/ambre exécutifs
- **Mood** : Professionnel, trustworthy, orienté résultats, winning proposal
- **Rendu** : Unreal Engine 5, qualité premium

#### REX (Retours d'expérience)
- **Format** : Wide 16:9 adapté aux présentations
- **Style** : Corporate tech aesthetic, analytique
- **Palette** : Bleus froids, accents ambre/or
- **Mood** : Professionnel, business presentation
- **Rendu** : Unreal Engine 5, qualité business

### Exemples de prompts pour slides

#### Formation
```python
"""Create a premium, professional illustration for a training presentation slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {bullets}

Style: Educational yet professional, Unreal Engine 5 render, engaging and clear.
Colors: Cool blues, warm amber/gold accents, approachable palette.
Mood: Pedagogical, inspiring, professional learning environment.
Format: Wide format suitable for training slides."""
```

#### Proposition commerciale
```python
"""Create a premium, professional illustration for a business proposal slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {bullets}

Style: High-end corporate, Unreal Engine 5 render, sophisticated and impactful.
Colors: Premium blues, gold/amber accents, executive palette.
Mood: Professional, trustworthy, results-oriented, winning proposal aesthetic.
Format: Wide format suitable for executive presentation."""
```

#### Présentation classique
```python
"""Create a premium, professional illustration for a business presentation slide.

Topic: {topic}
Slide Title: {title}
Content: {content}
Key Points: {bullets}

Style: Corporate tech aesthetic, Unreal Engine 5 render, clean and modern.
Colors: Cool blues, warm amber/gold accents, professional palette.
Mood: Sophisticated, futuristic but grounded, business presentation quality.
Format: Wide format suitable for presentation slides."""
```

## 3. Configuration

### Variables d'environnement requises

```bash
# Dans .env
GEMINI_API_KEY=votre_cle_api_gemini
```

### Obtenir une clé API

1. Allez sur https://aistudio.google.com/apikey
2. Créez une clé API
3. Ajoutez-la dans votre fichier `.env`

## 4. Performance et coûts

### Génération

- **Vitesse** : 2-4 secondes par image (Nano Banana Pro est optimisé pour la rapidité)
- **Format** : JPEG optimisé (~100-200 KB par image)
- **Résolution** : 1024×576 (16:9)

### Tarification

- **Nano Banana Pro** : ~$0.04 par image
- **Document Editor** : 1 image par article = $0.04
- **Slide Editor** : Variable selon le nombre de slides visuelles
  - **Présentation 10 slides** : ~3-5 images = $0.12-$0.20
  - **Formation 20 slides** : ~6-8 images = $0.24-$0.32
  - **Proposition commerciale 15 slides** : ~5-7 images = $0.20-$0.28
  - **REX 12 slides** : ~4-6 images = $0.16-$0.24

### Optimisations

- Les images sont générées uniquement pour les slides pertinentes
- Skip automatique des slides avec images déjà présentes
- Erreurs non-bloquantes : si une image échoue, le processus continue

## 5. Gestion des erreurs

### Échecs de génération

Si la génération d'image échoue :

- ✅ Le processus continue sans bloquer
- ✅ Les autres images sont générées normalement
- ✅ Le slide reste utilisable sans image
- ⚠️  Un message d'erreur est loggé

### Logs

```python
print(f"  [NanoBanana] Image generee: {output_path}")  # Succès
print(f"  [NanoBanana] Erreur generation: {e}")       # Échec
```

## 6. Emplacements des fichiers

### Articles

```
output/images/article_illustration_{timestamp}.jpg
```

### Slides

```
output/images/slides/slide_{index}_{timestamp}.jpg
```

## 7. Intégration dans le workflow

### Document Editor

```
1. Utilisateur soumet un sujet
2. LLM génère l'article (streaming)
3. → Nano Banana Pro génère l'illustration (3-4s)
4. Article + image retournés
5. Markdown affiché avec image intégrée
```

### Slide Editor

```
1. Utilisateur soumet brief + type
2. LLM génère les slides (streaming progressif)
3. → Nano Banana Pro génère images pour slides visuelles (parallèle)
4. Slides enrichies avec images
5. Affichage dans l'éditeur + export possible
```

## 8. Personnalisation

### Modifier les types de slides illustrés

Dans `app.py`, ligne ~4263 :

```python
visual_types = ["content", "highlight", "stat", "diagram", "image", "two_column"]
```

### Modifier le style des images

Dans `utils/image_generator.py`, ligne ~668 :

```python
prompt = f"""Visual Style Guidelines:
* Aesthetic: Votre style ici
* Mood: Votre mood ici
* Lighting: Votre lighting ici
..."""
```

### Changer le format d'image

Images slides en PNG au lieu de JPEG :

```python
output_path = str(output_dir / f"slide_{idx}_{timestamp}.png")
```

(Nota : JPEG est recommandé pour optimiser la taille)

## 9. Désactivation

Pour désactiver temporairement la génération d'images :

### Dans Document Editor

Commentez l'appel dans `agents/article_generator.py` :

```python
# result = self.generate_illustration(article)
```

### Dans Slide Editor

Commentez l'appel dans `app.py` :

```python
# _generate_slide_illustrations(job["slides"], job, topic)
```

## 10. Roadmap

Améliorations futures possibles :

- [ ] Choix du modèle (Nano Banana Pro vs Imagen 4)
- [ ] Styles personnalisables par utilisateur
- [ ] Cache d'images pour prompts similaires
- [ ] Génération asynchrone en background
- [ ] Preview avant génération finale
- [ ] Batch generation pour plusieurs slides
