"""
Tests unitaires pour la base de donnees E-learning
"""

import json
import tempfile

import pytest

from utils.elearning_db import ElearningDatabase


@pytest.fixture
def db():
    """Base de donnees temporaire pour les tests"""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        database = ElearningDatabase(db_path=f.name)
        yield database


@pytest.fixture
def sample_course_data():
    """Donnees d'exemple pour un cours"""
    return {
        "title": "Introduction a Python",
        "description": "Cours complet pour debutants",
        "topic": "Python Programming",
        "target_audience": "Debutants en programmation",
        "difficulty_level": "beginner",
        "duration_hours": 3,
        "learning_objectives": [
            "Comprendre les bases de Python",
            "Ecrire des programmes simples",
            "Utiliser les structures de donnees",
        ],
        "modules": [
            {
                "title": "Les bases de Python",
                "description": "Variables, types et operateurs",
                "estimated_duration_minutes": 60,
                "lessons": [
                    {
                        "title": "Variables et types",
                        "content_markdown": "# Variables\n\nUne variable...",
                        "key_takeaways": [
                            "Les variables stockent des donnees",
                            "Python est dynamiquement type",
                        ],
                        "practical_exercises": [
                            {
                                "title": "Exercice 1",
                                "description": "Creer des variables",
                                "hints": ["Utilisez ="],
                            }
                        ],
                        "estimated_duration_minutes": 30,
                    },
                    {
                        "title": "Operateurs",
                        "content_markdown": "# Operateurs\n\nLes operateurs...",
                        "key_takeaways": ["Operateurs arithmetiques"],
                        "practical_exercises": [],
                        "estimated_duration_minutes": 30,
                    },
                ],
            },
            {
                "title": "Structures de controle",
                "description": "If, for, while",
                "estimated_duration_minutes": 60,
                "lessons": [
                    {
                        "title": "Conditions if/else",
                        "content_markdown": "# Conditions\n\nLe if...",
                        "key_takeaways": ["if, elif, else"],
                        "practical_exercises": [],
                        "estimated_duration_minutes": 30,
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_quiz_data():
    """Donnees d'exemple pour un quiz"""
    return {
        "title": "Quiz - Les bases de Python",
        "difficulty_level": "medium",
        "course_id": 1,
        "lesson_id": 1,
        "questions": [
            {
                "question_type": "mcq",
                "question_text": "Quel mot-cle definit une variable en Python?",
                "options": ["var", "let", "aucun mot-cle", "define"],
                "correct_answer": "aucun mot-cle",
                "explanation": "Python n'a pas besoin de mot-cle",
                "difficulty_level": "easy",
                "bloom_level": "remember",
            },
            {
                "question_type": "true_false",
                "question_text": "Python est un langage compile.",
                "options": ["Vrai", "Faux"],
                "correct_answer": "Faux",
                "explanation": "Python est interprete",
                "difficulty_level": "easy",
                "bloom_level": "remember",
            },
            {
                "question_type": "fill_blank",
                "question_text": "La fonction ___ affiche du texte.",
                "options": [],
                "correct_answer": "print",
                "explanation": "print() affiche sur la sortie standard",
                "difficulty_level": "medium",
                "bloom_level": "understand",
            },
            {
                "question_type": "open_ended",
                "question_text": "Expliquez la difference entre une liste et un tuple.",
                "options": [],
                "correct_answer": "Une liste est mutable, un tuple est immutable",
                "explanation": "Les listes peuvent etre modifiees",
                "difficulty_level": "hard",
                "bloom_level": "analyze",
            },
        ],
    }


# ==================
# COURSES
# ==================


class TestCourses:
    @pytest.mark.unit
    def test_save_and_get_course(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        assert course_id > 0

        course = db.get_course(course_id)
        assert course is not None
        assert course["title"] == "Introduction a Python"
        assert course["topic"] == "Python Programming"
        assert course["difficulty_level"] == "beginner"
        assert course["duration_hours"] == 3
        assert len(course["learning_objectives"]) == 3
        assert len(course["modules"]) == 2

    @pytest.mark.unit
    def test_course_modules_and_lessons(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        course = db.get_course(course_id)

        mod1 = course["modules"][0]
        assert mod1["title"] == "Les bases de Python"
        assert mod1["module_number"] == 1
        assert len(mod1["lessons"]) == 2

        lesson1 = mod1["lessons"][0]
        assert lesson1["title"] == "Variables et types"
        assert "# Variables" in lesson1["content_markdown"]
        assert len(lesson1["key_takeaways"]) == 2
        assert len(lesson1["practical_exercises"]) == 1

        mod2 = course["modules"][1]
        assert mod2["title"] == "Structures de controle"
        assert len(mod2["lessons"]) == 1

    @pytest.mark.unit
    def test_get_all_courses(self, db, sample_course_data):
        db.save_course(sample_course_data)
        db.save_course(
            {
                **sample_course_data,
                "title": "Python Avance",
                "difficulty_level": "advanced",
            }
        )

        courses = db.get_all_courses()
        assert len(courses) == 2
        assert courses[0]["modules_count"] > 0
        assert courses[0]["lessons_count"] > 0

    @pytest.mark.unit
    def test_delete_course(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        assert db.delete_course(course_id) is True
        assert db.get_course(course_id) is None

    @pytest.mark.unit
    def test_delete_course_not_found(self, db):
        assert db.delete_course(999) is False

    @pytest.mark.unit
    def test_get_course_not_found(self, db):
        assert db.get_course(999) is None

    @pytest.mark.unit
    def test_update_course(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        updated = db.update_course(
            course_id,
            {
                "title": "Python Modifie",
                "description": "Nouvelle description",
                "learning_objectives": ["Objectif 1"],
            },
        )
        assert updated is True
        course = db.get_course(course_id)
        assert course["title"] == "Python Modifie"
        assert course["description"] == "Nouvelle description"


# ==================
# QUIZZES
# ==================


class TestQuizzes:
    @pytest.mark.unit
    def test_save_and_get_quiz(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None

        quiz_id = db.save_quiz(sample_quiz_data)
        assert quiz_id > 0

        quiz = db.get_quiz(quiz_id)
        assert quiz is not None
        assert quiz["title"] == "Quiz - Les bases de Python"
        assert len(quiz["questions"]) == 4

    @pytest.mark.unit
    def test_quiz_question_types(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None

        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        types = [q["question_type"] for q in quiz["questions"]]
        assert "mcq" in types
        assert "true_false" in types
        assert "fill_blank" in types
        assert "open_ended" in types

        mcq = [q for q in quiz["questions"] if q["question_type"] == "mcq"][0]
        assert len(mcq["options"]) == 4

    @pytest.mark.unit
    def test_get_quiz_not_found(self, db):
        assert db.get_quiz(999) is None

    @pytest.mark.unit
    def test_get_quizzes_for_course(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None

        db.save_quiz(sample_quiz_data)
        db.save_quiz(
            {
                **sample_quiz_data,
                "title": "Quiz 2",
            }
        )

        quizzes = db.get_quizzes_for_course(course_id)
        assert len(quizzes) == 2
        assert quizzes[0]["questions_count"] == 4

    @pytest.mark.unit
    def test_get_questions_by_difficulty(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None

        quiz_id = db.save_quiz(sample_quiz_data)

        easy = db.get_questions_by_difficulty(quiz_id, "easy")
        assert len(easy) == 2

        medium = db.get_questions_by_difficulty(quiz_id, "medium")
        assert len(medium) == 1

        hard = db.get_questions_by_difficulty(quiz_id, "hard")
        assert len(hard) == 1


# ==================
# SESSIONS
# ==================


class TestSessions:
    @pytest.mark.unit
    def test_init_session_new(self, db):
        session = db.init_session("test-123")
        assert session["session_identifier"] == "test-123"
        assert session["id"] > 0

    @pytest.mark.unit
    def test_init_session_existing(self, db):
        s1 = db.init_session("test-123")
        s2 = db.init_session("test-123")
        assert s1["id"] == s2["id"]

    @pytest.mark.unit
    def test_init_session_auto_id(self, db):
        session = db.init_session()
        assert len(session["session_identifier"]) == 8

    @pytest.mark.unit
    def test_get_session(self, db):
        db.init_session("abc-456")
        session = db.get_session("abc-456")
        assert session is not None
        assert session["session_identifier"] == "abc-456"

    @pytest.mark.unit
    def test_get_session_not_found(self, db):
        assert db.get_session("nonexistent") is None


# ==================
# QUIZ ATTEMPTS
# ==================


class TestQuizAttempts:
    @pytest.mark.unit
    def test_create_attempt(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)
        assert attempt_id > 0

    @pytest.mark.unit
    def test_record_answer_correct(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        q_id = quiz["questions"][0]["id"]
        db.record_answer(attempt_id, q_id, "aucun mot-cle", True, 10)

        results = db.get_attempt_results(attempt_id)
        assert results["total_questions"] == 1
        assert results["correct_answers"] == 1
        assert len(results["answers"]) == 1

    @pytest.mark.unit
    def test_record_multiple_answers(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        db.record_answer(
            attempt_id,
            quiz["questions"][0]["id"],
            "aucun mot-cle",
            True,
            10,
        )
        db.record_answer(
            attempt_id,
            quiz["questions"][1]["id"],
            "Vrai",
            False,
            5,
        )
        db.record_answer(
            attempt_id,
            quiz["questions"][2]["id"],
            "print",
            True,
            8,
        )

        results = db.get_attempt_results(attempt_id)
        assert results["total_questions"] == 3
        assert results["correct_answers"] == 2

    @pytest.mark.unit
    def test_complete_attempt(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        db.record_answer(
            attempt_id,
            quiz["questions"][0]["id"],
            "aucun mot-cle",
            True,
            10,
        )
        db.record_answer(
            attempt_id,
            quiz["questions"][1]["id"],
            "Faux",
            True,
            5,
        )

        result = db.complete_attempt(attempt_id)
        assert result["score_percentage"] == 100.0
        assert result["total_questions"] == 2
        assert result["correct_answers"] == 2
        assert result["completed_at"] is not None

    @pytest.mark.unit
    def test_complete_attempt_not_found(self, db):
        result = db.complete_attempt(999)
        assert result == {}

    @pytest.mark.unit
    def test_get_attempt_results_not_found(self, db):
        assert db.get_attempt_results(999) is None

    @pytest.mark.unit
    def test_update_attempt_difficulty(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        db.update_attempt_difficulty(attempt_id, "hard")
        results = db.get_attempt_results(attempt_id)
        assert results["current_difficulty"] == "hard"

    @pytest.mark.unit
    def test_get_recent_answers(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        for i, q in enumerate(quiz["questions"]):
            db.record_answer(
                attempt_id,
                q["id"],
                "answer",
                i % 2 == 0,
                5,
            )

        recent = db.get_recent_answers(attempt_id, limit=3)
        assert len(recent) == 3


# ==================
# LEARNING PATHS
# ==================


class TestLearningPaths:
    @pytest.mark.unit
    def test_save_and_get_learning_path(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        session = db.init_session("student-1")

        path_id = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": ["Maitriser Python", "Creer des scripts"],
                "knowledge_gaps": [
                    {"module_id": 1, "topic": "Variables"},
                ],
                "recommendations": [
                    {"type": "review", "module_id": 1, "reason": "Lacune"},
                ],
            }
        )
        assert path_id > 0

        path = db.get_learning_path(session["id"], course_id)
        assert path is not None
        assert len(path["stated_goals"]) == 2
        assert len(path["knowledge_gaps"]) == 1
        assert len(path["recommendations"]) == 1

    @pytest.mark.unit
    def test_update_existing_learning_path(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        session = db.init_session("student-1")

        path_id1 = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": ["Goal 1"],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        path_id2 = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": ["Goal 1", "Goal 2"],
                "knowledge_gaps": [{"topic": "New gap"}],
                "recommendations": [],
            }
        )

        assert path_id1 == path_id2
        path = db.get_learning_path(session["id"], course_id)
        assert len(path["stated_goals"]) == 2

    @pytest.mark.unit
    def test_get_learning_path_not_found(self, db):
        assert db.get_learning_path(999, 999) is None

    @pytest.mark.unit
    def test_update_module_progress(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        course = db.get_course(course_id)
        session = db.init_session("student-1")

        path_id = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": ["Learn"],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        module_id = course["modules"][0]["id"]
        db.update_module_progress(path_id, module_id, 50.0, "intermediate")

        path = db.get_learning_path(session["id"], course_id)
        assert len(path["module_progress"]) == 1
        assert path["module_progress"][0]["completion_percentage"] == 50.0
        assert path["module_progress"][0]["mastery_level"] == "intermediate"
        assert path["current_progress_percentage"] == 50.0

    @pytest.mark.unit
    def test_update_module_progress_recalculates_overall(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        course = db.get_course(course_id)
        session = db.init_session("student-1")

        path_id = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": [],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        mod1_id = course["modules"][0]["id"]
        mod2_id = course["modules"][1]["id"]

        db.update_module_progress(path_id, mod1_id, 100.0, "expert")
        db.update_module_progress(path_id, mod2_id, 50.0, "intermediate")

        path = db.get_learning_path(session["id"], course_id)
        assert path["current_progress_percentage"] == 75.0

    @pytest.mark.unit
    def test_update_module_progress_upsert(self, db, sample_course_data):
        course_id = db.save_course(sample_course_data)
        course = db.get_course(course_id)
        session = db.init_session("student-1")

        path_id = db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": [],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        module_id = course["modules"][0]["id"]
        db.update_module_progress(path_id, module_id, 30.0, "beginner")
        db.update_module_progress(path_id, module_id, 80.0, "proficient")

        path = db.get_learning_path(session["id"], course_id)
        assert len(path["module_progress"]) == 1
        assert path["module_progress"][0]["completion_percentage"] == 80.0


# ==================
# SESSION QUIZ RESULTS
# ==================


class TestSessionQuizResults:
    @pytest.mark.unit
    def test_get_session_quiz_results(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        quiz_id = db.save_quiz(sample_quiz_data)
        quiz = db.get_quiz(quiz_id)

        session = db.init_session("student-1")
        attempt_id = db.create_attempt(session["id"], quiz_id)

        db.record_answer(
            attempt_id,
            quiz["questions"][0]["id"],
            "aucun mot-cle",
            True,
            10,
        )
        db.complete_attempt(attempt_id)

        results = db.get_session_quiz_results(session["id"], course_id)
        assert len(results) == 1
        assert results[0]["score_percentage"] == 100.0

    @pytest.mark.unit
    def test_get_session_quiz_results_empty(self, db):
        session = db.init_session("student-1")
        results = db.get_session_quiz_results(session["id"], 999)
        assert results == []


# ==================
# CASCADE DELETE
# ==================


class TestCascadeDelete:
    @pytest.mark.unit
    def test_delete_course_cascades(self, db, sample_course_data, sample_quiz_data):
        course_id = db.save_course(sample_course_data)
        sample_quiz_data["course_id"] = course_id
        sample_quiz_data["lesson_id"] = None
        db.save_quiz(sample_quiz_data)

        session = db.init_session("student-1")
        db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": course_id,
                "stated_goals": [],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        db.delete_course(course_id)

        assert db.get_course(course_id) is None
        assert db.get_quizzes_for_course(course_id) == []
        assert db.get_learning_path(session["id"], course_id) is None
