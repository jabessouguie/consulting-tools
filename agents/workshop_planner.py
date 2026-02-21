"""
Agent de préparation de workshops/formations
Génère un plan pédagogique complet à partir d'un sujet et d'objectifs
"""
import os
import sys
from typing import Dict, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient
from config import get_consultant_info


class WorkshopPlannerAgent:
    """Agent de création de plans de formation pour consultants"""

    def __init__(self):
        self.llm_client = LLMClient()

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()

    def generate_workshop_plan(
        self,
        topic: str,
        duration: str,
        audience: str,
        objectives: str
    ) -> Dict[str, Any]:
        """
        Génère un plan de workshop complet

        Args:
            topic: Sujet du workshop (ex: "Introduction au Machine Learning")
            duration: Durée ("half_day", "full_day", "two_days")
            audience: Public cible (ex: "Managers non-techniques", "Data analysts juniors")
            objectives: Objectifs pédagogiques

        Returns:
            Plan complet
        """
        print(f"📚 Génération du plan de workshop: {topic}")

        duration_labels = {
            "half_day": "Demi-journée (3h30)",
            "full_day": "Journée complète (7h)",
            "two_days": "2 jours (14h)"
        }
        duration_label = duration_labels.get(duration, duration)

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Tu conçois des formations et workshops professionnels en data/IA."""

        prompt = f"""Conçois un plan de formation/workshop complet pour:

**SUJET:** {topic}

**DURÉE:** {duration_label}

**PUBLIC:** {audience}

**OBJECTIFS PÉDAGOGIQUES:**
{objectives}

---

Le plan doit contenir:

# 📚 Plan de Formation - {topic}

## 🎯 Vue d'ensemble

**Durée:** {duration_label}
**Public:** {audience}
**Format:** [Présentiel/Hybride recommandé]

**Objectifs:**
- [Liste des objectifs pédagogiques]

**Prérequis:**
- [Connaissances nécessaires si applicable]

## 📋 Programme détaillé

[Programme heure par heure avec:
- Timings précis (ex: 09h00-10h30)
- Titres de modules
- Format (théorie/pratique/exercice)
- Durées de pause]

### Module 1 : [Titre]
**Durée:** [XX min]
**Format:** Théorie + Démo

**Contenu:**
- Point 1
- Point 2
- Point 3

**Livrables:** [Ce que les participants auront appris/produit]

[Répéter pour chaque module...]

## 💻 Exercices pratiques

[Description de 2-4 exercices concrets avec:
- Objectif de l'exercice
- Durée
- Matériel nécessaire
- Livrables attendus]

## 🎨 Structure des slides

[Outline des slides par section:
- Slide 1-5 : Introduction
- Slide 6-15 : Module 1
- etc.]

## 📦 Matériel nécessaire

**Technique:**
- [Hardware/Software requis]

**Pédagogique:**
- [Supports, datasets, outils]

**Logistique:**
- [Salle, équipements]

## ✅ Évaluation

[Comment mesurer l'atteinte des objectifs:
- Quiz
- Exercice final
- Feedback à chaud]

## 📝 Notes pour le formateur

[Conseils pratiques:
- Points d'attention
- Pièges à éviter
- Temps forts]

Ton : professionnel et pédagogique. Sois concret et actionnable."""

        plan = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=3500,
        )

        print("   ✅ Plan généré")

        return {
            'plan': plan,
            'topic': topic,
            'duration': duration_label,
            'audience': audience,
            'generated_at': datetime.now().isoformat(),
        }

    def run(
        self,
        topic: str,
        duration: str = "full_day",
        audience: str = "Professionnels",
        objectives: str = ""
    ) -> Dict[str, Any]:
        """
        Pipeline complet

        Args:
            topic: Sujet
            duration: Durée
            audience: Public
            objectives: Objectifs

        Returns:
            Résultat complet
        """
        print(f"\n{'='*50}")
        print("📚 PLANIFICATION DE WORKSHOP")
        print(f"{'='*50}\n")

        result = self.generate_workshop_plan(topic, duration, audience, objectives)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Nettoyer le nom du fichier
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        safe_topic = safe_topic.replace(' ', '_')

        md_path = os.path.join(output_dir, f"workshop_{safe_topic}_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result['plan'])

        result['md_path'] = md_path

        print(f"\n✅ Plan sauvegardé: {md_path}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Planification de workshop')
    parser.add_argument('topic', help='Sujet du workshop')
    parser.add_argument('--duration', choices=['half_day', 'full_day', 'two_days'], default='full_day')
    parser.add_argument('--audience', default='Professionnels')
    parser.add_argument('--objectives', default='')

    args = parser.parse_args()

    agent = WorkshopPlannerAgent()
    result = agent.run(
        topic=args.topic,
        duration=args.duration,
        audience=args.audience,
        objectives=args.objectives
    )

    print(f"\n{'='*50}")
    print("PLAN GÉNÉRÉ")
    print(f"{'='*50}\n")
    print(result['plan'][:1000] + "...")


if __name__ == '__main__':
    main()
