#!/usr/bin/env python3
"""
Liste tous les modeles disponibles via google-genai SDK
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai

    client = genai.Client()

    print("=" * 80)
    print("MODELES DISPONIBLES via google-genai SDK")
    print("=" * 80)

    models = client.models.list()

    image_models = []
    text_models = []

    for model in models:
        model_name = model.name
        capabilities = getattr(model, 'supported_generation_methods', [])

        # Filtrer les modeles d'images
        if 'imagen' in model_name.lower() or 'image' in str(capabilities).lower():
            image_models.append((model_name, capabilities))
        else:
            text_models.append((model_name, capabilities))

    if image_models:
        print("\n📸 MODELES D'IMAGES:")
        print("-" * 80)
        for name, caps in image_models:
            print(f"  ✅ {name}")
            if caps:
                print(f"     Capabilities: {caps}")
    else:
        print("\n⚠️  Aucun modele d'image trouve")

    print("\n💬 MODELES DE TEXTE (selection):")
    print("-" * 80)
    for name, caps in text_models[:10]:  # Afficher les 10 premiers
        print(f"  • {name}")

    if len(text_models) > 10:
        print(f"  ... et {len(text_models) - 10} autres modeles")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
