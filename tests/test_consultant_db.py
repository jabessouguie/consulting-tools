"""
Tests unitaires pour ConsultantDatabase (Market of Skills)
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.consultant_db import ConsultantDatabase


@pytest.fixture
def db():
    """Cree une base de donnees temporaire pour les tests"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = ConsultantDatabase(db_path=db_path)
    yield database
    os.unlink(db_path)


@pytest.fixture
def sample_consultant():
    """Donnees d'un consultant exemple"""
    return {
        "name": "Jean Dupont",
        "title": "Senior Consultant Data & IA",
        "email": "jean.dupont@consulting-tools.com",
        "bio": "Expert en transformation digitale et IA",
        "raw_pptx_text": "Texte brut du slide PPTX",
        "skills_technical": [
            {"name": "Python", "level": "expert"},
            {"name": "Machine Learning", "level": "senior"},
            {"name": "Product Owner", "level": "confirmed"},
        ],
        "skills_sector": [
            {"name": "Banque", "level": "expert"},
            {"name": "Industrie", "level": "senior"},
        ],
        "missions": [
            {
                "client_name": "BNP Paribas",
                "context_and_challenges": "Migration cloud",
                "deliverables": "Architecture cible, roadmap",
                "tasks": "Audit, cadrage, POC",
            },
            {
                "client_name": "Total",
                "context_and_challenges": "Industrialisation IA",
                "deliverables": "Pipeline MLOps",
                "tasks": "Setup infra, CI/CD, monitoring",
            },
        ],
        "interests": ["GenAI", "Gouvernance data", "Sport"],
        "strengths": ["Leadership technique", "Communication"],
        "improvement_areas": ["Delegation", "Prise de parole en public"],
        "management_suggestions": "Proposer des formations en prise de parole",
    }


@pytest.fixture
def second_consultant():
    """Deuxieme consultant exemple"""
    return {
        "name": "Marie Martin",
        "title": "Manager Consulting",
        "bio": "Experte en strategie et conduite du changement",
        "skills_technical": [
            {"name": "Agile", "level": "expert"},
            {"name": "Product Owner", "level": "expert"},
        ],
        "skills_sector": [
            {"name": "Assurance", "level": "senior"},
            {"name": "Industrie", "level": "confirmed"},
        ],
        "missions": [
            {
                "client_name": "AXA",
                "context_and_challenges": "Transformation agile",
                "deliverables": "Framework agile",
                "tasks": "Coaching, formation",
            },
        ],
        "interests": ["Innovation", "Management"],
    }


class TestDatabaseInit:
    """Tests d'initialisation de la base de donnees"""

    @pytest.mark.unit
    def test_database_creation(self, db):
        """La base de donnees est creee correctement"""
        assert db is not None
        assert os.path.exists(db.db_path)

    @pytest.mark.unit
    def test_tables_exist(self, db):
        """Toutes les tables sont creees"""
        import sqlite3

        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

        assert "consultants" in tables
        assert "skills" in tables
        assert "missions" in tables
        assert "interests" in tables

    @pytest.mark.unit
    def test_empty_database(self, db):
        """La base de donnees est vide a la creation"""
        assert not db.is_imported()
        assert db.get_consultant_count() == 0


