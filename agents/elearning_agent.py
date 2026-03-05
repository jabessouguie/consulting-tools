"""
Agent E-learning Adaptatif par IA
Generation de cours, quiz adaptatifs et parcours personnalises
"""

import json
import re
from typing import Any, Dict, List, Optional

from utils.llm_client import LLMClient


class ElearningAgent:
    """Agent pour la generation de contenu e-learning adaptatif"""

    # Modes specialises pour consultants
    MODES = {
        "free": {
            "label": "Cours libre",
            "system_context": "",
            "outline_rules": "",
            "lesson_rules": "",
            "quiz_rules": "",
        },
        "interview": {
            "label": "Preparation entretien",
            "system_context": (
                "Le consultant se prepare pour un entretien "
                "technique ou de recrutement. Le cours doit "
                "couvrir les questions frequentes, les mises en "
                "situation, les pieges classiques et les bonnes "
                "pratiques pour repondre."
            ),
            "outline_rules": (
                "- Inclure un module sur les questions techniques "
                "frequentes et les reponses attendues\n"
                "- Inclure un module sur les questions "
                "comportementales (STAR method)\n"
                "- Inclure des exercices de simulation "
                "d'entretien\n"
                "- Ajouter un module sur la presentation du "
                "parcours professionnel\n"
                "- Prevoir des cas pratiques/etudes de cas"
            ),
            "lesson_rules": (
                "- Chaque lecon doit contenir des exemples de "
                "questions et reponses modeles\n"
                "- Inclure des exercices de mise en situation\n"
                "- Ajouter des conseils pratiques (posture, "
                "formulation, erreurs a eviter)\n"
                "- Proposer des scripts de reponse adaptables"
            ),
            "quiz_rules": (
                "- Formuler les questions comme dans un vrai "
                "entretien technique\n"
                "- Inclure des mises en situation (que repondez-"
                "vous si...)\n"
                "- Tester la capacite a structurer une reponse\n"
                "- Evaluer la connaissance des concepts cles"
            ),
        },
        "certification": {
            "label": "Preparation certification",
            "system_context": (
                "Le consultant se prepare a obtenir une "
                "certification professionnelle. L'unique objectif "
                "est qu'il reussisse l'examen. Le cours doit "
                "couvrir exhaustivement le programme officiel, "
                "les points cles a memoriser, les pieges "
                "recurrents aux examens et les strategies pour "
                "maximiser son score. Ignore le public cible: "
                "le seul apprenant est le consultant lui-meme."
            ),
            "outline_rules": (
                "- Suivre le syllabus officiel de la "
                "certification si connu\n"
                "- Inclure un module de revision rapide "
                "(fiches memo)\n"
                "- Prevoir des examens blancs complets\n"
                "- Insister sur les points frequemment testes\n"
                "- Couvrir les pieges classiques des examens\n"
                "- Ajouter un module de strategie d'examen "
                "(gestion du temps, elimination, scoring)"
            ),
            "lesson_rules": (
                "- Structurer chaque lecon autour des objectifs "
                "de l'examen\n"
                "- Ajouter des encadres 'A retenir' avec les "
                "concepts cles a memoriser\n"
                "- Inclure des exemples de questions d'examen "
                "reelles ou realistes\n"
                "- Fournir des mnemoniques et astuces de "
                "memorisation\n"
                "- Differencier les notions 'a connaitre par "
                "coeur' vs 'a comprendre en profondeur'\n"
                "- Pour chaque concept, indiquer la probabilite "
                "de le retrouver a l'examen (frequence haute/"
                "moyenne/basse)"
            ),
            "quiz_rules": (
                "- Utiliser le format exact de l'examen de "
                "certification (majoritairement QCM)\n"
                "- 60-70%% de QCM, 20%% vrai/faux, 10%% "
                "questions ouvertes\n"
                "- Inclure des questions a elimination "
                "(2 reponses plausibles)\n"
                "- Simuler la pression temps de l'examen reel\n"
                "- Expliquer pourquoi chaque mauvaise reponse "
                "est incorrecte\n"
                "- Indiquer le score minimum requis pour "
                "reussir la certification"
            ),
        },
        "training": {
            "label": "Preparation formation",
            "system_context": (
                "Le consultant se prepare a donner une "
                "formation ou un atelier sur ce sujet. "
                "L'objectif principal est qu'il maitrise "
                "parfaitement les concepts cles et soit "
                "capable de repondre a toutes les questions "
                "que les participants pourraient poser. "
                "Le cours doit approfondir chaque concept "
                "pour que le formateur ait une comprehension "
                "complete, au-dela du surface level."
            ),
            "outline_rules": (
                "- Chaque module doit approfondir les concepts "
                "cles pour une maitrise complete\n"
                "- Inclure un module FAQ avec les questions "
                "difficiles que les participants posent "
                "frequemment et les reponses detaillees\n"
                "- Prevoir les objections et incomprehensions "
                "courantes avec comment y repondre\n"
                "- Structurer du fondamental vers l'avance "
                "pour une maitrise progressive\n"
                "- Inclure des cas limites et subtilites que "
                "les participants curieux pourraient soulever"
            ),
            "lesson_rules": (
                "- Chaque lecon doit approfondir le 'pourquoi' "
                "derriere chaque concept, pas juste le 'quoi'\n"
                "- Ajouter une section 'Questions anticipees "
                "des participants' avec reponses detaillees\n"
                "- Inclure les erreurs et confusions frequentes "
                "des apprenants et comment les corriger\n"
                "- Proposer des analogies et metaphores claires "
                "pour expliquer les concepts complexes\n"
                "- Fournir des exemples concrets et cas "
                "pratiques pour illustrer chaque notion\n"
                "- Indiquer les liens entre concepts pour "
                "repondre aux questions transversales"
            ),
            "quiz_rules": (
                "- Les questions testent la maitrise profonde "
                "des concepts, pas la memorisation\n"
                "- Inclure des questions du type 'comment "
                "expliqueriez-vous X a un debutant'\n"
                "- Tester la capacite a repondre aux questions "
                "pieges que les participants pourraient poser\n"
                "- Inclure des scenarios : 'un participant "
                "demande pourquoi X et pas Y, que repondez-"
                "vous ?'\n"
                "- Evaluer la comprehension des nuances et "
                "cas limites"
            ),
        },
    }

    def __init__(self):
        self.llm = LLMClient(max_tokens=8192)

    def _get_mode_config(self, mode: str) -> Dict:
        """Retourne la config du mode ou le mode libre"""
        return self.MODES.get(mode, self.MODES["free"])

    # ==================
    # COURSE GENERATION
    # ==================

    def generate_course(
        self,
        topic: str,
        target_audience: str,
        difficulty: str,
        duration_hours: int,
        progress_callback=None,
        mode: str = "free",
    ) -> Dict[str, Any]:
        """
        Genere un cours complet avec modules et lecons.

        Args:
            topic: Sujet du cours
            target_audience: Public cible
            difficulty: beginner, intermediate, advanced
            duration_hours: Duree en heures
            progress_callback: fn(step, detail) pour SSE
            mode: free, interview, certification, training

        Returns:
            Dict structure du cours complet
        """
        mode_cfg = self._get_mode_config(mode)
        if progress_callback:
            label = mode_cfg.get("label", "Cours")
            progress_callback(
                "outline",
                f"Generation du plan ({label})...",
            )

        # Step 1: Generate course outline
        outline = self._generate_outline(
            topic,
            target_audience,
            difficulty,
            duration_hours,
            mode=mode,
        )
        if not outline:
            return {"error": "Echec de generation du plan"}

        if progress_callback:
            progress_callback(
                "modules",
                f"Plan genere: {len(outline.get('modules', []))} modules",
            )

        # Step 2: Generate lessons for each module
        modules = []
        for i, mod_outline in enumerate(outline.get("modules", [])):
            if progress_callback:
                progress_callback(
                    "lessons",
                    f"Generation module {i + 1}: " f"{mod_outline.get('title', '')}",
                )

            lessons = self._generate_lessons(
                topic,
                target_audience,
                difficulty,
                mod_outline,
                mode=mode,
            )

            modules.append(
                {
                    "module_number": i + 1,
                    "title": mod_outline.get("title", ""),
                    "description": mod_outline.get("description", ""),
                    "estimated_duration_minutes": mod_outline.get("estimated_duration_minutes", 30),
                    "lessons": lessons,
                }
            )

        if progress_callback:
            progress_callback("done", "Cours genere avec succes")

        return {
            "title": outline.get("title", topic),
            "description": outline.get("description", ""),
            "topic": topic,
            "target_audience": target_audience,
            "difficulty_level": difficulty,
            "duration_hours": duration_hours,
            "mode": mode,
            "learning_objectives": outline.get("learning_objectives", []),
            "modules": modules,
        }

    def generate_course_from_document(
        self,
        document_content: str,
        target_audience: str,
        difficulty: str,
        duration_hours: int,
        progress_callback=None,
        mode: str = "free",
    ) -> Dict[str, Any]:
        """
        Genere un cours a partir d'un document existant
        (PDF, PPTX, HTML, Markdown).

        Args:
            document_content: Contenu textuel du document
            target_audience: Public cible
            difficulty: beginner, intermediate, advanced
            duration_hours: Duree en heures
            progress_callback: fn(step, detail) pour SSE

        Returns:
            Dict structure du cours complet
        """
        mode_cfg = self._get_mode_config(mode)

        if progress_callback:
            label = mode_cfg.get("label", "Cours")
            progress_callback(
                "analyzing",
                f"Analyse du document ({label})...",
            )

        mode_ctx = mode_cfg.get("system_context", "")
        system_prompt = (
            "Tu es un expert en ingenierie pedagogique. "
            "Tu transformes des supports de formation existants "
            "en cours e-learning structures et interactifs, "
            "avec des modules, lecons, exercices et objectifs "
            "alignes sur la taxonomie de Bloom. "
            "Reponds uniquement en JSON."
        )
        if mode_ctx:
            system_prompt += f" CONTEXTE: {mode_ctx}"

        # Truncate document if too long for context
        doc_excerpt = document_content[:12000]

        prompt = f"""Transforme ce document de formation en un cours
e-learning structure.

DOCUMENT SOURCE:
{doc_excerpt}

PUBLIC CIBLE: {target_audience}
NIVEAU: {difficulty}
DUREE TOTALE: {duration_hours} heures

Retourne UNIQUEMENT un JSON valide:
{{
    "title": "Titre du cours (deduit du document)",
    "description": "Description engageante (3-4 phrases)",
    "topic": "Sujet principal identifie",
    "learning_objectives": [
        "A la fin, l'apprenant sera capable de ..."
    ],
    "modules": [
        {{
            "module_number": 1,
            "title": "Titre du module",
            "description": "Description du module",
            "estimated_duration_minutes": 45,
            "lessons": [
                {{
                    "lesson_number": 1,
                    "title": "Titre de la lecon",
                    "content_markdown": "# Titre\\n\\nContenu detaille...",
                    "key_takeaways": ["Point cle 1"],
                    "practical_exercises": [
                        {{
                            "title": "Exercice",
                            "description": "Description",
                            "hints": ["Indice"]
                        }}
                    ],
                    "estimated_duration_minutes": 20
                }}
            ]
        }}
    ]
}}

REGLES:
- Conserve le contenu et la structure du document source
- Reorganise en modules/lecons logiques si necessaire
- Enrichis avec des exercices pratiques
- Ajoute des objectifs pedagogiques Bloom
- Le content_markdown doit reprendre le contenu original
  enrichi et structure
- Adapte au public cible et au niveau de difficulte
- 1-2 modules par heure de formation"""

        mode_outline_rules = mode_cfg.get("outline_rules", "")
        mode_lesson_rules = mode_cfg.get("lesson_rules", "")
        if mode_outline_rules or mode_lesson_rules:
            prompt += (
                f"\n\nREGLES SPECIFIQUES AU MODE "
                f"'{mode_cfg['label']}':\n"
                f"{mode_outline_rules}\n{mode_lesson_rules}"
            )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
            )
            result = self._parse_json_response(response)

            if not result:
                if progress_callback:
                    progress_callback("error", "Echec du parsing")
                return {"error": "Echec de transformation du document"}

            # Ensure required fields
            result.setdefault("topic", result.get("title", ""))
            result["target_audience"] = target_audience
            result["difficulty_level"] = difficulty
            result["duration_hours"] = duration_hours

            if progress_callback:
                nb_modules = len(result.get("modules", []))
                progress_callback(
                    "done",
                    f"Cours genere: {nb_modules} modules",
                )
            return result

        except Exception as e:
            print(f"Erreur generation depuis document: {e}")
            if progress_callback:
                progress_callback("error", str(e))
            return {"error": str(e)}

    def _generate_outline(
        self,
        topic: str,
        target_audience: str,
        difficulty: str,
        duration_hours: int,
        mode: str = "free",
    ) -> Optional[Dict]:
        """Genere le plan du cours (titre, objectifs, modules)"""
        mode_cfg = self._get_mode_config(mode)
        mode_ctx = mode_cfg.get("system_context", "")

        system_prompt = (
            "Tu es un expert en ingenierie pedagogique et en "
            "conception de formations e-learning. Tu crees des "
            "cours structures et engageants, alignes sur la "
            "taxonomie de Bloom. Reponds uniquement en JSON."
        )
        if mode_ctx:
            system_prompt += f" CONTEXTE: {mode_ctx}"

        mode_rules = mode_cfg.get("outline_rules", "")
        extra_rules = (
            f"\n\nREGLES SPECIFIQUES AU MODE " f"'{mode_cfg['label']}':\n{mode_rules}"
            if mode_rules
            else ""
        )

        prompt = f"""Cree le plan d'un cours e-learning sur le sujet suivant :

SUJET: {topic}
PUBLIC CIBLE: {target_audience}
NIVEAU: {difficulty}
DUREE TOTALE: {duration_hours} heures

Retourne UNIQUEMENT un JSON valide avec cette structure:
{{
    "title": "Titre du cours",
    "description": "Description engageante du cours (3-4 phrases)",
    "learning_objectives": [
        "A la fin, l'apprenant sera capable de [verbe Bloom] ...",
        "..."
    ],
    "modules": [
        {{
            "title": "Titre du module",
            "description": "Description du module",
            "estimated_duration_minutes": 45,
            "lesson_titles": ["Lecon 1", "Lecon 2"]
        }}
    ]
}}

REGLES:
- Les objectifs doivent utiliser la taxonomie de Bloom
  (Connaitre, Comprendre, Appliquer, Analyser, Evaluer, Creer)
- Le nombre de modules doit correspondre a la duree
  (~1-2 modules par heure)
- Chaque module a 2-4 lecons
- La progression doit etre logique (du simple au complexe)
- Adapte le vocabulaire au public cible{extra_rules}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )
            return self._parse_json_response(response)
        except Exception as e:
            print(f"Erreur generation outline: {e}")
            return None

    def _generate_lessons(
        self,
        topic: str,
        target_audience: str,
        difficulty: str,
        module_outline: Dict,
        mode: str = "free",
    ) -> List[Dict]:
        """Genere les lecons detaillees d'un module"""
        mode_cfg = self._get_mode_config(mode)
        mode_ctx = mode_cfg.get("system_context", "")

        system_prompt = (
            "Tu es un expert en creation de contenu pedagogique. "
            "Tu generes du contenu de cours detaille, clair et "
            "engageant avec des exemples pratiques. "
            "Reponds uniquement en JSON."
        )
        if mode_ctx:
            system_prompt += f" CONTEXTE: {mode_ctx}"

        lesson_titles = module_outline.get("lesson_titles", ["Lecon 1"])
        lessons_list = json.dumps(lesson_titles, ensure_ascii=False)

        mode_lesson_rules = mode_cfg.get("lesson_rules", "")
        extra_rules = (
            f"\n\nREGLES SPECIFIQUES AU MODE " f"'{mode_cfg['label']}':\n{mode_lesson_rules}"
            if mode_lesson_rules
            else ""
        )

        prompt = f"""Genere le contenu detaille des lecons pour ce module:

MODULE: {module_outline.get('title', '')}
DESCRIPTION: {module_outline.get('description', '')}
SUJET GENERAL: {topic}
PUBLIC: {target_audience}
NIVEAU: {difficulty}
LECONS A GENERER: {lessons_list}

Retourne UNIQUEMENT un JSON valide:
{{
    "lessons": [
        {{
            "lesson_number": 1,
            "title": "Titre de la lecon",
            "content_markdown": "# Titre\\n\\nContenu detaille en Markdown...\\n\\n## Section 1\\n...",
            "key_takeaways": [
                "Point cle 1",
                "Point cle 2"
            ],
            "practical_exercises": [
                {{
                    "title": "Exercice pratique",
                    "description": "Description de l'exercice",
                    "hints": ["Indice 1"]
                }}
            ],
            "estimated_duration_minutes": 15
        }}
    ]
}}

REGLES:
- Le content_markdown doit etre detaille (min 300 mots par lecon)
- Inclure des exemples concrets et du code si pertinent
- 2-4 points cles par lecon
- Au moins 1 exercice pratique par lecon
- Adapter le niveau de detail au public cible{extra_rules}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )
            result = self._parse_json_response(response)
            if result and "lessons" in result:
                return result["lessons"]
            return []
        except Exception as e:
            print(f"Erreur generation lecons: {e}")
            return []

    def regenerate_with_feedback(
        self,
        course_data: Dict,
        feedback: str,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Regenere un cours avec du feedback utilisateur"""
        if progress_callback:
            progress_callback("regenerating", "Regeneration en cours...")

        system_prompt = (
            "Tu es un expert en ingenierie pedagogique. "
            "Tu dois modifier un cours e-learning existant "
            "en tenant compte du feedback de l'utilisateur. "
            "Conserve la structure et ameliore le contenu. "
            "Reponds uniquement en JSON."
        )

        # Simplify course data for prompt
        course_summary = json.dumps(
            {
                "title": course_data.get("title", ""),
                "description": course_data.get("description", ""),
                "learning_objectives": course_data.get("learning_objectives", []),
                "modules": [
                    {
                        "title": m.get("title", ""),
                        "lessons": [les.get("title", "") for les in m.get("lessons", [])],
                    }
                    for m in course_data.get("modules", [])
                ],
            },
            ensure_ascii=False,
        )

        prompt = f"""Voici le cours actuel (resume):
{course_summary}

FEEDBACK DE L'UTILISATEUR:
{feedback}

Genere une version amelioree complete du cours en tenant compte
du feedback. Retourne le meme format JSON que pour la generation
initiale:
{{
    "title": "...",
    "description": "...",
    "learning_objectives": [...],
    "modules": [
        {{
            "module_number": 1,
            "title": "...",
            "description": "...",
            "estimated_duration_minutes": 45,
            "lessons": [
                {{
                    "lesson_number": 1,
                    "title": "...",
                    "content_markdown": "...",
                    "key_takeaways": [...],
                    "practical_exercises": [
                        {{"title": "...", "description": "...", "hints": [...]}}
                    ],
                    "estimated_duration_minutes": 15
                }}
            ]
        }}
    ]
}}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )
            result = self._parse_json_response(response)
            if result:
                result["topic"] = course_data.get("topic", "")
                result["target_audience"] = course_data.get("target_audience", "")
                result["difficulty_level"] = course_data.get("difficulty_level", "intermediate")
                result["duration_hours"] = course_data.get("duration_hours", 1)
                if progress_callback:
                    progress_callback("done", "Cours regenere")
                return result

            return {"error": "Echec de regeneration"}
        except Exception as e:
            print(f"Erreur regeneration: {e}")
            return {"error": str(e)}

    # ==================
    # QUIZ GENERATION
    # ==================

    def generate_quiz(
        self,
        lesson_title: str,
        lesson_content: str,
        difficulty: str = "medium",
        num_questions: int = 10,
        progress_callback=None,
        mode: str = "free",
    ) -> Dict[str, Any]:
        """
        Genere un quiz a partir du contenu d'une lecon.

        Args:
            lesson_title: Titre de la lecon
            lesson_content: Contenu markdown de la lecon
            difficulty: easy, medium, hard
            num_questions: Nombre de questions
            progress_callback: fn(step, detail)
            mode: free, interview, certification, training

        Returns:
            Dict avec titre et questions
        """
        mode_cfg = self._get_mode_config(mode)

        if progress_callback:
            label = mode_cfg.get("label", "Quiz")
            progress_callback(
                "generating",
                f"Generation des questions ({label})...",
            )

        mode_ctx = mode_cfg.get("system_context", "")
        system_prompt = (
            "Tu es un expert en evaluation pedagogique. "
            "Tu crees des questions variees et pertinentes "
            "qui testent la comprehension reelle, pas juste "
            "la memorisation. Reponds uniquement en JSON."
        )
        if mode_ctx:
            system_prompt += f" CONTEXTE: {mode_ctx}"

        # Distribute questions across types and difficulties
        difficulty_dist = self._get_difficulty_distribution(difficulty, num_questions)

        prompt = f"""Genere un quiz de {num_questions} questions pour cette lecon:

