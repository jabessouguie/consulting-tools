"""
Test rapide de l'agent de commentaires LinkedIn
"""
import sys
from agents.linkedin_commenter import LinkedInCommenterAgent

# Post LinkedIn d'exemple
sample_post = """
L'IA générative va révolutionner le travail des data scientists.

Après 6 mois à intégrer ChatGPT et Claude dans nos workflows chez différents clients,
voici ce qu'on observe :

✅ Gain de temps massif sur le code répétitif (SQL, data cleaning, viz)
✅ Génération de premières analyses plus rapide
✅ Meilleure documentation automatique

MAIS :
❌ L'interprétation métier reste 100% humaine
❌ La validation des résultats critique
❌ Le choix des bonnes questions idem

L'IA est un super accélérateur. Pas un remplacement.

Les data scientists qui l'utilisent vont écraser ceux qui résistent.
Mais ceux qui comptent uniquement sur elle vont se planter.

Vous l'utilisez comment dans vos équipes data ?

#DataScience #IA #GenAI
"""

def main():
    print("\n" + "="*60)
    print("TEST - Agent de Commentaires LinkedIn")
    print("="*60 + "\n")

    agent = LinkedInCommenterAgent()

    print("📝 Post d'exemple :")
    print("-" * 60)
    print(sample_post)
    print("-" * 60 + "\n")

    # Test avec différents styles
    styles = ["insightful", "question", "experience"]

    for style in styles:
        print(f"\n🎨 Style : {style.upper()}")
        print("-" * 60)

        result = agent.run(post_input=sample_post, style=style)

        print(f"\n💬 Commentaire COURT ({len(result['short'])} caractères) :")
        print(result['short'])

        print(f"\n💬 Commentaire MOYEN ({len(result['medium'])} caractères) :")
        print(result['medium'])

        print(f"\n💬 Commentaire LONG ({len(result['long'])} caractères) :")
        print(result['long'])

        print(f"\n✅ Sauvegardé : {result['md_path']}")
        print("="*60)

if __name__ == '__main__':
    main()