class TestSaveAndGetConsultant:
    """Tests de sauvegarde et recuperation de consultants"""

    @pytest.mark.unit
    def test_save_consultant(self, db, sample_consultant):
        """Sauvegarde d'un consultant"""
        consultant_id = db.save_consultant(sample_consultant)
        assert consultant_id > 0

    @pytest.mark.unit
    def test_get_consultant(self, db, sample_consultant):
        """Recuperation d'un consultant complet"""
        consultant_id = db.save_consultant(sample_consultant)
        consultant = db.get_consultant(consultant_id)

        assert consultant is not None
        assert consultant["name"] == "Jean Dupont"
        assert consultant["title"] == "Senior Consultant Data & IA"
        assert consultant["bio"] == "Expert en transformation digitale et IA"

    @pytest.mark.unit
    def test_get_consultant_skills(self, db, sample_consultant):
        """Recuperation des competences"""
        consultant_id = db.save_consultant(sample_consultant)
        consultant = db.get_consultant(consultant_id)

        assert len(consultant["skills_technical"]) == 3
        assert len(consultant["skills_sector"]) == 2

        tech_names = {s["name"] for s in consultant["skills_technical"]}
        assert "Python" in tech_names
        assert "Machine Learning" in tech_names

    @pytest.mark.unit
    def test_get_consultant_missions(self, db, sample_consultant):
        """Recuperation des missions"""
        consultant_id = db.save_consultant(sample_consultant)
        consultant = db.get_consultant(consultant_id)

        assert len(consultant["missions"]) == 2
        client_names = {m["client_name"] for m in consultant["missions"]}
        assert "BNP Paribas" in client_names
        assert "Total" in client_names

    @pytest.mark.unit
    def test_get_consultant_interests(self, db, sample_consultant):
        """Recuperation des centres d'interet"""
        consultant_id = db.save_consultant(sample_consultant)
        consultant = db.get_consultant(consultant_id)

        assert len(consultant["interests"]) == 3
        interest_names = {i["name"] for i in consultant["interests"]}
        assert "GenAI" in interest_names

    @pytest.mark.unit
    def test_get_consultant_strengths(self, db, sample_consultant):
        """Recuperation des points forts"""
        consultant_id = db.save_consultant(sample_consultant)
        consultant = db.get_consultant(consultant_id)

        assert "Leadership technique" in consultant["strengths"]
        assert "Communication" in consultant["strengths"]

    @pytest.mark.unit
    def test_get_nonexistent_consultant(self, db):
        """Consultant inexistant retourne None"""
        result = db.get_consultant(999)
        assert result is None

    @pytest.mark.unit
    def test_duplicate_consultant_update(self, db, sample_consultant):
        """Un consultant avec le meme nom est mis a jour"""
        db.save_consultant(sample_consultant)

        updated = sample_consultant.copy()
        updated["title"] = "Director Data & IA"
        updated["skills_technical"] = [{"name": "Rust", "level": "junior"}]
        db.save_consultant(updated)

        # Should still have 1 consultant
        assert db.get_consultant_count() == 1

        # Should have updated data
        consultants = db.get_all_consultants()
        assert consultants[0]["title"] == "Director Data & IA"

    @pytest.mark.unit
    def test_is_imported_after_save(self, db, sample_consultant):
        """is_imported retourne True apres sauvegarde"""
        db.save_consultant(sample_consultant)
        assert db.is_imported()