TITRE: {lesson_title}
CONTENU:
{lesson_content[:5000]}

DISTRIBUTION DES DIFFICULTES:
{json.dumps(difficulty_dist, ensure_ascii=False)}

Retourne UNIQUEMENT un JSON valide:
{{
    "title": "Quiz - {lesson_title}",
    "questions": [
        {{
            "question_number": 1,
            "question_type": "mcq",
            "question_text": "Question claire et precise?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option B",
            "explanation": "Explication pedagogique detaillee",
            "difficulty_level": "easy",
            "bloom_level": "remember"
        }},
        {{
            "question_number": 2,
            "question_type": "true_false",
            "question_text": "Affirmation a evaluer.",
            "options": ["Vrai", "Faux"],
            "correct_answer": "Faux",
            "explanation": "...",
            "difficulty_level": "medium",
            "bloom_level": "understand"
        }},
        {{
            "question_number": 3,
            "question_type": "fill_blank",
            "question_text": "Le ___ est utilise pour ...",
            "options": [],
            "correct_answer": "mot attendu",
            "explanation": "...",
            "difficulty_level": "medium",
            "bloom_level": "apply"
        }},
        {{
            "question_number": 4,
            "question_type": "open_ended",
            "question_text": "Expliquez...",
            "options": [],
            "correct_answer": "Reponse attendue resumee",
            "explanation": "...",
            "difficulty_level": "hard",
            "bloom_level": "analyze"
        }}
    ]
}}

