# Configuration Imagen 3 (Nano Banana Pro) via google-genai SDK

## 1. Installation des dépendances

```bash
pip install -r requirements.txt
```

Cela installera `google-genai>=0.2.0` nécessaire pour Imagen 3.

## 2. Obtenir une clé API Gemini

### 2.1 Créer une clé API

1. Allez sur [Google AI Studio](https://aistudio.google.com/apikey)
2. Cliquez sur **Get API Key** ou **Create API Key**
3. Copiez la clé générée

**Note** : Aucune configuration Google Cloud n'est nécessaire ! Le SDK `google-genai` utilise simplement une clé API, comme OpenAI ou Anthropic.

### 2.2 Configurer le fichier .env

Ajoutez la clé dans votre fichier `.env` :

```bash
# Gemini Configuration
GEMINI_API_KEY=votre_cle_api_gemini_ici
```

C'est tout ! Pas besoin de credentials GCP, de projet, ou de Vertex AI.

## 3. Tester l'intégration

```bash
python3 test_imagen.py
```

Si tout est bien configuré, vous devriez voir :

```
✅ GEMINI_API_KEY: AIzaSyC...
  [NanoBanana] Initialise avec Imagen 3 via google-genai SDK
  [NanoBanana] Image generee: output/images/test_imagen.jpg
✅ Image generee avec succes: output/images/test_imagen.jpg
   Taille: 142.3 KB
```

## 4. Utilisation dans l'application

Une fois configuré, Imagen 3 sera automatiquement utilisé pour :

- **Document Editor** : génération d'illustrations pour les articles de blog
- **Article Generator** : illustrations premium pour les posts LinkedIn

### Modèle utilisé : `models/imagen-4.0-fast-generate-001`

- ⚡ Rapide (3-5 secondes par image)
- 🎨 Qualité élevée (Imagen 4 Fast)
- 💰 Coût optimisé (~$0.04 par image)
- 🖼️ Format 16:9 par défaut (paysage)
- 📦 JPEG par défaut (meilleure compression)
- ⏱️ Timeout étendu (120s) pour fiabilité

## 5. Avantages vs Vertex AI

### Avec `google-genai` (cette implémentation) ✅
- ✅ Configuration simple : juste une clé API
- ✅ Pas de projet GCP requis
- ✅ Pas de service account ou credentials JSON
- ✅ Même simplicité que OpenAI ou Anthropic
- ✅ Facturation directe sur la clé API

### Avec Vertex AI (ancienne approche) ❌
- ❌ Configuration complexe : projet GCP, service account, IAM, etc.
- ❌ Credentials JSON à gérer
- ❌ Configuration multi-étapes
- ❌ Facturation au niveau projet GCP

## 6. Tarification

- **Imagen 3** : ~$0.04 par image (1024x1024)
- Facturation via Google AI Studio (même compte que la clé API)
- [Voir la tarification Google AI](https://ai.google.dev/pricing)

## 7. Limites et quotas

- Quotas par défaut généreux pour usage personnel/dev
- Pour production : demander augmentation de quota sur AI Studio
- Rate limiting : ~60 images/minute

## 8. Dépannage

### Erreur : "API key not valid"
→ Vérifiez que votre clé API est correcte et active sur AI Studio

### Erreur : "Quota exceeded"
→ Attendez 1 minute ou demandez augmentation de quota

### Erreur : "Import error: No module named 'google.genai'"
→ Installez le package : `pip install google-genai`

### Erreur : "Safety filter triggered"
→ Le prompt contient du contenu filtré par les safety filters. Reformulez le prompt.

## 9. Configuration avancée

### Changer le format d'image

Dans `utils/image_generator.py`, ligne ~607 :

```python
config=dict(
    number_of_images=1,
    output_mime_type="image/png",  # ou "image/jpeg"
    aspect_ratio="16:9"  # ou "1:1", "9:16", "4:3", "3:4"
)
```

### Générer plusieurs images

```python
config=dict(
    number_of_images=4,  # Jusqu'à 4 images en une requête
    ...
)
```