class TestGetAllConsultants:
    """Tests de liste de consultants"""

    @pytest.mark.unit
    def test_get_all_empty(self, db):
        """Liste vide sans consultants"""
        result = db.get_all_consultants()
        assert result == []

    @pytest.mark.unit
    def test_get_all_with_data(self, db, sample_consultant, second_consultant):
        """Liste avec plusieurs consultants"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.get_all_consultants()
        assert len(result) == 2

        names = {c["name"] for c in result}
        assert "Jean Dupont" in names
        assert "Marie Martin" in names

    @pytest.mark.unit
    def test_get_all_has_counts(self, db, sample_consultant):
        """La liste inclut les compteurs skills/missions"""
        db.save_consultant(sample_consultant)
        result = db.get_all_consultants()

        assert result[0]["skills_count"] == 5  # 3 tech + 2 sector
        assert result[0]["missions_count"] == 2

    @pytest.mark.unit
    def test_get_all_has_top_skills(self, db, sample_consultant):
        """La liste inclut les top skills"""
        db.save_consultant(sample_consultant)
        result = db.get_all_consultants()

        assert "top_skills" in result[0]
        assert len(result[0]["top_skills"]) > 0


class TestSearchBySkills:
    """Tests de recherche par competences"""

    @pytest.mark.unit
    def test_search_technical(self, db, sample_consultant, second_consultant):
        """Recherche par competence technique"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.search_by_skills(technical=["Python"])
        assert len(result) == 1
        assert result[0]["name"] == "Jean Dupont"

    @pytest.mark.unit
    def test_search_sector(self, db, sample_consultant, second_consultant):
        """Recherche par competence sectorielle"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.search_by_skills(sector=["Assurance"])
        assert len(result) == 1
        assert result[0]["name"] == "Marie Martin"

    @pytest.mark.unit
    def test_search_common_skill(self, db, sample_consultant, second_consultant):
        """Recherche par competence partagee"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        # Both have "Industrie" sector skill
        result = db.search_by_skills(sector=["Industrie"])
        assert len(result) == 2

    @pytest.mark.unit
    def test_search_combined(self, db, sample_consultant, second_consultant):
        """Recherche combinee technique + sectorielle"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.search_by_skills(technical=["Product Owner"], sector=["Industrie"])
        assert len(result) == 2

    @pytest.mark.unit
    def test_search_no_match(self, db, sample_consultant):
        """Recherche sans resultats"""
        db.save_consultant(sample_consultant)

        result = db.search_by_skills(technical=["Blockchain"])
        assert len(result) == 0

    @pytest.mark.unit
    def test_search_case_insensitive(self, db, sample_consultant):
        """Recherche insensible a la casse"""
        db.save_consultant(sample_consultant)

        result = db.search_by_skills(technical=["python"])
        assert len(result) == 1

    @pytest.mark.unit
    def test_search_empty_filters(self, db, sample_consultant, second_consultant):
        """Recherche sans filtres retourne tout"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.search_by_skills()
        assert len(result) == 2


class TestMissions:
    """Tests de gestion des missions"""

    @pytest.mark.unit
    def test_add_mission(self, db, sample_consultant):
        """Ajout d'une nouvelle mission"""
        consultant_id = db.save_consultant(sample_consultant)

        mission_id = db.add_mission(
            consultant_id,
            {
                "client_name": "EDF",
                "context_and_challenges": "Transition energetique",
                "deliverables": "Rapport strategie",
                "tasks": "Analyse, recommandations",
            },
        )
        assert mission_id > 0

        consultant = db.get_consultant(consultant_id)
        assert len(consultant["missions"]) == 3

    @pytest.mark.unit
    def test_mission_fields(self, db, sample_consultant):
        """Verification des champs de mission"""
        consultant_id = db.save_consultant(sample_consultant)

        db.add_mission(
            consultant_id,
            {
                "client_name": "EDF",
                "context_and_challenges": "Transition",
                "deliverables": "Rapport",
                "tasks": "Analyse",
                "start_date": "2025-01",
                "end_date": "2025-06",
            },
        )

        consultant = db.get_consultant(consultant_id)
        edf_mission = next(m for m in consultant["missions"] if m["client_name"] == "EDF")
        assert edf_mission["context_and_challenges"] == "Transition"
        assert edf_mission["start_date"] == "2025-01"


class TestInterests:
    """Tests de gestion des centres d'interet"""

    @pytest.mark.unit
    def test_update_interests(self, db, sample_consultant):
        """Mise a jour des centres d'interet"""
        consultant_id = db.save_consultant(sample_consultant)

        db.update_interests(consultant_id, ["Blockchain", "Sustainability", "Piano"])

        consultant = db.get_consultant(consultant_id)
        interest_names = {i["name"] for i in consultant["interests"]}
        assert interest_names == {"Blockchain", "Sustainability", "Piano"}

    @pytest.mark.unit
    def test_update_interests_replaces(self, db, sample_consultant):
        """La mise a jour remplace les anciens interets"""
        consultant_id = db.save_consultant(sample_consultant)

        # Original: GenAI, Gouvernance data, Sport
        db.update_interests(consultant_id, ["NewInterest"])

        consultant = db.get_consultant(consultant_id)
        assert len(consultant["interests"]) == 1
        assert consultant["interests"][0]["name"] == "NewInterest"

    @pytest.mark.unit
    def test_update_interests_empty(self, db, sample_consultant):
        """Vider les centres d'interet"""
        consultant_id = db.save_consultant(sample_consultant)

        db.update_interests(consultant_id, [])

        consultant = db.get_consultant(consultant_id)
        assert len(consultant["interests"]) == 0

    @pytest.mark.unit
    def test_update_interests_strips_whitespace(self, db, sample_consultant):
        """Les espaces sont supprimes"""
        consultant_id = db.save_consultant(sample_consultant)

        db.update_interests(consultant_id, ["  AI  ", " Sport ", ""])

        consultant = db.get_consultant(consultant_id)
        interest_names = {i["name"] for i in consultant["interests"]}
        assert interest_names == {"AI", "Sport"}


