#!/usr/bin/env python3
"""
Script de test pour Imagen 3 (Nano Banana Pro) via google-genai SDK
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def test_imagen():
    """Test de generation d'image avec Imagen 3"""
    print("=" * 60)
    print("Test Imagen 3 (Nano Banana Pro) via google-genai SDK")
    print("=" * 60)

    # Verifier les variables d'environnement
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY: NON DEFINIE")
        print("\n⚠️  Configurez GEMINI_API_KEY dans votre fichier .env")
        print("   Obtenez une cle sur: https://aistudio.google.com/apikey")
        return
    else:
        print(f"✅ GEMINI_API_KEY: {api_key[:20]}...")

    # Tester la generation d'image
    print("\n" + "=" * 60)
    print("Generation d'une image de test...")
    print("=" * 60)

    try:
        from utils.image_generator import NanoBananaGenerator

        generator = NanoBananaGenerator()

        prompt = """A premium, cinematic illustration of a modern tech consultant
        orchestrating AI and data flows. Unreal Engine 5 style, isometric view,
        8k resolution. Dramatic lighting with cool electric blues and warm amber/gold.
        Professional and sophisticated."""

        output_path = "output/images/test_imagen.jpg"

        result = generator.generate_image(prompt, output_path)

        if result:
            print(f"\n✅ Image generee avec succes: {result}")
            print(f"   Taille: {Path(result).stat().st_size / 1024:.1f} KB")
        else:
            print("\n❌ Echec de la generation")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imagen()
