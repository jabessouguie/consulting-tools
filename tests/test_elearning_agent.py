"""
Tests unitaires pour l'agent E-learning
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.elearning_agent import ElearningAgent


@pytest.fixture
def agent():
    """Agent avec LLM mocke"""
    with patch("agents.elearning_agent.LLMClient") as mock_cls:
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        a = ElearningAgent()
        a.llm = mock_llm
        yield a


# ==================
# PARSE JSON
# ==================


class TestParseJson:
    @pytest.mark.unit
    def test_parse_direct_json(self, agent):
        result = agent._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_code_block(self, agent):
        text = '```json\n{"key": "value"}\n```'
        result = agent._parse_json_response(text)
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_generic_block(self, agent):
        text = 'Voici le resultat:\n```\n{"key": "value"}\n```'
        result = agent._parse_json_response(text)
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_embedded(self, agent):
        text = 'Voici: {"key": "value"} et voila.'
        result = agent._parse_json_response(text)
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_json_empty(self, agent):
        assert agent._parse_json_response("") is None
        assert agent._parse_json_response(None) is None

    @pytest.mark.unit
    def test_parse_json_invalid(self, agent):
        assert agent._parse_json_response("not json at all") is None


# ==================
# COURSE GENERATION
# ==================


class TestCourseGeneration:
    @pytest.mark.unit
    def test_generate_outline(self, agent):
        outline = {
            "title": "Python pour debutants",
            "description": "Un cours complet",
            "learning_objectives": [
                "Comprendre les bases",
                "Ecrire des programmes",
            ],
            "modules": [
                {
                    "title": "Module 1",
                    "description": "Desc",
                    "estimated_duration_minutes": 45,
                    "lesson_titles": ["Lecon 1", "Lecon 2"],
                }
            ],
        }
        agent.llm.generate.return_value = json.dumps(outline)

        result = agent._generate_outline("Python", "Debutants", "beginner", 3)
        assert result is not None
        assert result["title"] == "Python pour debutants"
        assert len(result["modules"]) == 1

    @pytest.mark.unit
    def test_generate_lessons(self, agent):
        lessons = {
            "lessons": [
                {
                    "lesson_number": 1,
                    "title": "Variables",
                    "content_markdown": "# Variables\n\nContenu...",
                    "key_takeaways": ["Point 1"],
                    "practical_exercises": [
                        {
                            "title": "Ex 1",
                            "description": "Desc",
                            "hints": [],
                        }
                    ],
                    "estimated_duration_minutes": 20,
                }
            ]
        }
        agent.llm.generate.return_value = json.dumps(lessons)

        result = agent._generate_lessons(
            "Python",
            "Debutants",
            "beginner",
            {
                "title": "Module 1",
                "description": "Desc",
                "lesson_titles": ["Variables"],
            },
        )
        assert len(result) == 1
        assert result[0]["title"] == "Variables"

    @pytest.mark.unit
    def test_generate_course_full(self, agent):
        outline = {
            "title": "Test Course",
            "description": "Description",
            "learning_objectives": ["Obj 1"],
            "modules": [
                {
                    "title": "Mod 1",
                    "description": "D",
                    "estimated_duration_minutes": 30,
                    "lesson_titles": ["L1"],
                }
            ],
        }
        lessons = {
            "lessons": [
                {
                    "lesson_number": 1,
                    "title": "L1",
                    "content_markdown": "# L1",
                    "key_takeaways": ["K1"],
                    "practical_exercises": [],
                    "estimated_duration_minutes": 15,
                }
            ]
        }
        agent.llm.generate.side_effect = [
            json.dumps(outline),
            json.dumps(lessons),
        ]

        result = agent.generate_course("Python", "Debutants", "beginner", 1)
        assert result["title"] == "Test Course"
        assert result["topic"] == "Python"
        assert len(result["modules"]) == 1
        assert len(result["modules"][0]["lessons"]) == 1

    @pytest.mark.unit
    def test_generate_course_outline_failure(self, agent):
        agent.llm.generate.return_value = "invalid"

        result = agent.generate_course("Python", "Debutants", "beginner", 1)
        assert "error" in result

    @pytest.mark.unit
    def test_generate_from_document(self, agent):
        course = {
            "title": "Cours depuis PDF",
            "description": "Un cours genere depuis un document",
            "topic": "DevOps",
            "learning_objectives": ["Comprendre CI/CD"],
            "modules": [
                {
                    "module_number": 1,
                    "title": "Introduction DevOps",
                    "description": "D",
                    "estimated_duration_minutes": 45,
                    "lessons": [
                        {
                            "lesson_number": 1,
                            "title": "CI/CD",
                            "content_markdown": "# CI/CD\n\nContenu",
                            "key_takeaways": ["P1"],
                            "practical_exercises": [],
                            "estimated_duration_minutes": 20,
                        }
                    ],
                }
            ],
        }
        agent.llm.generate.return_value = json.dumps(course)

        result = agent.generate_course_from_document(
            document_content="# DevOps\nCeci est un cours",
            target_audience="Devs",
            difficulty="intermediate",
            duration_hours=2,
        )
        assert result["title"] == "Cours depuis PDF"
        assert result["target_audience"] == "Devs"
        assert result["difficulty_level"] == "intermediate"
        assert len(result["modules"]) == 1

    @pytest.mark.unit
    def test_generate_from_document_failure(self, agent):
        agent.llm.generate.return_value = "not json"
        result = agent.generate_course_from_document(
            document_content="Some content",
            target_audience="Devs",
            difficulty="beginner",
            duration_hours=1,
        )
        assert "error" in result

    @pytest.mark.unit
    def test_generate_from_document_with_callback(self, agent):
        course = {
            "title": "Test",
            "description": "D",
            "topic": "T",
            "learning_objectives": [],
            "modules": [],
        }
        agent.llm.generate.return_value = json.dumps(course)
        steps = []

        result = agent.generate_course_from_document(
            document_content="Content here",
            target_audience="All",
            difficulty="beginner",
            duration_hours=1,
            progress_callback=lambda s, d: steps.append((s, d)),
        )
        assert result["title"] == "Test"
        assert len(steps) == 2
        assert steps[0][0] == "analyzing"
        assert steps[1][0] == "done"

    @pytest.mark.unit
    def test_regenerate_with_feedback(self, agent):
        regenerated = {
            "title": "Cours ameliore",
            "description": "Nouvelle desc",
            "learning_objectives": ["Obj ameliore"],
            "modules": [
                {
                    "module_number": 1,
                    "title": "Mod ameliore",
                    "description": "D",
                    "estimated_duration_minutes": 30,
                    "lessons": [
                        {
                            "lesson_number": 1,
                            "title": "L1 amelioree",
                            "content_markdown": "# Better",
                            "key_takeaways": [],
                            "practical_exercises": [],
                            "estimated_duration_minutes": 15,
                        }
                    ],
                }
            ],
        }
        agent.llm.generate.return_value = json.dumps(regenerated)

        result = agent.regenerate_with_feedback(
            {
                "title": "Old",
                "description": "Old desc",
                "topic": "Python",
                "target_audience": "Devs",
                "difficulty_level": "intermediate",
                "duration_hours": 2,
                "learning_objectives": [],
                "modules": [],
            },
            "Plus d'exemples svp",
        )
        assert result["title"] == "Cours ameliore"
        assert result["topic"] == "Python"


# ==================
# QUIZ
# ==================


class TestQuiz:
    @pytest.mark.unit
    def test_generate_quiz(self, agent):
        quiz = {
            "title": "Quiz - Python",
            "questions": [
                {
                    "question_number": 1,
                    "question_type": "mcq",
                    "question_text": "Question?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "explanation": "Parce que B",
                    "difficulty_level": "easy",
                    "bloom_level": "remember",
                },
                {
                    "question_number": 2,
                    "question_type": "true_false",
                    "question_text": "Vrai ou faux?",
                    "options": ["Vrai", "Faux"],
                    "correct_answer": "Vrai",
                    "explanation": "Explication",
                    "difficulty_level": "medium",
                    "bloom_level": "understand",
                },
            ],
        }
        agent.llm.generate.return_value = json.dumps(quiz)

        result = agent.generate_quiz("Python", "# Contenu", "medium", 2)
        assert result["title"] == "Quiz - Python"
        assert len(result["questions"]) == 2

    @pytest.mark.unit
    def test_evaluate_mcq_correct(self, agent):
        question = {
            "question_type": "mcq",
            "correct_answer": "Option B",
            "explanation": "Parce que B",
        }
        result = agent.evaluate_answer(question, "Option B")
        assert result["is_correct"] is True

    @pytest.mark.unit
    def test_evaluate_mcq_wrong(self, agent):
        question = {
            "question_type": "mcq",
            "correct_answer": "Option B",
            "explanation": "Parce que B",
        }
        result = agent.evaluate_answer(question, "Option A")
        assert result["is_correct"] is False

    @pytest.mark.unit
    def test_evaluate_true_false(self, agent):
        question = {
            "question_type": "true_false",
            "correct_answer": "Faux",
            "explanation": "Explication",
        }
        result = agent.evaluate_answer(question, "Faux")
        assert result["is_correct"] is True

    @pytest.mark.unit
    def test_evaluate_fill_blank_correct(self, agent):
        question = {
            "question_type": "fill_blank",
            "correct_answer": "print",
            "explanation": "La fonction print",
        }
        result = agent.evaluate_answer(question, "print")
        assert result["is_correct"] is True

    @pytest.mark.unit
    def test_evaluate_fill_blank_case_insensitive(self, agent):
        question = {
            "question_type": "fill_blank",
            "correct_answer": "Print",
            "explanation": "print()",
        }
        result = agent.evaluate_answer(question, "print")
        assert result["is_correct"] is True

    @pytest.mark.unit
    def test_evaluate_open_ended_llm(self, agent):
        question = {
            "question_type": "open_ended",
            "question_text": "Qu'est-ce qu'une variable?",
            "correct_answer": "Un espace memoire nomme",
            "explanation": "Explication",
        }
        agent.llm.generate.return_value = json.dumps(
            {
                "is_correct": True,
                "score": 0.85,
                "feedback": "Bonne explication!",
                "missing_elements": [],
            }
        )

        result = agent.evaluate_answer(question, "C'est un espace en memoire avec un nom")
        assert result["is_correct"] is True
        assert "Bonne" in result["feedback"]

    @pytest.mark.unit
    def test_evaluate_open_ended_fallback(self, agent):
        question = {
            "question_type": "open_ended",
            "question_text": "Qu'est-ce qu'une variable?",
            "correct_answer": "Un espace memoire nomme",
            "explanation": "Explication",
        }
        agent.llm.generate.side_effect = Exception("API error")

        result = agent.evaluate_answer(question, "Un espace memoire nomme pour stocker")
        assert isinstance(result["is_correct"], bool)


# ==================
# ADAPTIVE DIFFICULTY
# ==================


class TestAdaptiveDifficulty:
    @pytest.mark.unit
    def test_adapt_up(self, agent):
        answers = [
            {"is_correct": True},
            {"is_correct": True},
            {"is_correct": True},
        ]
        assert agent.adapt_difficulty(answers) == "hard"

    @pytest.mark.unit
    def test_adapt_down(self, agent):
        answers = [
            {"is_correct": False},
            {"is_correct": False},
            {"is_correct": False},
        ]
        assert agent.adapt_difficulty(answers) == "easy"

    @pytest.mark.unit
    def test_adapt_no_change(self, agent):
        answers = [
            {"is_correct": True},
            {"is_correct": False},
            {"is_correct": True},
        ]
        assert agent.adapt_difficulty(answers) is None

    @pytest.mark.unit
    def test_adapt_insufficient_data(self, agent):
        answers = [{"is_correct": True}]
        assert agent.adapt_difficulty(answers) is None

    @pytest.mark.unit
    def test_difficulty_distribution_easy(self, agent):
        dist = agent._get_difficulty_distribution("easy", 10)
        assert dist["easy"] >= dist["hard"]
        assert sum(dist.values()) >= 3

    @pytest.mark.unit
    def test_difficulty_distribution_hard(self, agent):
        dist = agent._get_difficulty_distribution("hard", 10)
        assert dist["hard"] >= dist["easy"]

    @pytest.mark.unit
    def test_difficulty_distribution_medium(self, agent):
        dist = agent._get_difficulty_distribution("medium", 10)
        assert dist["medium"] >= dist["easy"]
        assert dist["medium"] >= dist["hard"]


# ==================
# LEARNING PATHS
# ==================


class TestLearningPaths:
    @pytest.mark.unit
    def test_analyze_gaps_empty(self, agent):
        result = agent.analyze_knowledge_gaps(
            [],
            [{"id": 1, "title": "Module 1"}],
        )
        assert len(result["recommended_review"]) == 1

    @pytest.mark.unit
    def test_analyze_gaps_with_results(self, agent):
        gaps = {
            "weak_modules": [
                {
                    "module_id": 1,
                    "title": "Faible",
                    "mastery": 0.3,
                    "reason": "Score bas",
                }
            ],
            "strong_modules": [],
            "recommended_review": [{"module_id": 1, "reason": "Revoir"}],
        }
        agent.llm.generate.return_value = json.dumps(gaps)

        result = agent.analyze_knowledge_gaps(
            [{"quiz_title": "Q1", "score_percentage": 30}],
            [{"id": 1, "title": "M1", "lessons": []}],
        )
        assert len(result["weak_modules"]) == 1

    @pytest.mark.unit
    def test_generate_learning_path(self, agent):
        path = {
            "path_steps": [
                {
                    "step_number": 1,
                    "type": "review",
                    "module_id": 1,
                    "title": "M1",
                    "reason": "Lacune",
                    "estimated_duration_minutes": 30,
                }
            ],
            "recommendations": [
                {
                    "type": "practice",
                    "module_id": 1,
                    "reason": "Pratiquer",
                }
            ],
            "completion_estimate_hours": 2.5,
        }
        agent.llm.generate.return_value = json.dumps(path)

        result = agent.generate_learning_path(
            {"weak_modules": [{"module_id": 1}]},
            ["Maitriser Python"],
            [{"id": 1, "title": "M1", "description": "D"}],
        )
        assert len(result["path_steps"]) == 1
        assert result["completion_estimate_hours"] == 2.5

    @pytest.mark.unit
    def test_generate_learning_path_fallback(self, agent):
        agent.llm.generate.side_effect = Exception("API error")

        result = agent.generate_learning_path(
            {"weak_modules": [], "recommended_review": []},
            ["Goal"],
            [
                {
                    "id": 1,
                    "title": "M1",
                    "description": "D",
                    "estimated_duration_minutes": 60,
                },
                {
                    "id": 2,
                    "title": "M2",
                    "description": "D",
                    "estimated_duration_minutes": 30,
                },
            ],
        )
        assert len(result["path_steps"]) == 2
        assert result["completion_estimate_hours"] == 1.5


# ==================
# MODES
# ==================


class TestModes:
    @pytest.mark.unit
    def test_mode_config_free(self, agent):
        cfg = agent._get_mode_config("free")
        assert cfg["label"] == "Cours libre"
        assert cfg["system_context"] == ""

    @pytest.mark.unit
    def test_mode_config_interview(self, agent):
        cfg = agent._get_mode_config("interview")
        assert cfg["label"] == "Preparation entretien"
        assert "entretien" in cfg["system_context"]
        assert cfg["outline_rules"] != ""
        assert cfg["quiz_rules"] != ""

    @pytest.mark.unit
    def test_mode_config_certification(self, agent):
        cfg = agent._get_mode_config("certification")
        assert cfg["label"] == "Preparation certification"
        assert "certification" in cfg["system_context"]

    @pytest.mark.unit
    def test_mode_config_training(self, agent):
        cfg = agent._get_mode_config("training")
        assert cfg["label"] == "Preparation formation"
        assert "formation" in cfg["system_context"]

    @pytest.mark.unit
    def test_mode_config_unknown_falls_back(self, agent):
        cfg = agent._get_mode_config("unknown")
        assert cfg["label"] == "Cours libre"

    @pytest.mark.unit
    def test_generate_course_with_mode(self, agent):
        outline = {
            "title": "Prep AWS SAA",
            "description": "Certification AWS",
            "learning_objectives": ["Passer l'examen"],
            "modules": [
                {
                    "title": "Mod 1",
                    "description": "D",
                    "estimated_duration_minutes": 30,
                    "lesson_titles": ["L1"],
                }
            ],
        }
        lessons = {
            "lessons": [
                {
                    "lesson_number": 1,
                    "title": "L1",
                    "content_markdown": "# L1",
                    "key_takeaways": ["K1"],
                    "practical_exercises": [],
                    "estimated_duration_minutes": 15,
                }
            ]
        }
        agent.llm.generate.side_effect = [
            json.dumps(outline),
            json.dumps(lessons),
        ]

        result = agent.generate_course(
            "AWS Solutions Architect",
            "Devs",
            "intermediate",
            2,
            mode="certification",
        )
        assert result["title"] == "Prep AWS SAA"
        assert result["mode"] == "certification"

    @pytest.mark.unit
    def test_generate_quiz_with_mode(self, agent):
        quiz = {
            "title": "Quiz entretien",
            "questions": [
                {
                    "question_number": 1,
                    "question_type": "mcq",
                    "question_text": "Question?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "explanation": "Explication",
                    "difficulty_level": "medium",
                    "bloom_level": "apply",
                }
            ],
        }
        agent.llm.generate.return_value = json.dumps(quiz)

        result = agent.generate_quiz(
            "Data Engineer",
            "# Contenu",
            "medium",
            5,
            mode="interview",
        )
        assert result["title"] == "Quiz entretien"

    @pytest.mark.unit
    def test_generate_from_document_with_mode(self, agent):
        course = {
            "title": "Formation Docker",
            "description": "Preparer une formation",
            "topic": "Docker",
            "learning_objectives": ["Animer"],
            "modules": [],
        }
        agent.llm.generate.return_value = json.dumps(course)

        result = agent.generate_course_from_document(
            document_content="# Docker\nContenu",
            target_audience="Formateurs",
            difficulty="intermediate",
            duration_hours=2,
            mode="training",
        )
        assert result["title"] == "Formation Docker"

    @pytest.mark.unit
    def test_mode_prompts_contain_context(self, agent):
        """Verify mode context is passed to LLM calls"""
        outline = {
            "title": "T",
            "description": "D",
            "learning_objectives": [],
            "modules": [],
        }
        agent.llm.generate.return_value = json.dumps(outline)

        agent._generate_outline(
            "Python",
            "Devs",
            "beginner",
            1,
            mode="interview",
        )

        call_args = agent.llm.generate.call_args
        system = call_args.kwargs.get("system_prompt", "") or call_args[1].get("system_prompt", "")
        assert "entretien" in system
