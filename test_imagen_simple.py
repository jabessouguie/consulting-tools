#!/usr/bin/env python3
"""
Test simple de Nano Banana Pro sans imports complexes
"""
import os
import sys
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(__file__))

# Charger .env manuellement
with open(".env", "r") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
            break

# Importer et tester
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY non configurée")
    sys.exit(1)

print("=" * 70)
print("TEST NANO BANANA PRO")
print("=" * 70)
print(f"✅ API Key: {api_key[:20]}...\n")

# Configurer l'API
genai.configure(api_key=api_key)

# Tester Nano Banana Pro
model_name = "models/nano-banana-pro-preview"
prompt = """A premium, cinematic illustration of a modern tech consultant
orchestrating AI and data flows. Unreal Engine 5 style, isometric view,
8k resolution. Dramatic lighting with cool electric blues and warm amber/gold.
Professional and sophisticated."""

print(f"Modèle: {model_name}")
print(f"Prompt: {prompt[:80]}...\n")
print("Génération en cours...\n")

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    print("✅ Réponse reçue!")
    print(f"   Parts: {len(response.parts) if response.parts else 0}")

    # Chercher des données d'image
    if response.parts:
        for i, part in enumerate(response.parts):
            print(f"   Part {i}: {type(part).__name__}")
            if hasattr(part, "inline_data") and part.inline_data:
                print(f"   ✅ Image trouvée! Type: {part.inline_data.mime_type}")
                print(f"   Taille: {len(part.inline_data.data) / 1024:.1f} KB")

                # Sauvegarder
                output_path = "output/images/test_nano_banana.jpg"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"   ✅ Image sauvegardée: {output_path}")
            elif hasattr(part, "text"):
                print(f"   Texte: {part.text[:100]}...")
    else:
        print("   ⚠️  Aucun part dans la réponse")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
