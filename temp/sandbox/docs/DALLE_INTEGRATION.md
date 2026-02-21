# Intégration DALL-E pour la génération d'images

## Problème Imagen

Les modèles Imagen de Google **ne sont pas accessibles** via le SDK `google-generativeai` avec `generate_content()`. Ils nécessitent :
- Soit l'API Vertex AI (complexe, credentials GCP)
- Soit une API différente non disponible dans le SDK actuel

## Solution : DALL-E (OpenAI)

DALL-E 3 d'OpenAI est :
- ✅ Simple à intégrer (clé API)
- ✅ Qualité excellente
- ✅ Rapide (5-10 secondes)
- ✅ API stable et documentée
- 💰 ~$0.04 par image (1024x1024) ou $0.08 (1024x1792)

## 1. Installation

```bash
pip install openai
```

Ou ajoutez dans `requirements.txt` :
```
openai>=1.0.0
```

## 2. Configuration

Dans `.env` :
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Obtenez une clé sur : https://platform.openai.com/api-keys

## 3. Code d'intégration

### Remplacer NanoBananaGenerator

Éditez `utils/image_generator.py` :

```python
class DALLEGenerator:
    """Generateur d'images via DALL-E 3 (OpenAI)"""

    def __init__(self):
        try:
            from openai import OpenAI

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY non trouvee dans .env")

            self.client = OpenAI(api_key=api_key)
            print(f"  [DALL-E] Initialise avec DALL-E 3")

        except Exception as e:
            print(f"  [DALL-E] Erreur initialisation: {e}")
            self.client = None

    def generate_image(self, prompt: str, output_path: str) -> Optional[str]:
        """
        Genere une image a partir d'un prompt via DALL-E 3

        Args:
            prompt: Description de l'image a generer
            output_path: Chemin de sortie pour l'image

        Returns:
            Chemin du fichier image genere, ou None si echec
        """
        if not self.client:
            print("  [DALL-E] Client non initialise")
            return None

        try:
            # Tronquer le prompt si trop long (max 4000 chars)
            if len(prompt) > 4000:
                prompt = prompt[:3997] + "..."

            # Generer l'image avec DALL-E 3
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Landscape pour presentations
                quality="standard",  # ou "hd" pour meilleure qualite (+$0.08)
                n=1
            )

            # Telecharger l'image
            image_url = response.data[0].url

            import requests
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()

            # Sauvegarder
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(img_response.content)

            print(f"  [DALL-E] Image generee: {output_path}")
            return output_path

        except Exception as e:
            print(f"  [DALL-E] Erreur generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_article_illustration(self, article_text: str, output_path: str) -> Optional[str]:
        """Genere une illustration pour un article"""
        # Meme prompt style qu'avant
        prompt = f"""A premium, cinematic illustration for a tech consulting blog post.

Article excerpt: {article_text[:1000]}

Style: Unreal Engine 5 render, isometric or wide-angle view, 8k quality.
Mood: Sophisticated, futuristic but grounded, corporate tech aesthetic.
Lighting: Dramatic contrast - cool electric blues (AI/data) and warm amber/gold (human guidance).
Composition: Central human figure orchestrating complex digital structures.
Format: Wide landscape suitable for blog header."""

        return self.generate_image(prompt, output_path)
```

### Mettre à jour les imports

Partout où `NanoBananaGenerator` est importé, remplacez par `DALLEGenerator` :

```python
# Avant
from utils.image_generator import NanoBananaGenerator
generator = NanoBananaGenerator()

# Après
from utils.image_generator import DALLEGenerator
generator = DALLEGenerator()
```

## 4. Réactiver la génération d'images

### Dans app.py (ligne ~4548)

Décommentez :
```python
# Generate illustrations for relevant slides
job["steps"].append({"message": "Generation des illustrations...", "step": 4})
_generate_slide_illustrations(job["slides"], job, topic, gen_type)
```

### Dans _generate_slide_illustrations (ligne ~4257)

Changez l'import :
```python
from utils.image_generator import DALLEGenerator
generator = DALLEGenerator()
```

### Dans article_generator.py (ligne ~235)

Décommentez :
```python
image_path = self.generate_illustration(article)
```

Et dans `generate_illustration()` (ligne ~140) :
```python
from utils.image_generator import DALLEGenerator
generator = DALLEGenerator()
```

## 5. Tailles et coûts DALL-E 3

| Taille | Usage | Coût (standard) | Coût (HD) |
|--------|-------|-----------------|-----------|
| 1024x1024 | Carré (Instagram) | $0.040 | $0.080 |
| 1792x1024 | Paysage (slides) | $0.080 | $0.120 |
| 1024x1792 | Portrait (mobile) | $0.080 | $0.120 |

**Recommandé** : `1792x1024` standard pour slides = $0.08/image

## 6. Comparaison

| Feature | Imagen (Vertex AI) | DALL-E 3 |
|---------|-------------------|----------|
| **Setup** | Complexe (GCP, credentials) | Simple (clé API) |
| **Qualité** | Excellente | Excellente |
| **Vitesse** | 3-5s | 5-10s |
| **Coût** | ~$0.04/image | $0.04-$0.12/image |
| **Fiabilité** | ❌ Non accessible actuellement | ✅ Stable |
| **Format max** | 1024x1024 | 1792x1024 |

## 7. Alternative : Replicate

Si vous préférez Stable Diffusion :

```bash
pip install replicate
```

```python
import replicate

client = replicate.Client(api_token=os.getenv('REPLICATE_API_TOKEN'))

output = client.run(
    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
    input={
        "prompt": prompt,
        "width": 1792,
        "height": 1024
    }
)
```

Coût : ~$0.0025 par image (beaucoup moins cher !)

## 8. Résumé

**Pour l'instant** :
- ❌ Génération d'images **désactivée** (Imagen non accessible)
- ✅ L'application fonctionne normalement sans images

**Pour activer** :
1. Choisir DALL-E (recommandé) ou Replicate
2. Suivre les étapes d'intégration ci-dessus
3. Configurer la clé API
4. Décommenter les appels dans app.py et article_generator.py

**Recommandation** : DALL-E 3 pour la qualité et simplicité ! 🎨