REGLES:
- Varier les types: mcq, true_false, fill_blank, open_ended
- Repartir: ~40%% mcq, ~20%% true_false, ~20%% fill_blank, ~20%% open_ended
- Les MCQ ont toujours 4 options avec 1 seule correcte
- Les explications doivent etre pedagogiques (enseigner, pas juste corriger)
- Utiliser tous les niveaux de Bloom
- La difficulte "easy" correspond a remember/understand
- La difficulte "medium" correspond a apply/analyze
- La difficulte "hard" correspond a evaluate/create"""

        mode_quiz_rules = mode_cfg.get("quiz_rules", "")
        if mode_quiz_rules:
            prompt += (
                f"\n\nREGLES SPECIFIQUES AU MODE " f"'{mode_cfg['label']}':\n{mode_quiz_rules}"
            )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
            )
            result = self._parse_json_response(response)
            if result:
                if progress_callback:
                    progress_callback(
                        "done",
                        f"{len(result.get('questions', []))} " "questions generees",
                    )
                return result

            return {"error": "Echec de generation du quiz"}
        except Exception as e:
            print(f"Erreur generation quiz: {e}")
            return {"error": str(e)}

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalise un texte pour comparaison souple :
        minuscules, sans ponctuation superflue, espaces normalisés.
        """
        t = text.strip().lower()
        # Apostrophes typographiques → standard
        t = re.sub(r"[''`\u2019]", "'", t)
        # Supprimer ponctuation de début/fin
        t = re.sub(r"^[\s.,;:!?\-–—]+|[\s.,;:!?\-–—]+$", "", t)
        # Normaliser les espaces multiples
        t = re.sub(r"\s+", " ", t)
        return t

    @staticmethod
    def _mcq_match(student: str, correct: str) -> bool:
        """
        Vérifie si une réponse MCQ correspond à la bonne réponse.

        Gère les cas :
        - Lettre seule : "A" correspond à "A. Paris" ou "A) Paris"
        - Texte seul : "Paris" correspond à "A. Paris"
        - Variantes de ponctuation : "a." "a)" "a:" "a -"
        """
        s = student.strip().lower()
        c = correct.strip().lower()

        if s == c:
            return True

        # Pattern de préfixe lettre (a. / a) / a: / a -)
        _letter_re = re.compile(r"^([a-d])[.):\s\-]")

        s_m = _letter_re.match(s)
        c_m = _letter_re.match(c)
        s_letter = s_m.group(1) if s_m else None
        c_letter = c_m.group(1) if c_m else None

        # Cas "A" vs "A. Paris" (ou inverse)
        if s == c_letter or c == s_letter:
            return True

        # Comparer les textes après le préfixe lettre
        s_text = re.sub(r"^[a-d][.):\s\-]+", "", s).strip()
        c_text = re.sub(r"^[a-d][.):\s\-]+", "", c).strip()
        if s_text and c_text and s_text == c_text:
            return True

        return False

    def evaluate_answer(
        self,
        question: Dict,
        student_answer: str,
    ) -> Dict[str, Any]:
        """
        Evalue la reponse d'un etudiant.

        Pour MCQ: comparaison avec gestion lettre/texte (A / A. Paris / Paris).
        Pour true_false: comparaison normalisée (vrai/true, faux/false).
        Pour fill_blank: comparaison après normalisation du texte.
        Pour open_ended: evaluation par LLM.

        Args:
            question: Dict avec question_type, correct_answer, etc.
            student_answer: Reponse de l'etudiant

        Returns:
            {is_correct, explanation, feedback}
        """
        q_type = question.get("question_type", "mcq")
        correct = question.get("correct_answer", "")
        explanation = question.get("explanation", "")

        if q_type == "mcq":
            is_correct = self._mcq_match(student_answer, correct)
            return {
                "is_correct": is_correct,
                "explanation": explanation,
                "feedback": (
                    "Bonne reponse !" if is_correct else f"La bonne reponse etait : {correct}"
                ),
            }

        elif q_type == "true_false":
            # Normaliser vrai/faux ↔ true/false
            _tf_map = {"vrai": "true", "faux": "false", "oui": "true", "non": "false"}
            s_norm = self._normalize_text(student_answer)
            c_norm = self._normalize_text(correct)
            s_norm = _tf_map.get(s_norm, s_norm)
            c_norm = _tf_map.get(c_norm, c_norm)
            is_correct = s_norm == c_norm
            return {
                "is_correct": is_correct,
                "explanation": explanation,
                "feedback": (
                    "Bonne reponse !" if is_correct else f"La bonne reponse etait : {correct}"
                ),
            }

        elif q_type == "fill_blank":
            is_correct = self._normalize_text(student_answer) == self._normalize_text(correct)
            # Tolérance partielle : chaque mot significatif de la réponse attendue est présent
            if not is_correct:
                correct_words = [
                    w for w in self._normalize_text(correct).split() if len(w) > 2
                ]
                answer_norm = self._normalize_text(student_answer)
                if correct_words and all(w in answer_norm for w in correct_words):
                    is_correct = True
            return {
                "is_correct": is_correct,
                "explanation": explanation,
                "feedback": (
                    "Bonne reponse !" if is_correct else f"La reponse attendue etait : {correct}"
                ),
            }

        elif q_type == "open_ended":
            return self._evaluate_open_ended(question, student_answer)

        return {
            "is_correct": False,
            "explanation": "",
            "feedback": "Type de question non reconnu",
        }

    def _evaluate_open_ended(
        self,
        question: Dict,
        student_answer: str,
    ) -> Dict[str, Any]:
        """Evalue une reponse ouverte via LLM"""
        system_prompt = (
            "Tu es un evaluateur pedagogique bienveillant. "
            "Tu evalues les reponses des etudiants de maniere "
            "constructive. Reponds uniquement en JSON."
        )

        prompt = f"""Evalue cette reponse d'etudiant:

QUESTION: {question.get('question_text', '')}
REPONSE ATTENDUE: {question.get('correct_answer', '')}
REPONSE DE L'ETUDIANT: {student_answer}

Retourne un JSON:
{{
    "is_correct": true ou false,
    "score": 0.0 a 1.0 (credit partiel possible),
    "feedback": "Feedback constructif et pedagogique",
    "missing_elements": ["Element manquant 1", "..."]
}}

REGLES:
- Accepter les reformulations et synonymes
- Credit partiel si la reponse est partiellement correcte
- Le feedback doit enseigner, pas juste evaluer
- is_correct = true si score >= 0.7"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )
            result = self._parse_json_response(response)
            if result:
                return {
                    "is_correct": result.get("is_correct", False),
                    "explanation": question.get("explanation", ""),
                    "feedback": result.get("feedback", ""),
                }
        except Exception as e:
            print(f"Erreur evaluation ouverte: {e}")

        # Fallback: simple keyword match
        correct_lower = question.get("correct_answer", "").lower()
        answer_lower = student_answer.lower()
        keywords = [w for w in correct_lower.split() if len(w) > 3]
        matches = sum(1 for kw in keywords if kw in answer_lower)
        is_correct = matches / len(keywords) >= 0.5 if keywords else False

        return {
            "is_correct": is_correct,
            "explanation": question.get("explanation", ""),
            "feedback": (
                "Reponse partiellement correcte."
                if is_correct
                else "Reponse incomplete. " + question.get("explanation", "")
            ),
        }

    def adapt_difficulty(self, recent_answers: List[Dict]) -> Optional[str]:
        """
        Adapte la difficulte basee sur les reponses recentes.

        Args:
            recent_answers: Liste des 3 dernieres reponses
                [{is_correct: bool, ...}]

        Returns:
            Nouvelle difficulte (easy/medium/hard) ou None
        """
        if len(recent_answers) < 3:
            return None

        last_3 = recent_answers[:3]
        all_correct = all(a.get("is_correct") for a in last_3)
        all_wrong = all(not a.get("is_correct") for a in last_3)

        if all_correct:
            return "hard"
        elif all_wrong:
            return "easy"

        return None

    def _get_difficulty_distribution(
        self, base_difficulty: str, num_questions: int
    ) -> Dict[str, int]:
        """Calcule la distribution de difficulte"""
        if base_difficulty == "easy":
            return {
                "easy": max(1, int(num_questions * 0.5)),
                "medium": max(1, int(num_questions * 0.35)),
                "hard": max(1, num_questions - int(num_questions * 0.85)),
            }
        elif base_difficulty == "hard":
            return {
                "easy": max(1, int(num_questions * 0.15)),
                "medium": max(1, int(num_questions * 0.35)),
                "hard": max(1, num_questions - int(num_questions * 0.5)),
            }
        else:  # medium
            return {
                "easy": max(1, int(num_questions * 0.3)),
                "medium": max(1, int(num_questions * 0.4)),
                "hard": max(1, num_questions - int(num_questions * 0.7)),
            }

    # ==================
    # LEARNING PATHS
    # ==================

    def analyze_knowledge_gaps(
        self,
        quiz_results: List[Dict],
        course_modules: List[Dict],
    ) -> Dict[str, Any]:
        """
        Analyse les lacunes a partir des resultats de quiz.

        Args:
            quiz_results: Liste des tentatives completees
            course_modules: Modules du cours

        Returns:
            {weak_modules, strong_modules, recommended_review}
        """
        if not quiz_results:
            return {
                "weak_modules": [],
                "strong_modules": [],
                "recommended_review": [
                    {
                        "module_id": m.get("id"),
                        "reason": "Aucun quiz realise",
                    }
                    for m in course_modules
                ],
            }

        system_prompt = (
            "Tu es un expert en evaluation pedagogique. "
            "Tu analyses les performances des apprenants pour "
            "identifier les lacunes et forces. "
            "Reponds uniquement en JSON."
        )

        # Build results summary
        results_summary = []
        for r in quiz_results:
            results_summary.append(
                {
                    "quiz_title": r.get("quiz_title", ""),
                    "score": r.get("score_percentage", 0),
                    "lesson_id": r.get("lesson_id"),
                }
            )

        modules_summary = [
            {
                "id": m.get("id"),
                "title": m.get("title", ""),
                "lessons": [
                    {"id": les.get("id"), "title": les.get("title", "")}
                    for les in m.get("lessons", [])
                ],
            }
            for m in course_modules
        ]

        prompt = f"""Analyse les performances de cet apprenant:

