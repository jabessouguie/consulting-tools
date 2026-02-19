"""
Test rapide du mail de partage de compte rendu
"""
import sys
from agents.meeting_summarizer import MeetingSummarizerAgent

# Transcript d'exemple
sample_transcript = """
[Début de la réunion - 14h00]

Jean-Sébastien: Bonjour à tous. Aujourd'hui on va faire le point sur le projet de migration data chez TotalEnergies.

Sophie (Client): Oui, on a quelques points à clarifier sur le planning et les ressources.

Jean-Sébastien: Parfait. Donc premier point : où en est-on sur l'audit des systèmes existants ?

Marc (Tech Lead): On a terminé l'audit de 85% des sources. Il reste les bases Oracle legacy qui sont plus complexes que prévu.

Sophie: Combien de temps supplémentaire vous estimez ?

Marc: 2 semaines max.

Jean-Sébastien: Ok, donc on décale le kick-off de la phase 2 de 2 semaines. Sophie, ça vous va ?

Sophie: Oui, on préfère partir sur des bases solides.

Jean-Sébastien: Parfait. Deuxième point : la formation des équipes. On a besoin de confirmer les participants.

Sophie: On a identifié 12 personnes. Je t'envoie la liste demain.

Jean-Sébastien: Super. Et niveau budget ?

Sophie: On a validé l'enveloppe de 180K€. Le bon de commande sera signé cette semaine.

Jean-Sébastien: Excellent. Actions pour la suite :
- Marc, tu finalises l'audit d'ici 2 semaines
- Sophie, tu m'envoies la liste des participants demain
- Je prépare le plan de formation détaillé pour vendredi
- On refait un point dans 15 jours

Tout le monde est ok ?

Marc: Oui parfait.

Sophie: Ok pour moi.

[Fin de la réunion - 14h45]
"""

def main():
    print("\n" + "="*60)
    print("TEST - Génération de mail de compte rendu")
    print("="*60 + "\n")

    agent = MeetingSummarizerAgent()

    print("📝 Transcript d'exemple (extrait):")
    print("-" * 60)
    print(sample_transcript[:300] + "...")
    print("-" * 60 + "\n")

    result = agent.run(transcript=sample_transcript)

    print("\n" + "="*60)
    print("COMPTE RENDU GÉNÉRÉ")
    print("="*60 + "\n")
    print(result['minutes'])

    print("\n" + "="*60)
    print("MAIL DE PARTAGE")
    print("="*60 + "\n")
    print(result['email'])

    print(f"\n✅ Sauvegardé : {result['md_path']}")

if __name__ == '__main__':
    main()
