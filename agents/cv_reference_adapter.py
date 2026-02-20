"""
Agent d adaptation de CV et references projets
Adapte un CV ou une reference a un appel d offre specifique
Genere des slides de presentation au format JSON
"""
import os
import sys
import json
from typing import Dict, Any, List
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient


class CVReferenceAdapterAgent:
    """Agent pour adapter des CV et references aux appels d offre - genere des slides"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)
        self.consultant_info = {
            'name': os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha'),
            'company': os.getenv('COMPANY_NAME', 'WEnvision')
        }

    def adapt_cv(self, cv_text: str, mission_brief: str) -> List[Dict]:
        """Adapte un CV au besoin d une mission - retourne des slides JSON"""

        system_prompt = f"""Tu es {self.consultant_info['name']}, consultant chez {self.consultant_info['company']}.

TON ROLE : Adapter un CV existant pour repondre precisement aux besoins d un appel d offre.
Tu dois generer UNE SEULE SLIDE CV qui contient TOUTES les informations condensees.

CHARTE GRAPHIQUE WENVISION :
- Palette : Rose Poudre (60%), Noir/Gris (30%), Corail/Terracotta (10%)
- Typographie : Chakra Petch (titres), Inter (texte)
- Style : Professionnel, moderne, epure

FORMAT SLIDE CV (UNE SEULE SLIDE) :

{{"type": "cv",
 "name": "[Nom complet du consultant]",
 "title": "[Titre professionnel adapte a la mission]",
 "photo": "placeholder",
 "profile": "[Synthese 2-3 lignes ultra pertinente pour la mission]",
 "skills": ["Competence 1", "Competence 2", "Competence 3", "Competence 4"],
 "experiences": [
   {{"role": "[Poste/Projet court]", "company": "[Client]", "period": "[Annee]", "description": "[1 ligne percutante alignee avec mission]"}},
   {{"role": "[Poste/Projet court]", "company": "[Client]", "period": "[Annee]", "description": "[1 ligne percutante alignee avec mission]"}},
   {{"role": "[Poste/Projet court]", "company": "[Client]", "period": "[Annee]", "description": "[1 ligne percutante alignee avec mission]"}}
 ]
}}

REGLES STRICTES :
- JSON valide OBLIGATOIRE
- UNE SEULE SLIDE (pas de cover, pas de closing, juste le CV)
- Le champ "photo": "placeholder" pour inserer la photo du consultant
- Skills : 4-5 competences MAX, ultra pertinentes pour la mission
- Experiences : 3-4 experiences MAX, format ULTRA CONDENSE (1 ligne par experience)
- Profile : 2-3 lignes MAX, focus sur adequation avec la mission
- Chiffres concrets quand possible dans descriptions
- Ton : professionnel, pragmatique, oriente resultats"""

        prompt = f"""DOCUMENT SOURCE (CV) :
---
{cv_text}
---

MISSION / APPEL D OFFRE CIBLE :
---
{mission_brief}
---

Genere UNE SEULE SLIDE CV professionnelle qui adapte ce CV a la mission.

OBJECTIF : Maximiser la pertinence percue en reformulant et selectionnant
les informations qui creent des resonances directes avec le besoin client.
Format ultra condense pour tenir dans UNE slide.

Retourne UNIQUEMENT un tableau JSON avec UNE seule slide, sans preambule ni explication.
Format : [slide_cv_unique]"""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Parser JSON
        result = result.strip()
        if result.startswith('```json'):
            result = result[len('```json'):]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]

        return json.loads(result.strip())

    def adapt_reference(self, reference_text: str, mission_brief: str) -> List[Dict]:
        """Adapte une reference projet au besoin client - retourne des slides JSON"""

        system_prompt = f"""Tu es {self.consultant_info['name']}, consultant chez {self.consultant_info['company']}.

TON ROLE : Adapter une reference projet existante pour repondre precisement aux besoins d un appel d offre.
Tu dois generer une PRESENTATION (slides JSON) qui met en valeur la reference adaptee.

CHARTE GRAPHIQUE WENVISION :
- Palette : Rose Poudre (60%), Noir/Gris (30%), Corail/Terracotta (10%)
- Typographie : Chakra Petch (titres), Inter (texte)
- Style : Professionnel, moderne, epure

STRUCTURE DES SLIDES :

1. Slide COVER
{{"type": "cover", "title": "Reference Mission : [Titre adapte]", "subtitle": "[Client] - [Annee]"}}

