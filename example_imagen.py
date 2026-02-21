#!/usr/bin/env python3
"""
Exemple d'utilisation de Imagen 3 (Nano Banana Pro) avec google-genai SDK
"""
import os
from google import genai

def generer_image(prompt_texte: str, fichier_sortie: str = "output.jpg"):
    """
    Genere une image avec Imagen 3 via l'API Gemini

    Args:
        prompt_texte: Description de l'image a generer
        fichier_sortie: Chemin du fichier de sortie

    Returns:
        Chemin du fichier genere ou None si echec
    """
    # Le client recupere automatiquement la variable d'environnement GEMINI_API_KEY
    client = genai.Client()

    print(f"Generation de l'image en cours : '{prompt_texte}'...")

    try:
        # Appel a l'API de generation d'images
        result = client.models.generate_images(
            model='imagen-3.0-generate-001',  # Modele d'image officiel via l'API Gemini
            prompt=prompt_texte,
            config=dict(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9"  # Options: "1:1", "16:9", "9:16", "4:3", "3:4"
            )
        )

        # Sauvegarder l'image generee
        if result.generated_images and len(result.generated_images) > 0:
            # Creer le dossier de sortie si necessaire
            os.makedirs(os.path.dirname(fichier_sortie) or '.', exist_ok=True)

            # Ecrire les donnees de l'image
            image_data = result.generated_images[0].image.image_bytes
            with open(fichier_sortie, 'wb') as f:
                f.write(image_data)

            print(f"✅ Image generee avec succes: {fichier_sortie}")
            print(f"   Taille: {len(image_data) / 1024:.1f} KB")
            return fichier_sortie
        else:
            print("❌ Aucune image generee")
            return None

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


if __name__ == "__main__":
    # Exemple 1: Image simple
    generer_image(
        prompt_texte="A futuristic city with flying cars at sunset",
        fichier_sortie="output/images/futuristic_city.jpg"
    )

    # Exemple 2: Illustration business
    generer_image(
        prompt_texte="""A premium, cinematic illustration of a modern tech consultant
        orchestrating AI and data flows. Unreal Engine 5 style, isometric view,
        8k resolution. Dramatic lighting with cool electric blues and warm amber/gold.
        Professional and sophisticated.""",
        fichier_sortie="output/images/consultant_ai.jpg"
    )

    # Exemple 3: Data visualization concept
    generer_image(
        prompt_texte="""Abstract representation of data transformation pipeline.
        Geometric shapes, flowing data streams, purple and cyan gradients.
        Modern, clean, tech aesthetic. Corporate presentation style.""",
        fichier_sortie="output/images/data_pipeline.jpg"
    )
