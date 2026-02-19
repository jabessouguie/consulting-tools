"""
Agent de synthèse de réunion
Analyse un transcript de réunion et génère un compte rendu structuré + email de partage
"""
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from utils.llm_client import LLMClient


class MeetingSummarizerAgent:
    """Agent pour générer des comptes rendus de réunion"""

    def __init__(self):
        """Initialise l'agent"""
        self.llm = LLMClient(max_tokens=4096)
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def extract_key_info(self, transcript: str) -> Dict[str, Any]:
        """
        Extrait les informations clés du transcript de réunion

        Args:
            transcript: Transcript de la réunion

        Returns:
            Dictionnaire avec les informations extraites
        """
        print("📊 Extraction des informations clés...")

        system_prompt = """Tu es un assistant expert en analyse de réunions.
Tu dois extraire les informations structurées d'un transcript de réunion."""

        prompt = f"""Analyse ce transcript de réunion et extrais les informations clés :

{transcript}

Extrais et structure les éléments suivants :
1. Date et heure de la réunion (si mentionnée)
2. Participants (noms et rôles si mentionnés)
3. Objectif principal de la réunion
4. Décisions prises (liste précise)
5. Actions à mener (qui fait quoi, avec échéances si mentionnées)
6. Points en suspens ou questions non résolues
7. Prochaines étapes

Retourne les informations en format structuré et clair."""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )

        return {"extracted_info": response}

    def generate_minutes(self, transcript: str, extracted_info: str) -> str:
        """
        Génère un compte rendu structuré de la réunion

        Args:
            transcript: Transcript original
            extracted_info: Informations extraites

        Returns:
            Compte rendu au format markdown
        """
        print("  [2/3] Generation du compte rendu...")

        consultant_name = os.getenv('CONSULTANT_NAME', 'Jean-Sebastien Abessouguie Bayiha')
        company_name = os.getenv('COMPANY_NAME', 'Wenvision')

        system_prompt = f"""Tu es un assistant de {consultant_name}, consultant en strategie data et IA chez {company_name}.
Tu transformes des transcripts bruts de reunions en comptes rendus structures, professionnels et synthetiques.

Objectif du compte rendu :
- Resumer les echanges de maniere concise et organisee.
- Mettre en avant les decisions prises, les actions a mener et les prochaines etapes.
- Etre facile a lire pour le client, avec des sections claires et des points d'action identifiables.
- Conserver un ton neutre et professionnel, sans jargon inutile.

Regles de transformation :
- Supprimer les redondances et les echanges informels (ex: "Oui, tout a fait", "Je suis d'accord").
- Reformuler les idees pour qu'elles soient claires et directes. Eviter les phrases trop longues.
- Extraire les decisions et actions: Identifier les phrases comme "On va faire X", "[Nom] s'occupe de Y".
- Organiser par themes: Regrouper les echanges par sujet.
- Mettre en evidence les echeances et responsables pour chaque action.
- Conserver les questions ouvertes dans une section dediee.

Ton et style :
- Neutre et professionnel: Pas de familiarite, utiliser "nous" pour designer le groupe.
- Precis et concis: Aller a l'essentiel sans perdre le sens.
- Visuel et aere: Utiliser des puces, des sauts de ligne et des titres pour faciliter la lecture."""

        prompt = f"""A partir de ces informations, redige un compte rendu de reunion complet et professionnel :

INFORMATIONS EXTRAITES :
{extracted_info}

TRANSCRIPT COMPLET (pour contexte) :
{transcript[:5000]}

Genere un compte rendu au format Markdown avec cette structure EXACTE :

# Compte rendu - Reunion [Nom du projet ou sujet] - [Date]

## 1. En-tete
- **Objet** : Compte rendu - Reunion [Nom du projet ou sujet] - [Date]
- **Participants** : [Liste des participants (noms, roles, organisations)]
- **Date et duree** : [Date], [Heure debut] - [Heure fin]

## 2. Objectifs de la reunion
La reunion avait pour but de :
- [Objectif 1]
- [Objectif 2]

## 3. Points cles discutes

### 3.1. [Sujet 1]
- [Resume en 2-3 lignes des echanges]
    - [Sous-point ou detail important]
    - [Question ouverte ou point non resolu]

### 3.2. [Sujet 2]
- [Resume]

## 4. Decisions prises
Les decisions suivantes ont ete actees :
1. **[Decision 1]** : [Description claire et concise]
2. **[Decision 2]** : [Description]

## 5. Actions et responsables
| Action | Responsable | Echeance |
|--------|-------------|----------|
| [Action 1] | [Nom] | [Date] |
| [Action 2] | [Nom] | [Date] |

## 6. Prochaines etapes
- **[Etape 1]** : [Description] - Date prevue : [Date]
- **[Etape 2]** : [Description] - Date prevue : [Date]

## 7. Annexes
Documents ou liens partages pendant la reunion :
- [Lien/Document 1] : [Description]

## 8. Cloture
Pour toute question ou precision, n'hesitez pas a me contacter.
Cordialement, {consultant_name} - {company_name}

---
*Compte rendu genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')} par {consultant_name} - {company_name}*"""

        minutes = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )

        return minutes

    def generate_email(self, extracted_info: str, minutes: str) -> Dict[str, str]:
        """
        Génère un email de partage du compte rendu

        Args:
            extracted_info: Informations extraites
            minutes: Compte rendu complet

        Returns:
            Dictionnaire avec subject et body
        """
        print("📧 Génération de l'email de partage...")

        consultant_name = os.getenv('CONSULTANT_NAME', 'Jean-Sébastien Abessouguie Bayiha')

        system_prompt = f"""Tu es {consultant_name}, tu rédiges un email professionnel pour partager un compte rendu de réunion."""

        prompt = f"""Génère un email de partage pour ce compte rendu de réunion :

INFORMATIONS EXTRAITES :
{extracted_info}

COMPTE RENDU :
{minutes[:1500]}

L'email doit contenir :
1. Un objet clair et professionnel
2. Un corps structuré avec :
   - Formule d'introduction courtoise
   - Résumé exécutif (3-5 lignes max)
   - Décisions clés (2-3 points)
   - Actions prioritaires (2-3 points)
   - Mention que le compte rendu complet est en pièce jointe
   - Indication de la prochaine réunion si mentionnée
   - Formule de politesse professionnelle

Ton : Professionnel, courtois, concis

Format de sortie :
OBJET: [objet de l'email]

CORPS:
[corps de l'email]"""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )

        # Parser la réponse pour extraire objet et corps
        lines = response.strip().split('\n')
        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            if line.startswith('OBJET:'):
                subject = line.replace('OBJET:', '').strip()
            elif line.startswith('CORPS:'):
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()

        if not subject:
            subject = "Compte rendu de réunion"
        if not body:
            body = response

        return {
            "subject": subject,
            "body": body
        }

    def run(self, transcript: str) -> Dict[str, Any]:
        """
        Pipeline complet : analyse le transcript et génère compte rendu + email

        Args:
            transcript: Transcript de la réunion

        Returns:
            Dictionnaire avec minutes, email, et métadonnées
        """
        print("\n🎙️  ANALYSE DE REUNION\n")

        # Extraction des informations
        extracted = self.extract_key_info(transcript)
        extracted_info = extracted["extracted_info"]

        # Génération du compte rendu
        minutes = self.generate_minutes(transcript, extracted_info)

        # Génération de l'email
        email = self.generate_email(extracted_info, minutes)

        # Sauvegarde
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        minutes_path = output_dir / f"meeting_minutes_{timestamp}.md"

        with open(minutes_path, 'w', encoding='utf-8') as f:
            f.write(minutes)

        print(f"\n✅ Compte rendu sauvegardé : {minutes_path.relative_to(self.base_dir)}")

        return {
            "minutes": minutes,
            "email": email,
            "minutes_path": str(minutes_path.relative_to(self.base_dir)),
            "generated_at": datetime.now().isoformat()
        }
