"""
Tests d'integration pour les endpoints API E-learning
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)


@pytest.fixture
def client():
    """Client de test FastAPI"""
    from httpx import ASGITransport, AsyncClient

    from app import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def elearning_db():
    """DB elearning temporaire peuplee"""
    from utils.elearning_db import ElearningDatabase

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = ElearningDatabase(db_path=db_path)

    # Insert sample course
    course_id = db.save_course(
        {
            "title": "Python Test Course",
            "description": "Un cours de test",
            "topic": "Python",
            "target_audience": "Debutants",
            "difficulty_level": "beginner",
            "duration_hours": 2,
            "learning_objectives": ["Obj 1", "Obj 2"],
            "modules": [
                {
                    "title": "Module 1",
                    "description": "Desc mod 1",
                    "estimated_duration_minutes": 60,
                    "lessons": [
                        {
                            "title": "Lecon 1",
                            "content_markdown": "# Lecon 1\n\nContenu",
                            "key_takeaways": ["Point 1"],
                            "practical_exercises": [],
                            "estimated_duration_minutes": 30,
                        },
                    ],
                },
            ],
        }
    )

    # Insert sample quiz
    quiz_id = db.save_quiz(
        {
            "title": "Quiz Test",
            "difficulty_level": "medium",
            "course_id": course_id,
            "lesson_id": None,
            "questions": [
                {
                    "question_type": "mcq",
                    "question_text": "Q1?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "explanation": "Explication",
                    "difficulty_level": "easy",
                    "bloom_level": "remember",
                },
                {
                    "question_type": "true_false",
                    "question_text": "Q2?",
                    "options": ["Vrai", "Faux"],
                    "correct_answer": "Vrai",
                    "explanation": "Explication",
                    "difficulty_level": "medium",
                    "bloom_level": "understand",
                },
            ],
        }
    )

    # Init session
    db.init_session("test-session-123")

    yield db

    os.unlink(db_path)


HEADERS = {"origin": "http://test"}


class TestElearningPage:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_page_loads(self, client):
        response = await client.get("/elearning", headers=HEADERS)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_page_contains_tabs(self, client):
        response = await client.get("/elearning", headers=HEADERS)
        assert "Generation" in response.text
        assert "Bibliotheque" in response.text
        assert "Quiz Adaptatif" in response.text
        assert "Parcours" in response.text


class TestSessionInit:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_init(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/session/init",
                json={"session_identifier": "new-session"},
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["session_identifier"] == "new-session"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_init_existing(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/session/init",
                json={"session_identifier": "test-session-123"},
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["session_identifier"] == "test-session-123"


class TestCoursesCRUD:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_courses(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/courses",
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
        assert len(data["courses"]) == 1
        assert data["courses"][0]["title"] == "Python Test Course"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_course(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/course/1",
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["course"]["title"] == "Python Test Course"
        assert len(data["course"]["modules"]) == 1
        assert len(data["course"]["modules"][0]["lessons"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_course_not_found(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/course/999",
                headers=HEADERS,
            )
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_course(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.delete(
                "/api/elearning/course/1",
                headers=HEADERS,
            )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_course_not_found(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.delete(
                "/api/elearning/course/999",
                headers=HEADERS,
            )
        assert response.status_code == 404


class TestQuizEndpoints:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_quizzes(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/quizzes/1",
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "quizzes" in data
        assert len(data["quizzes"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quiz_start(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/quiz/start",
                data={
                    "quiz_id": 1,
                    "session_identifier": "test-session-123",
                },
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "attempt_id" in data
        assert data["total_questions"] == 2
        assert data["first_question"] is not None
        # correct_answer should be stripped
        assert "correct_answer" not in data["first_question"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quiz_start_not_found(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/quiz/start",
                data={
                    "quiz_id": 999,
                    "session_identifier": "test-session-123",
                },
                headers=HEADERS,
            )
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quiz_answer_flow(self, client, elearning_db):
        """Test full quiz answer flow"""
        with patch("routers.elearning.elearning_db", elearning_db):
            # Start quiz
            start_resp = await client.post(
                "/api/elearning/quiz/start",
                data={
                    "quiz_id": 1,
                    "session_identifier": "test-session-123",
                },
                headers=HEADERS,
            )
            data = start_resp.json()
            attempt_id = data["attempt_id"]
            q = data["first_question"]

            # Submit answer (mock the agent for open-ended)
            with patch("routers.elearning.ElearningAgent") as mock_agent_cls:
                mock_agent = MagicMock()
                mock_agent.evaluate_answer.return_value = {
                    "is_correct": True,
                    "explanation": "Bonne reponse",
                    "feedback": "Bravo!",
                }
                mock_agent.adapt_difficulty.return_value = None
                mock_agent_cls.return_value = mock_agent

                answer_resp = await client.post(
                    "/api/elearning/quiz/answer",
                    data={
                        "attempt_id": attempt_id,
                        "question_id": q["id"],
                        "answer": "B",
                        "time_spent": 10,
                    },
                    headers=HEADERS,
                )

            assert answer_resp.status_code == 200
            answer_data = answer_resp.json()
            assert "is_correct" in answer_data
            assert "next_question" in answer_data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quiz_results(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            # Start and complete a quiz
            start_resp = await client.post(
                "/api/elearning/quiz/start",
                data={
                    "quiz_id": 1,
                    "session_identifier": "test-session-123",
                },
                headers=HEADERS,
            )
            attempt_id = start_resp.json()["attempt_id"]

            # Get results
            results_resp = await client.get(
                f"/api/elearning/quiz/results/{attempt_id}",
                headers=HEADERS,
            )
        assert results_resp.status_code == 200
        data = results_resp.json()
        assert "results" in data


class TestLearningPathEndpoints:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_learning_path_not_found(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/learning-path" "/test-session-123/1",
                headers=HEADERS,
            )
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_learning_path_exists(self, client, elearning_db):
        # Create a learning path first
        session = elearning_db.get_session("test-session-123")
        elearning_db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": 1,
                "stated_goals": ["Learn Python"],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )

        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.get(
                "/api/elearning/learning-path" "/test-session-123/1",
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert data["path"]["stated_goals"] == ["Learn Python"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_progress(self, client, elearning_db):
        session = elearning_db.get_session("test-session-123")
        path_id = elearning_db.save_learning_path(
            {
                "session_id": session["id"],
                "course_id": 1,
                "stated_goals": [],
                "knowledge_gaps": [],
                "recommendations": [],
            }
        )
        course = elearning_db.get_course(1)
        module_id = course["modules"][0]["id"]

        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/learning-path" "/update-progress",
                data={
                    "learning_path_id": path_id,
                    "module_id": module_id,
                    "completion_pct": 75.0,
                    "mastery_level": "intermediate",
                },
                headers=HEADERS,
            )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_progress_invalid_mastery(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/learning-path" "/update-progress",
                data={
                    "learning_path_id": 1,
                    "module_id": 1,
                    "completion_pct": 50.0,
                    "mastery_level": "invalid_level",
                },
                headers=HEADERS,
            )
        assert response.status_code == 400


class TestCourseGeneration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_invalid_difficulty(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/course/generate",
                data={
                    "topic": "Python",
                    "target_audience": "Debutants",
                    "difficulty": "invalid",
                    "duration_hours": 3,
                },
                headers=HEADERS,
            )
        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_returns_job_id(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/course/generate",
                data={
                    "topic": "Python",
                    "target_audience": "Debutants",
                    "difficulty": "beginner",
                    "duration_hours": 2,
                },
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_from_document(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/course/generate",
                data={
                    "document_content": "# Python\nCeci est un cours",
                    "target_audience": "Debutants",
                    "difficulty": "beginner",
                    "duration_hours": 2,
                },
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_generate_no_topic_no_document(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db), patch("routers.shared.limiter.enabled", False):
            response = await client.post(
                "/api/elearning/course/generate",
                data={
                    "target_audience": "Debutants",
                    "difficulty": "beginner",
                    "duration_hours": 2,
                },
                headers=HEADERS,
            )
        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_document_txt(self, client, elearning_db):
        import io

        txt_content = b"# Formation Python\nContenu du cours"
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/course/upload-document",
                files={
                    "file": ("test.md", io.BytesIO(txt_content), "text/markdown"),
                },
                headers=HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "Formation Python" in data["text"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_document_unsupported(self, client, elearning_db):
        import io

        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/course/upload-document",
                files={
                    "file": ("test.xyz", io.BytesIO(b"data"), "application/octet-stream"),
                },
                headers=HEADERS,
            )
        assert response.status_code in (400, 500)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quiz_generate_invalid_difficulty(self, client, elearning_db):
        with patch("routers.elearning.elearning_db", elearning_db):
            response = await client.post(
                "/api/elearning/quiz/generate",
                data={
                    "course_id": 1,
                    "difficulty": "invalid",
                },
                headers=HEADERS,
            )
        assert response.status_code == 400
