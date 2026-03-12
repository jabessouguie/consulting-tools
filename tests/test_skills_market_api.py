"""
Tests d'integration pour les endpoints API du Skills Market
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """Client de test FastAPI"""
    from httpx import ASGITransport, AsyncClient

    from app import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def populated_db():
    """DB peuplee avec des donnees de test"""
    from utils.consultant_db import ConsultantDatabase

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = ConsultantDatabase(db_path=db_path)
    db.save_consultant(
        {
            "name": "Alice Test",
            "title": "Consultante Senior Data",
            "bio": "Experte en data science",
            "skills_technical": [
                {"name": "Python", "level": "expert"},
                {"name": "SQL", "level": "senior"},
            ],
            "skills_sector": [
                {"name": "Banque", "level": "expert"},
            ],
            "missions": [
                {
                    "client_name": "TestBank",
                    "context_and_challenges": "Migration cloud",
                    "deliverables": "Architecture",
                    "tasks": "Cadrage",
                }
            ],
            "interests": ["IA", "Sport"],
        }
    )
    db.save_consultant(
        {
            "name": "Bob Test",
            "title": "Manager Consulting",
            "bio": "Expert en strategie",
            "skills_technical": [
                {"name": "Agile", "level": "expert"},
            ],
            "skills_sector": [
                {"name": "Assurance", "level": "senior"},
            ],
            "missions": [],
            "interests": ["Innovation"],
        }
    )

    yield db

    os.unlink(db_path)


class TestSkillsMarketPage:
    """Tests de la page Skills Market"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_page_loads(self, client):
        """La page /skills-market se charge"""
        response = await client.get(
            "/skills-market",
            headers={"origin": "http://test"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_page_is_html(self, client):
        """La page retourne du HTML"""
        response = await client.get(
            "/skills-market",
            headers={"origin": "http://test"},
        )
        assert "text/html" in response.headers.get("content-type", "")


class TestImportStatus:
    """Tests du statut d'import"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_import_status(self, client):
        """Le statut d'import retourne un JSON valide"""
        response = await client.get(
            "/api/skills-market/import/status",
            headers={"origin": "http://test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "imported" in data
        assert "count" in data
        assert isinstance(data["imported"], bool)


class TestConsultantsList:
    """Tests de la liste des consultants"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_consultants(self, client, populated_db):
        """Liste des consultants"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "consultants" in data
        assert len(data["consultants"]) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_filter_technical(self, client, populated_db):
        """Filtre par competence technique"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants?technical=Python",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data["consultants"]) == 1
        assert data["consultants"][0]["name"] == "Alice Test"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_filter_sector(self, client, populated_db):
        """Filtre par expertise sectorielle"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants?sector=Assurance",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data["consultants"]) == 1
        assert data["consultants"][0]["name"] == "Bob Test"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_filter_no_match(self, client, populated_db):
        """Filtre sans resultats"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants" "?technical=Blockchain",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data["consultants"]) == 0


class TestConsultantDetail:
    """Tests du detail consultant"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_consultant(self, client, populated_db):
        """Recuperation d'un consultant"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants/1",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "consultant" in data
        assert data["consultant"]["name"] == "Alice Test"
        assert "skills_technical" in data["consultant"]
        assert "missions" in data["consultant"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client, populated_db):
        """Consultant inexistant retourne 404"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/consultants/999",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 404


class TestSkillsList:
    """Tests de la liste des competences"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_skills(self, client, populated_db):
        """Liste des competences groupees"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.get(
                "/api/skills-market/skills",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "technical" in data
        assert "sector" in data
        assert "Python" in data["technical"]
        assert "Banque" in data["sector"]


class TestAddMission:
    """Tests d'ajout de mission"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_mission(self, client, populated_db):
        """Ajout d'une mission"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/consultants/1/missions",
                json={
                    "client_name": "EDF",
                    "context_and_challenges": "Transition",
                    "deliverables": "Rapport",
                    "tasks": "Analyse",
                },
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "mission_id" in data

        # Verify mission was added
        consultant = populated_db.get_consultant(1)
        assert len(consultant["missions"]) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_mission_no_client(self, client, populated_db):
        """Ajout de mission sans client retourne 400"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/consultants/1/missions",
                json={"context_and_challenges": "Test"},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 400


class TestUpdateInterests:
    """Tests de mise a jour des interets"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_interests(self, client, populated_db):
        """Mise a jour des centres d'interet"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.put(
                "/api/skills-market/consultants/1/interests",
                json={"interests": ["Blockchain", "Piano"]},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200

        # Verify interests were updated
        consultant = populated_db.get_consultant(1)
        names = {i["name"] for i in consultant["interests"]}
        assert names == {"Blockchain", "Piano"}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_interests_invalid(self, client, populated_db):
        """Interets invalides retourne 400"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.put(
                "/api/skills-market/consultants/1/interests",
                json={"interests": "not a list"},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 400


class TestNLSearch:
    """Tests de la recherche en langage naturel"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_empty_query(self, client, populated_db):
        """Requete vide retourne 400"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/search",
                json={"query": ""},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_with_mock_llm(self, client, populated_db):
        """Recherche NL avec LLM mocke"""
        mock_results = [
            {
                "id": 1,
                "score": 90,
                "explanation": "Expertise Python",
            }
        ]

        with patch("routers.skills_market.skills_market_db", populated_db), patch(
            "routers.skills_market.SkillsMarketAgent"
        ) as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.natural_language_search.return_value = mock_results
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/skills-market/search",
                json={"query": "expert Python data"},
                headers={"origin": "http://test"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Alice Test"
        assert data["results"][0]["score"] == 90


class TestUploadCV:
    """Tests de l'upload de CV multi-format"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client):
        """Format non supporte retourne 400"""
        response = await client.post(
            "/api/skills-market/upload",
            files={"file": ("test.docx", b"content", "application/octet-stream")},
            headers={"origin": "http://test"},
        )
        assert response.status_code == 400
        assert "Format non supporte" in response.json()["error"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_pdf_returns_job(self, client, populated_db):
        """Upload PDF lance un job"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/upload",
                files={
                    "file": (
                        "cv_test.pdf",
                        b"%PDF-1.4 fake content",
                        "application/pdf",
                    )
                },
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_html_returns_job(self, client, populated_db):
        """Upload HTML lance un job"""
        html_content = (
            b"<html><body><h1>Jean Test</h1>" b"<p>Consultant Senior Python</p></body></html>"
        )
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/upload",
                files={
                    "file": (
                        "cv.html",
                        html_content,
                        "text/html",
                    )
                },
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_pptx_returns_job(self, client, populated_db):
        """Upload PPTX lance un job"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/upload",
                files={
                    "file": (
                        "cv.pptx",
                        b"PK\x03\x04 fake pptx",
                        "application/vnd.openxmlformats",
                    )
                },
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestCertifications:
    """Tests des certifications via API"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_certification(self, client, populated_db):
        """Ajout d'une certification"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/consultants/1" "/certifications",
                json={
                    "name": "AWS Solutions Architect",
                    "organization": "Amazon",
                    "skills_technical": [{"name": "AWS"}],
                },
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "certification_id" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_certification_no_name(self, client, populated_db):
        """Certification sans nom retourne 400"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.post(
                "/api/skills-market/consultants/1" "/certifications",
                json={"organization": "Test"},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 400


class TestDisinterests:
    """Tests des desinterets via API"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_disinterests(self, client, populated_db):
        """Mise a jour des desinterets"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.put(
                "/api/skills-market/consultants/1" "/disinterests",
                json={"disinterests": ["Admin", "Compta"]},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200

        consultant = populated_db.get_consultant(1)
        names = {d["name"] for d in consultant["disinterests"]}
        assert names == {"Admin", "Compta"}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_disinterests_invalid(self, client, populated_db):
        """Desinterets invalides retourne 400"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.put(
                "/api/skills-market/consultants/1" "/disinterests",
                json={"disinterests": "not a list"},
                headers={"origin": "http://test"},
            )
        assert response.status_code == 400


class TestDeleteConsultant:
    """Tests de suppression consultant via API"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_consultant(self, client, populated_db):
        """Suppression d'un consultant"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.delete(
                "/api/skills-market/consultants/1",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client, populated_db):
        """Suppression consultant inexistant"""
        with patch("routers.skills_market.skills_market_db", populated_db):
            response = await client.delete(
                "/api/skills-market/consultants/999",
                headers={"origin": "http://test"},
            )
        assert response.status_code == 404