class TestGetAllSkills:
    """Tests de recuperation des competences uniques"""

    @pytest.mark.unit
    def test_get_all_skills_empty(self, db):
        """Competences vides"""
        result = db.get_all_skills()
        assert result == {"technical": [], "sector": []}

    @pytest.mark.unit
    def test_get_all_skills_grouped(self, db, sample_consultant, second_consultant):
        """Competences groupees par categorie"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.get_all_skills()

        assert "Python" in result["technical"]
        assert "Machine Learning" in result["technical"]
        assert "Agile" in result["technical"]
        assert "Banque" in result["sector"]
        assert "Assurance" in result["sector"]

    @pytest.mark.unit
    def test_get_all_skills_unique(self, db, sample_consultant, second_consultant):
        """Les competences sont uniques (pas de doublons)"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.get_all_skills()

        # "Product Owner" and "Industrie" appear in both consultants
        assert result["technical"].count("Product Owner") == 1
        assert result["sector"].count("Industrie") == 1


class TestFulltextSearch:
    """Tests de recherche textuelle"""

    @pytest.mark.unit
    def test_search_by_name(self, db, sample_consultant, second_consultant):
        """Recherche par nom"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)

        result = db.search_fulltext("Dupont")
        assert len(result) == 1
        assert result[0]["name"] == "Jean Dupont"

    @pytest.mark.unit
    def test_search_by_skill_name(self, db, sample_consultant):
        """Recherche par nom de competence"""
        db.save_consultant(sample_consultant)

        result = db.search_fulltext("Machine Learning")
        assert len(result) == 1

    @pytest.mark.unit
    def test_search_by_client(self, db, sample_consultant):
        """Recherche par nom de client"""
        db.save_consultant(sample_consultant)

        result = db.search_fulltext("BNP")
        assert len(result) == 1

    @pytest.mark.unit
    def test_search_no_match(self, db, sample_consultant):
        """Recherche sans resultats"""
        db.save_consultant(sample_consultant)

        result = db.search_fulltext("XYZNOTFOUND")
        assert len(result) == 0


class TestDeleteAndAnalysis:
    """Tests de suppression et analyse"""

    @pytest.mark.unit
    def test_delete_all(self, db, sample_consultant, second_consultant):
        """Suppression de toutes les donnees"""
        db.save_consultant(sample_consultant)
        db.save_consultant(second_consultant)
        assert db.get_consultant_count() == 2

        db.delete_all()
        assert db.get_consultant_count() == 0
        assert not db.is_imported()

    @pytest.mark.unit
    def test_update_analysis(self, db, sample_consultant):
        """Mise a jour de l'analyse forces/faiblesses"""
        consultant_id = db.save_consultant(sample_consultant)

        db.update_consultant_analysis(
            consultant_id,
            strengths=["Expertise IA", "Autonomie"],
            improvement_areas=["Gestion du temps"],
            management_suggestions="Coaching individuel recommande",
        )

        consultant = db.get_consultant(consultant_id)
        assert "Expertise IA" in consultant["strengths"]
        assert "Gestion du temps" in consultant["improvement_areas"]
        assert "Coaching" in consultant["management_suggestions"]