RESULTATS DES QUIZ:
{json.dumps(results_summary, ensure_ascii=False)}

MODULES DU COURS:
{json.dumps(modules_summary, ensure_ascii=False)}

Retourne un JSON:
{{
    "weak_modules": [
        {{
            "module_id": 1,
            "title": "Module faible",
            "mastery": 0.3,
            "reason": "Pourquoi c'est faible"
        }}
    ],
    "strong_modules": [
        {{
            "module_id": 2,
            "title": "Module maitrise",
            "mastery": 0.9,
            "reason": "Pourquoi c'est fort"
        }}
    ],
    "recommended_review": [
        {{
            "module_id": 1,
            "reason": "Raison de la recommandation"
        }}
    ]
}}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception as e:
            print(f"Erreur analyse lacunes: {e}")

        return {
            "weak_modules": [],
            "strong_modules": [],
            "recommended_review": [],
        }

    def generate_learning_path(
        self,
        gaps: Dict,
        goals: List[str],
        course_modules: List[Dict],
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Genere un parcours d'apprentissage personnalise.

        Args:
            gaps: Resultat de analyze_knowledge_gaps
            goals: Objectifs de l'apprenant
            course_modules: Modules du cours
            progress_callback: fn(step, detail)

        Returns:
            {path_steps, knowledge_gaps, recommendations,
             completion_estimate}
        """
        if progress_callback:
            progress_callback("analyzing", "Analyse des lacunes...")

        system_prompt = (
            "Tu es un expert en parcours d'apprentissage "
            "personnalises. Tu sequences les modules de maniere "
            "optimale pour combler les lacunes et atteindre "
            "les objectifs. Reponds uniquement en JSON."
        )

        modules_info = json.dumps(
            [
                {
                    "id": m.get("id"),
                    "title": m.get("title", ""),
                    "description": m.get("description", ""),
                }
                for m in course_modules
            ],
            ensure_ascii=False,
        )

        prompt = f"""Genere un parcours d'apprentissage personnalise:

OBJECTIFS DE L'APPRENANT:
{json.dumps(goals, ensure_ascii=False)}

ANALYSE DES LACUNES:
{json.dumps(gaps, ensure_ascii=False)}

MODULES DISPONIBLES:
{modules_info}

Retourne un JSON:
{{
    "path_steps": [
        {{
            "step_number": 1,
            "type": "review",
            "module_id": 1,
            "title": "Titre du module",
            "reason": "Pourquoi commencer par ce module",
            "estimated_duration_minutes": 30
        }}
    ],
    "recommendations": [
        {{
            "type": "practice",
            "module_id": 1,
            "reason": "Raison de la recommandation"
        }}
    ],
    "completion_estimate_hours": 3.5
}}

REGLES:
- Commencer par les modules faibles (lacunes)
- Inclure les modules forts en revision rapide
- Respecter les prerequis (progression logique)
- Adapter l'estimation au niveau de l'apprenant
- Types possibles: review, study, practice, assessment"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
            )
            result = self._parse_json_response(response)
            if result:
                if progress_callback:
                    progress_callback("done", "Parcours genere")
                return {
                    "path_steps": result.get("path_steps", []),
                    "knowledge_gaps": gaps.get("weak_modules", []),
                    "recommendations": result.get("recommendations", []),
                    "completion_estimate_hours": result.get("completion_estimate_hours", 0),
                }
        except Exception as e:
            print(f"Erreur generation parcours: {e}")

        if progress_callback:
            progress_callback("done", "Parcours genere (basic)")

        return {
            "path_steps": [
                {
                    "step_number": i + 1,
                    "type": "study",
                    "module_id": m.get("id"),
                    "title": m.get("title", ""),
                    "reason": "Module du cours",
                    "estimated_duration_minutes": m.get("estimated_duration_minutes", 30),
                }
                for i, m in enumerate(course_modules)
            ],
            "knowledge_gaps": gaps.get("weak_modules", []),
            "recommendations": gaps.get("recommended_review", []),
            "completion_estimate_hours": sum(
                m.get("estimated_duration_minutes", 30) for m in course_modules
            )
            / 60,
        }

    # ==================
    # INTERVIEW CHAT
    # ==================

    def interview_chat(
        self,
        messages: List[Dict[str, str]],
        topic: str = "",
        role: str = "",
        interviewer_name: str = "",
        interviewer_linkedin: str = "",
    ) -> str:
        """
        Répond dans un mode chat d'entretien interactif.

        L'IA joue le rôle d'un recruteur / interviewer technique et
        pose des questions de suivi basées sur les réponses de l'apprenant.

        Args:
            messages: Historique de la conversation
                [{"role": "user"|"assistant", "content": "..."}]
            topic: Sujet de l'entretien (ex: "Data Engineering", "Python")
            role: Poste visé (ex: "Data Engineer Senior")
            interviewer_name: Nom/Poste de l'interviewer réel ou simulé
            interviewer_linkedin: Lien LinkedIn de l'interviewer pour contexte

        Returns:
            Réponse de l'interviewer (texte)
        """
        interviewer_info = ""
        if interviewer_name:
            interviewer_info += f"Tu t'appelles {interviewer_name} ou tu occupes ce poste. "
        if interviewer_linkedin:
            interviewer_info += f"Voici ton profil pour inspiration : {interviewer_linkedin}. "

        topic_line = f"Poste : {role}\nDomaine : {topic}" if topic or role else ""
        system_prompt = f"""Tu es un recruteur technique expérimenté dans un entretien simulé.
{topic_line}
{interviewer_info}

Ton rôle :
- Jouer le rôle d'un interviewer professionnel, bienveillant mais exigeant
- Poser des questions techniques et comportementales pertinentes
- Approfondir les réponses du candidat avec des questions de suivi
- Ne pas donner les réponses : faire réfléchir le candidat
- Adapter la difficulté selon la qualité des réponses
- Terminer par "FIN_ENTRETIEN" uniquement si l'utilisateur demande explicitement à arrêter

Style : conversationnel, professionnel, concis (2-4 phrases max par tour)."""

        response = self.llm.generate_with_context(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
        )
        return response.strip()

    def analyze_interview_performance(
        self,
        conversation: List[Dict[str, str]],
        topic: str = "",
        role: str = "",
        interviewer_name: str = "",
        interviewer_linkedin: str = "",
    ) -> Dict[str, Any]:
        """
        Analyse les performances d'un entretien simulé.

        Args:
            conversation: Historique complet de la conversation
            topic: Sujet de l'entretien
            role: Poste visé
            interviewer_name: Nom de l'interviewer
            interviewer_linkedin: Profil LinkedIn de l'interviewer

        Returns:
            {overall_score, strengths, improvements, detailed_feedback, recommendations}
        """
        # Filtrer les messages utilisateur pour l'analyse
        user_turns = [m["content"] for m in conversation if m.get("role") == "user"]
        if not user_turns:
            return {
                "overall_score": 0,
                "strengths": [],
                "improvements": ["Aucune réponse fournie"],
                "detailed_feedback": "Entretien vide.",
                "recommendations": [],
            }

        conversation_text = "\n".join(
            f"[{m.get('role', 'user').upper()}] {m.get('content', '')}"
            for m in conversation
        )

        interviewer_ctx = f" (Interviewer: {interviewer_name})" if interviewer_name else ""

        prompt = f"""Analyse cet entretien simulé{interviewer_ctx} et évalue les performances du candidat.

POSTE VISÉ : {role or "Non précisé"}
DOMAINE : {topic or "Non précisé"}

TRANSCRIPT :
{conversation_text[:4000]}

Retourne un JSON avec :
{{
    "overall_score": 0-100,
    "grade": "A/B/C/D/F",
    "strengths": ["Point fort 1", "Point fort 2", "Point fort 3"],
    "improvements": ["Axe d'amélioration 1", "Axe 2", "Axe 3"],
    "detailed_feedback": "Analyse narrative de 3-4 phrases sur la qualité des réponses",
    "technical_score": 0-100,
    "communication_score": 0-100,
    "recommendations": ["Recommandation 1", "Recommandation 2"]
}}

RÈGLES :
- Bienveillant mais objectif
- Basé uniquement sur ce qui a été dit
- Retourne UNIQUEMENT le JSON"""

        system_prompt = (
            "Tu es un expert en évaluation RH et performance en entretien."
            " Reponds uniquement en JSON."
        )
        try:
            response = self.llm.generate(
                prompt=prompt, system_prompt=system_prompt, temperature=0.3
            )
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception as e:
            print(f"Erreur analyse entretien: {e}")

        return {
            "overall_score": 50,
            "grade": "C",
            "strengths": [],
            "improvements": ["Analyse non disponible"],
            "detailed_feedback": "Impossible d'analyser les performances.",
            "technical_score": 50,
            "communication_score": 50,
            "recommendations": [],
        }

    # ==================
    # PREMIUM RESOURCES
    # ==================

    def generate_premium_resources(
        self,
        course: Dict,
        resource_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Génère des ressources premium exportables pour un cours.

        Args:
            course: Dict du cours avec modules et leçons
            resource_types: Liste de types parmi ["memo", "summary", "cheatsheet"]
                            Défaut : tous les types

        Returns:
            {memo_cards, module_summaries, cheatsheet, generated_at}
        """
        if resource_types is None:
            resource_types = ["memo", "summary", "cheatsheet"]

        course_title = course.get("title", "Cours")
        modules = course.get("modules", [])

        result: Dict[str, Any] = {"course_title": course_title}

        # --- Fiches mémo (une par module) ---
        if "memo" in resource_types:
            result["memo_cards"] = self._generate_memo_cards(course_title, modules) if modules else []

        # --- Résumés condensés par module ---
        if "summary" in resource_types:
            result["module_summaries"] = (
                self._generate_module_summaries(course_title, modules) if modules else []
            )

        # --- Cheatsheet globale du cours ---
        if "cheatsheet" in resource_types:
            result["cheatsheet"] = self._generate_cheatsheet(course_title, modules)

        return result

    def _generate_memo_cards(
        self, course_title: str, modules: List[Dict]
    ) -> List[Dict]:
        """Génère une fiche mémo HTML par module."""
        memo_cards = []
        for module in modules:
            lessons_text = "\n".join(
                f"- {les.get('title', '')}: {les.get('content', '')[:400]}"
                for les in module.get("lessons", [])
            )
            prompt = f"""Cours : {course_title}
Module : {module.get("title", "")}

Contenu des leçons :
{lessons_text or "(aucun contenu disponible)"}

Génère une fiche mémo HTML compacte (fiche de révision) avec :
- Titre du module en en-tête coloré
- Les 5-8 concepts clés en puces courtes (1 ligne max par concept)
- Un encadré "À retenir absolument" avec 2-3 points essentiels
- Style CSS inline (carte blanche, bordure bleue, police sans-serif)
- Format A6 paysage (max-width: 420px)

Retourne UNIQUEMENT le HTML, sans markdown ni préambule."""

            system_prompt = (
                "Tu es un expert en design pédagogique. "
                "Tu crées des fiches mémo visuelles et impactantes."
            )
            try:
                html = self.llm.generate(
                    prompt=prompt, system_prompt=system_prompt, temperature=0.4
                )
                html = re.sub(r"^```(?:html)?\s*", "", html.strip())
                html = re.sub(r"\s*```$", "", html)
            except Exception as e:
                html = f"<p>Erreur génération fiche mémo : {e}</p>"

            memo_cards.append(
                {
                    "module_id": module.get("id"),
                    "module_title": module.get("title", ""),
                    "html": html.strip(),
                }
            )
        return memo_cards

    def _generate_module_summaries(
        self, course_title: str, modules: List[Dict]
    ) -> List[Dict]:
        """Génère un résumé condensé par module."""
        summaries = []
        for module in modules:
            lessons_text = "\n".join(
                f"Leçon : {les.get('title', '')}\n{les.get('content', '')[:600]}"
                for les in module.get("lessons", [])
            )
            prompt = f"""Cours : {course_title}
Module : {module.get("title", "")}

Contenu :
{lessons_text or "(aucun contenu disponible)"}

Rédige un résumé condensé en Markdown (200-300 mots) :
- Commence par une phrase d'accroche sur l'enjeu du module
- Structure en 3-4 paragraphes thématiques
- Mets en **gras** les termes clés
- Termine par "En bref :" + 2 lignes de synthèse

Retourne UNIQUEMENT le Markdown."""

            system_prompt = "Tu es un expert en synthèse pédagogique."
            try:
                md = self.llm.generate(
                    prompt=prompt, system_prompt=system_prompt, temperature=0.4
                )
                md = re.sub(r"^```(?:markdown|md)?\s*", "", md.strip())
                md = re.sub(r"\s*```$", "", md)
            except Exception as e:
                md = f"Erreur génération résumé : {e}"

            summaries.append(
                {
                    "module_id": module.get("id"),
                    "module_title": module.get("title", ""),
                    "markdown": md.strip(),
                }
            )
        return summaries

    def _generate_cheatsheet(
        self, course_title: str, modules: List[Dict]
    ) -> str:
        """Génère une cheatsheet globale HTML du cours."""
        modules_overview = "\n".join(
            f"Module {i+1}: {m.get('title', '')} — "
            + ", ".join(les.get("title", "") for les in m.get("lessons", []))
            for i, m in enumerate(modules)
        )

        prompt = f"""Cours : {course_title}

Structure :
{modules_overview or "(aucun module disponible)"}

Génère une cheatsheet HTML globale (mémo de référence rapide) :
- En-tête avec titre du cours et date de génération
- Tableau récapitulatif par module : Module | Concepts clés | Commandes/Formules/Points mémo
- Section "Top 10 des points à retenir" (puces numérotées)
- Style CSS inline professionnel (fond gris clair, tableaux bordés, police monospace pour les commandes)
- Max-width 900px

Retourne UNIQUEMENT le HTML, sans markdown ni préambule."""

        system_prompt = (
            "Tu es un expert en cheatsheets techniques et pédagogiques."
        )
        try:
            html = self.llm.generate(
                prompt=prompt, system_prompt=system_prompt, temperature=0.4
            )
            html = re.sub(r"^```(?:html)?\s*", "", html.strip())
            html = re.sub(r"\s*```$", "", html)
        except Exception as e:
            html = f"<p>Erreur génération cheatsheet : {e}</p>"

        return html.strip()

    # ==================
    # HELPERS
    # ==================

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse une reponse LLM contenant du JSON"""
        if not response:
            return None

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{.*\}",
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    text = match.group(1) if "```" in pattern else match.group(0)
                    return json.loads(text)
                except json.JSONDecodeError:
                    continue

        return None
