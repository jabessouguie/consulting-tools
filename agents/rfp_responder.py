"""
Agent de réponse aux RFP (Request for Proposal)
Analyse un RFP et génère une ébauche de réponse structurée
"""
import os
import sys
from typing import Dict, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient


class RFPResponderAgent:
    """Agent de génération de réponses aux appels d'offres"""

    def __init__(self):
        self.llm_client = LLMClient()

        self.consultant_info = {
            'name': os.getenv('CONSULTANT_NAME', 'Jean-Sébastien Abessouguie Bayiha'),
            'title': os.getenv('CONSULTANT_TITLE', 'Consultant en stratégie data et IA'),
            'company': os.getenv('COMPANY_NAME', 'Wenvision'),
        }

    def analyze_rfp(self, rfp_text: str) -> Dict[str, Any]:
        """
        Analyse un RFP pour extraire les éléments clés

        Args:
            rfp_text: Texte du RFP

        Returns:
            Analyse structurée
        """
        print("🔍 Analyse du RFP...")

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Tu analyses des appels d'offres pour préparer des réponses."""

        prompt = f"""Analyse cet appel d'offres et extrais les éléments clés:

{rfp_text[:4000]}

Fournis une analyse structurée en JSON avec:
- "client": Nom du client si mentionné
- "context": Contexte du projet en 2-3 phrases
- "key_requirements": Liste des 5-7 exigences principales
- "deliverables": Livrables attendus
- "constraints": Contraintes (budget, timing, technos imposées)
- "evaluation_criteria": Critères d'évaluation si mentionnés

Format JSON uniquement."""

        analysis_json = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500,
        )

        print("   ✅ RFP analysé")

        # Parser le JSON
        import json
        try:
            analysis = json.loads(analysis_json)
        except:
            # Fallback si le parsing échoue
            analysis = {
                "client": "Client non spécifié",
                "context": "Analyse à compléter",
                "key_requirements": [],
                "deliverables": [],
                "constraints": [],
                "evaluation_criteria": []
            }

        return analysis

    def generate_response(
        self,
        rfp_text: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Génère une ébauche de réponse au RFP

        Args:
            rfp_text: Texte du RFP
            analysis: Analyse structurée

        Returns:
            Réponse complète
        """
        print("✍️  Génération de la réponse...")

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Tu rédiges des réponses professionnelles à des appels d'offres."""

        prompt = f"""Rédige une ébauche de réponse à cet appel d'offres.

ANALYSE DU RFP:
Client: {analysis.get('client', 'N/A')}
Contexte: {analysis.get('context', 'N/A')}
Exigences clés: {', '.join(analysis.get('key_requirements', [])[:5])}
Livrables: {', '.join(analysis.get('deliverables', [])[:5])}

EXTRAIT DU RFP:
{rfp_text[:3000]}

---

La réponse doit contenir:

# 📋 Réponse à l'appel d'offres

## 1. Synthèse exécutive

[Résumé en 150-200 mots:
- Compréhension du besoin
- Notre proposition de valeur
- Pourquoi nous sommes le bon partenaire]

## 2. Compréhension du contexte et des enjeux

[Reformulation du besoin montrant notre compréhension:
- Contexte business
- Enjeux stratégiques identifiés
- Risques et opportunités]

## 3. Notre approche

### 3.1 Méthodologie

[Description de notre approche:
- Cadre méthodologique (Agile, Design Thinking, etc.)
- Phases du projet
- Gouvernance proposée]

### 3.2 Plan de travail détaillé

[Planning macro avec phases:
- Phase 1: Cadrage (X semaines)
- Phase 2: Développement (X semaines)
- Phase 3: Déploiement (X semaines)
- Phase 4: Accompagnement (X semaines)]

## 4. Livrables

[Liste détaillée des livrables avec:
- Description
- Format
- Jalons de validation]

## 5. Équipe et compétences

[Composition de l'équipe projet:
- Profils clés
- Expériences pertinentes
- Rôles et responsabilités]

## 6. Références et expériences similaires

[2-3 projets similaires avec:
- Client (si possible de mentionner)
- Contexte
- Résultats obtenus]

## 7. Planning et jalons

[Gantt textuel ou tableau des jalons avec dates]

## 8. Estimation budgétaire

[Décomposition indicative:
- Phase X: [budget range]
- Phase Y: [budget range]
- Options additionnelles]

## 9. Conditions et modalités

[Conditions contractuelles:
- Durée d'engagement
- Modalités de facturation
- Propriété intellectuelle
- Garanties]

## 10. Points de différenciation

[Ce qui nous distingue:
- Expertise spécifique
- Innovation proposée
- Flexibilité et agilité
- Support et accompagnement]

---

**IMPORTANT:**
- Remplace [placeholder] par du contenu concret basé sur le RFP
- Adapte le niveau de détail aux exigences
- Reste professionnel et factuel
- Si info manquante, indique [À COMPLÉTER: raison]

Ton : professionnel, confiant mais pas arrogant."""

        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4000,
        )

        print("   ✅ Réponse générée")

        return {
            'response': response,
            'analysis': analysis,
            'generated_at': datetime.now().isoformat(),
        }

    def run(self, rfp_text: str) -> Dict[str, Any]:
        """
        Pipeline complet: analyse -> réponse

        Args:
            rfp_text: Texte du RFP

        Returns:
            Résultat complet
        """
        print(f"\n{'='*50}")
        print("📋 RÉPONSE À APPEL D'OFFRES")
        print(f"{'='*50}\n")

        analysis = self.analyze_rfp(rfp_text)
        result = self.generate_response(rfp_text, analysis)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, f"rfp_response_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Réponse à l'appel d'offres\n\n")
            f.write(f"**Généré le:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write("---\n\n")
            f.write(result['response'])

        result['md_path'] = md_path

        print(f"\n✅ Réponse sauvegardée: {md_path}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Génération de réponse à RFP')
    parser.add_argument('rfp_file', help='Fichier contenant le RFP (.txt ou .md)')

    args = parser.parse_args()

    if not os.path.exists(args.rfp_file):
        print(f"❌ Fichier introuvable: {args.rfp_file}")
        return

    with open(args.rfp_file, 'r', encoding='utf-8') as f:
        rfp_text = f.read()

    agent = RFPResponderAgent()
    result = agent.run(rfp_text=rfp_text)

    print(f"\n{'='*50}")
    print("RÉPONSE GÉNÉRÉE")
    print(f"{'='*50}\n")
    print(result['response'][:1000] + "...")


if __name__ == '__main__':
    main()