class TestCertifications:
    """Tests des certifications"""

    @pytest.mark.unit
    def test_add_certification(self, db, sample_consultant):
        """Ajout d'une certification"""
        cid = db.save_consultant(sample_consultant)

        cert_id = db.add_certification(
            cid,
            {
                "name": "AWS Solutions Architect",
                "organization": "Amazon",
                "date_obtained": "2025-01-15",
                "description": "Cloud architecture cert",
            },
        )

        assert cert_id is not None
        consultant = db.get_consultant(cid)
        assert len(consultant["certifications"]) == 1
        assert consultant["certifications"][0]["name"] == ("AWS Solutions Architect")

    @pytest.mark.unit
    def test_certification_updates_skills(self, db, sample_consultant):
        """Certification met a jour les competences"""
        cid = db.save_consultant(sample_consultant)

        db.add_certification(
            cid,
            {
                "name": "Scrum Master",
                "organization": "Scrum.org",
                "skills_technical": [{"name": "Scrum", "level": "expert"}],
                "skills_sector": [{"name": "Conseil", "level": "senior"}],
            },
        )

        consultant = db.get_consultant(cid)
        tech_names = [s["name"] for s in consultant["skills_technical"]]
        sector_names = [s["name"] for s in consultant["skills_sector"]]
        assert "Scrum" in tech_names
        assert "Conseil" in sector_names


class TestDisinterests:
    """Tests des centres de desinteret"""

    @pytest.mark.unit
    def test_update_disinterests(self, db, sample_consultant):
        """Mise a jour des desinterets"""
        cid = db.save_consultant(sample_consultant)

        db.update_disinterests(cid, ["Admin", "Compta"])

        consultant = db.get_consultant(cid)
        names = {d["name"] for d in consultant["disinterests"]}
        assert names == {"Admin", "Compta"}

    @pytest.mark.unit
    def test_replace_disinterests(self, db, sample_consultant):
        """Remplacement des desinterets"""
        cid = db.save_consultant(sample_consultant)

        db.update_disinterests(cid, ["Admin"])
        db.update_disinterests(cid, ["Juridique", "RH"])

        consultant = db.get_consultant(cid)
        names = {d["name"] for d in consultant["disinterests"]}
        assert names == {"Juridique", "RH"}


class TestAddSkill:
    """Tests d'ajout de competence"""

    @pytest.mark.unit
    def test_add_new_skill(self, db, sample_consultant):
        """Ajout d'une nouvelle competence"""
        cid = db.save_consultant(sample_consultant)
        db.add_skill(cid, {"name": "Docker"}, "technical")

        consultant = db.get_consultant(cid)
        tech_names = [s["name"] for s in consultant["skills_technical"]]
        assert "Docker" in tech_names

    @pytest.mark.unit
    def test_no_duplicate_skill(self, db, sample_consultant):
        """Pas de doublon de competence"""
        cid = db.save_consultant(sample_consultant)
        db.add_skill(cid, {"name": "Python"}, "technical")

        consultant = db.get_consultant(cid)
        python_count = sum(1 for s in consultant["skills_technical"] if s["name"] == "Python")
        assert python_count == 1

    @pytest.mark.unit
    def test_mission_updates_skills(self, db, sample_consultant):
        """L'ajout de mission met a jour les competences"""
        cid = db.save_consultant(sample_consultant)

        db.add_mission(
            cid,
            {
                "client_name": "TotalEnergies",
                "context_and_challenges": "Transition",
                "skills_technical": [{"name": "Spark", "level": "senior"}],
                "skills_sector": [{"name": "Energie", "level": "confirmed"}],
            },
        )

        consultant = db.get_consultant(cid)
        tech_names = [s["name"] for s in consultant["skills_technical"]]
        sector_names = [s["name"] for s in consultant["skills_sector"]]
        assert "Spark" in tech_names
        assert "Energie" in sector_names


class TestDeleteConsultant:
    """Tests de suppression d'un consultant"""

    @pytest.mark.unit
    def test_delete_existing(self, db, sample_consultant):
        """Suppression d'un consultant existant"""
        cid = db.save_consultant(sample_consultant)
        assert db.delete_consultant(cid) is True
        assert db.get_consultant(cid) is None

    @pytest.mark.unit
    def test_delete_nonexistent(self, db):
        """Suppression d'un consultant inexistant"""
        assert db.delete_consultant(999) is False