2. Slide CONTEXTE
{{"type": "content", "title": "Contexte Client", "bullets": ["Secteur : [...]", "Enjeux : [reformules pour creer paralleles avec mission cible]", "Contexte : [...]"]}}

3. Slide OBJECTIFS
{{"type": "highlight", "title": "Objectifs de la Mission", "bullets": ["Objectif 1 [align avec nouveau besoin]", "Objectif 2 [...]", "Objectif 3 [...]"]}}

4. Slide DEMARCHE
{{"type": "diagram", "title": "Demarche & Methodologie", "diagram_type": "timeline", "elements": ["Phase 1 : [...]", "Phase 2 : [...]", "Phase 3 : [...]"], "description": "Approche methodologique"}}

5. Slide RESULTATS
{{"type": "stat", "title": "Resultats & Impact", "stats": [{{"label": "ROI", "value": "[chiffre]"}}, {{"label": "Performance", "value": "[chiffre]"}}, {{"label": "Delais", "value": "[chiffre]"}}]}}

6. Slide SIMILITUDES
{{"type": "two_column", "title": "Similitudes avec votre besoin", "left": {{"title": "Mission realisee", "bullets": ["Point 1", "Point 2"]}}, "right": {{"title": "Votre besoin", "bullets": ["Parallele 1", "Parallele 2"]}}}}

7. Slide CLOSING
{{"type": "closing", "title": "Contact", "content": "Reference disponible sur demande"}}

REGLES :
- JSON valide OBLIGATOIRE
- Reformule pour creer resonances avec mission cible
- Chiffres concrets obligatoires (ROI, KPIs, delais)
- Ton : professionnel, pragmatique, oriente resultats"""

        prompt = f"""DOCUMENT SOURCE (REFERENCE) :
---
{reference_text}
---

MISSION / APPEL D OFFRE CIBLE :
---
{mission_brief}
---

Genere une presentation professionnelle (slides JSON) qui adapte cette reference a la mission.

OBJECTIF : Maximiser la pertinence percue en reformulant et selectionnant
les informations qui creent des resonances directes avec le besoin client.

Retourne UNIQUEMENT le tableau JSON des slides, sans preambule ni explication.
Format : [slide1, slide2, ...]"""

        result = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.7)

        # Parser JSON
        result = result.strip()
        if result.startswith('```json'):
            result = result[len('```json'):]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]

        return json.loads(result.strip())

    def run(self, document_text: str, mission_brief: str, doc_type: str = "auto") -> Dict[str, Any]:
        """Point d entree principal - retourne des slides"""

        # Auto-detection si doc_type = "auto"
        if doc_type == "auto":
            is_cv = any(kw in document_text.lower() for kw in [
                'experience', 'competences', 'formation', 'cv', 'consultant',
                'diplome', 'certification', 'parcours professionnel'
            ])
            doc_type = "CV" if is_cv else "Reference"

        print(f"\n  ADAPTATION DE {doc_type.upper()}")
        print(f"  Mission : {mission_brief[:100]}...")

        # Adaptation selon le type - retourne slides JSON
        if doc_type.upper() == "CV":
            slides = self.adapt_cv(document_text, mission_brief)
        else:
            slides = self.adapt_reference(document_text, mission_brief)

        print(f"  {len(slides)} slides generees")

        return {
            "slides": slides,
            "doc_type": doc_type,
            "mission_brief": mission_brief
        }


if __name__ == "__main__":
    agent = CVReferenceAdapterAgent()

    # Test CV
    test_cv = """Jean-Sebastien ABESSOUGUIE
Consultant Data & IA

Experience :
- 2020-2024 : Consultant senior chez WEnvision
  Missions de transformation data et IA
  Accompagnement de grands comptes

Competences : Python, Machine Learning, Cloud, Data Governance"""

    test_mission = """Recherche consultant pour mission gouvernance des donnees
Client : Grande banque francaise
Duree : 6 mois
Competences : Data Governance, RGPD, Azure"""

    result = agent.run(test_cv, test_mission, doc_type="auto")
    print("\n=== SLIDES GENEREES ===")
    print(f"Type : {result['doc_type']}")
    print(f"Nombre de slides : {len(result['slides'])}")
    for i, slide in enumerate(result['slides'], 1):
        print(f"  Slide {i}: {slide.get('type', 'unknown')} - {slide.get('title', 'N/A')}")
