"""
Base de donnees pour le Market of Skills des consultants Consulting Tools
Stockage et gestion des profils, competences, missions et centres d'interet
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConsultantDatabase:
    """Gestion de la base de donnees des consultants Consulting Tools"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_dir = base_dir / "data" / "skills_market"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "consultants.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialise les tables si elles n'existent pas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS consultants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    title TEXT,
                    email TEXT,
                    photo_url TEXT,
                    bio TEXT,
                    raw_pptx_text TEXT,
                    strengths TEXT,
                    improvement_areas TEXT,
                    management_suggestions TEXT,
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    level TEXT,
                    FOREIGN KEY (consultant_id) REFERENCES consultants(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultant_id INTEGER NOT NULL,
                    client_name TEXT NOT NULL,
                    context_and_challenges TEXT,
                    deliverables TEXT,
                    tasks TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (consultant_id) REFERENCES consultants(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (consultant_id) REFERENCES consultants(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS certifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    organization TEXT,
                    date_obtained TEXT,
                    description TEXT,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (consultant_id)
                        REFERENCES consultants(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS disinterests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (consultant_id)
                        REFERENCES consultants(id) ON DELETE CASCADE
                )
            """
            )

            # Indexes
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_consultant
                ON skills(consultant_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_category
                ON skills(category)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_missions_consultant
                ON missions(consultant_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_interests_consultant
                ON interests(consultant_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_certifications_consultant
                ON certifications(consultant_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_disinterests_consultant
                ON disinterests(consultant_id)
            """
            )

            conn.commit()

            # Migration : ajout des colonnes etendues (idempotent)
            for col_sql in [
                "ALTER TABLE consultants ADD COLUMN firstname TEXT",
                "ALTER TABLE consultants ADD COLUMN company TEXT",
                "ALTER TABLE consultants ADD COLUMN linkedin_url TEXT",
                "ALTER TABLE consultants ADD COLUMN consultant_theme TEXT",
            ]:
                try:
                    cursor.execute(col_sql)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Colonne deja existante

    def save_consultant(self, data: Dict[str, Any]) -> int:
        """
        Insere ou met a jour un consultant

        Args:
            data: Dict avec name, title, bio, skills_technical, skills_sector,
                  missions, interests, strengths, improvement_areas, etc.

        Returns:
            ID du consultant
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            # Upsert consultant
            cursor.execute(
                """
                INSERT INTO consultants
                (name, title, email, photo_url, bio, raw_pptx_text,
                 strengths, improvement_areas, management_suggestions,
                 imported_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    title = excluded.title,
                    email = excluded.email,
                    photo_url = excluded.photo_url,
                    bio = excluded.bio,
                    raw_pptx_text = excluded.raw_pptx_text,
                    strengths = excluded.strengths,
                    improvement_areas = excluded.improvement_areas,
                    management_suggestions = excluded.management_suggestions,
                    updated_at = excluded.updated_at
            """,
                (
                    data.get("name", ""),
                    data.get("title", ""),
                    data.get("email", ""),
                    data.get("photo_url", ""),
                    data.get("bio", ""),
                    data.get("raw_pptx_text", ""),
                    json.dumps(data.get("strengths", []), ensure_ascii=False),
                    json.dumps(data.get("improvement_areas", []), ensure_ascii=False),
                    data.get("management_suggestions", ""),
                    now,
                    now,
                ),
            )

            consultant_id = cursor.lastrowid
            if consultant_id == 0:
                # ON CONFLICT case: fetch existing id
                cursor.execute(
                    "SELECT id FROM consultants WHERE name = ?",
                    (data.get("name", ""),),
                )
                consultant_id = cursor.fetchone()[0]
                # Clear existing related data for re-import
                cursor.execute("DELETE FROM skills WHERE consultant_id = ?", (consultant_id,))
                cursor.execute("DELETE FROM missions WHERE consultant_id = ?", (consultant_id,))
                cursor.execute("DELETE FROM interests WHERE consultant_id = ?", (consultant_id,))

            # Insert skills
            insert_skill_sql = (
                "INSERT INTO skills (consultant_id, name, category, level)" " VALUES (?, ?, ?, ?)"
            )
            for skill in data.get("skills_technical", []):
                if isinstance(skill, dict):
                    s_name = skill.get("name", "")
                    s_level = skill.get("level", "")
                else:
                    s_name = str(skill)
                    s_level = ""
                cursor.execute(
                    insert_skill_sql,
                    (consultant_id, s_name, "technical", s_level),
                )

            for skill in data.get("skills_sector", []):
                if isinstance(skill, dict):
                    s_name = skill.get("name", "")
                    s_level = skill.get("level", "")
                else:
                    s_name = str(skill)
                    s_level = ""
                cursor.execute(
                    insert_skill_sql,
                    (consultant_id, s_name, "sector", s_level),
                )

            # Insert missions
            for mission in data.get("missions", []):
                cursor.execute(
                    """INSERT INTO missions
                    (consultant_id, client_name, context_and_challenges, deliverables, tasks,
                     start_date, end_date, added_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        consultant_id,
                        mission.get("client_name", ""),
                        mission.get("context_and_challenges", ""),
                        mission.get("deliverables", ""),
                        mission.get("tasks", ""),
                        mission.get("start_date", ""),
                        mission.get("end_date", ""),
                        now,
                    ),
                )

            # Insert interests
            for interest in data.get("interests", []):
                interest_name = interest if isinstance(interest, str) else interest.get("name", "")
                if interest_name:
                    cursor.execute(
                        "INSERT INTO interests (consultant_id, name, added_at) VALUES (?, ?, ?)",
                        (consultant_id, interest_name, now),
                    )

            conn.commit()

        return consultant_id

    def get_consultant(self, consultant_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupere le profil complet d'un consultant

        Args:
            consultant_id: ID du consultant

        Returns:
            Dict avec profil complet ou None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM consultants WHERE id = ?", (consultant_id,))
            row = cursor.fetchone()
            if not row:
                return None

            consultant = dict(row)

            # Parse JSON fields
            for field in ("strengths", "improvement_areas"):
                try:
                    consultant[field] = json.loads(consultant.get(field) or "[]")
                except (json.JSONDecodeError, TypeError):
                    consultant[field] = []

            # Load skills
            cursor.execute(
                "SELECT id, name, category, level FROM skills WHERE consultant_id = ?",
                (consultant_id,),
            )
            skills = [dict(r) for r in cursor.fetchall()]
            consultant["skills_technical"] = [s for s in skills if s["category"] == "technical"]
            consultant["skills_sector"] = [s for s in skills if s["category"] == "sector"]

            # Load missions
            cursor.execute(
                "SELECT * FROM missions WHERE consultant_id = ? ORDER BY added_at DESC",
                (consultant_id,),
            )
            consultant["missions"] = [dict(r) for r in cursor.fetchall()]

            # Load interests
            cursor.execute(
                "SELECT id, name FROM interests WHERE consultant_id = ?",
                (consultant_id,),
            )
            consultant["interests"] = [dict(r) for r in cursor.fetchall()]

            # Load certifications
            cursor.execute(
                "SELECT id, name, organization, date_obtained, "
                "description FROM certifications "
                "WHERE consultant_id = ? ORDER BY added_at DESC",
                (consultant_id,),
            )
            consultant["certifications"] = [dict(r) for r in cursor.fetchall()]

            # Load disinterests
            cursor.execute(
                "SELECT id, name FROM disinterests " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            consultant["disinterests"] = [dict(r) for r in cursor.fetchall()]

            return consultant

    def get_all_consultants(self) -> List[Dict[str, Any]]:
        """
        Recupere la liste resumee de tous les consultants

        Returns:
            Liste de dicts avec id, name, title, nombre de skills/missions
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT c.id, c.name, c.title, c.bio,
                    (SELECT COUNT(*) FROM skills WHERE consultant_id = c.id) as skills_count,
                    (SELECT COUNT(*) FROM missions WHERE consultant_id = c.id) as missions_count
                FROM consultants c
                ORDER BY c.name
            """
            )
            consultants = [dict(r) for r in cursor.fetchall()]

            # Attach top skills for each consultant
            for consultant in consultants:
                cursor.execute(
                    """SELECT name, category, level FROM skills
                    WHERE consultant_id = ? ORDER BY category, name LIMIT 10""",
                    (consultant["id"],),
                )
                consultant["top_skills"] = [dict(r) for r in cursor.fetchall()]

            return consultants

    def search_by_skills(
        self,
        technical: Optional[List[str]] = None,
        sector: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recherche des consultants par competences

        Args:
            technical: Liste de noms de competences techniques
            sector: Liste de noms de competences sectorielles

        Returns:
            Liste de consultants correspondants
        """
        if not technical and not sector:
            return self.get_all_consultants()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            conditions = []
            params = []

            if technical:
                placeholders = ",".join("?" * len(technical))
                # nosec B608 - placeholders are parameterized ?
                conditions.append(
                    f"c.id IN ("
                    f"SELECT consultant_id FROM skills "
                    f"WHERE category = 'technical' "
                    f"AND LOWER(name) IN ({placeholders})"  # nosec B608
                    f")"
                )
                params.extend([t.lower() for t in technical])

            if sector:
                placeholders = ",".join("?" * len(sector))
                # nosec B608 - placeholders are parameterized ?
                conditions.append(
                    f"c.id IN ("
                    f"SELECT consultant_id FROM skills "
                    f"WHERE category = 'sector' "
                    f"AND LOWER(name) IN ({placeholders})"  # nosec B608
                    f")"
                )
                params.extend([s.lower() for s in sector])

            where_clause = " AND ".join(conditions)
            query = (
                "SELECT c.id, c.name, c.title, c.bio,"
                " (SELECT COUNT(*) FROM skills"
                " WHERE consultant_id = c.id) as skills_count,"
                " (SELECT COUNT(*) FROM missions"
                " WHERE consultant_id = c.id) as missions_count"
                " FROM consultants c"
                f" WHERE {where_clause}"  # nosec B608
                " ORDER BY c.name"
            )
            cursor.execute(query, params)
            consultants = [dict(r) for r in cursor.fetchall()]

            skills_q = (
                "SELECT name, category, level FROM skills"
                " WHERE consultant_id = ?"
                " ORDER BY category, name LIMIT 10"
            )
            for consultant in consultants:
                cursor.execute(skills_q, (consultant["id"],))
                consultant["top_skills"] = [dict(r) for r in cursor.fetchall()]

            return consultants

    def add_mission(
        self,
        consultant_id: int,
        mission_data: Dict[str, Any],
    ) -> int:
        """
        Ajoute une mission et met a jour les competences.

        Args:
            consultant_id: ID du consultant
            mission_data: Dict avec client_name, context_and_challenges,
                deliverables, tasks, skills_technical, skills_sector

        Returns:
            ID de la mission creee
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO missions
                (consultant_id, client_name,
                 context_and_challenges, deliverables,
                 tasks, start_date, end_date, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    consultant_id,
                    mission_data.get("client_name", ""),
                    mission_data.get("context_and_challenges", ""),
                    mission_data.get("deliverables", ""),
                    mission_data.get("tasks", ""),
                    mission_data.get("start_date", ""),
                    mission_data.get("end_date", ""),
                    now,
                ),
            )
            mission_id = cursor.lastrowid
            conn.commit()

            # Update consultant updated_at
            cursor.execute(
                "UPDATE consultants SET updated_at = ? " "WHERE id = ?",
                (now, consultant_id),
            )
            conn.commit()

        # Add skills from the mission
        for skill in mission_data.get("skills_technical", []):
            self.add_skill(consultant_id, skill, "technical")
        for skill in mission_data.get("skills_sector", []):
            self.add_skill(consultant_id, skill, "sector")

        return mission_id

    def add_skill(
        self,
        consultant_id: int,
        skill: Any,
        category: str,
    ):
        """
        Ajoute une competence si elle n'existe pas deja.

        Args:
            consultant_id: ID du consultant
            skill: str ou dict avec name/level
            category: 'technical' ou 'sector'
        """
        if isinstance(skill, dict):
            s_name = skill.get("name", "").strip()
            s_level = skill.get("level", "")
        else:
            s_name = str(skill).strip()
            s_level = ""

        if not s_name:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check if skill already exists
            cursor.execute(
                "SELECT id FROM skills "
                "WHERE consultant_id = ? "
                "AND LOWER(name) = ? AND category = ?",
                (consultant_id, s_name.lower(), category),
            )
            if cursor.fetchone():
                return  # Already exists

            cursor.execute(
                "INSERT INTO skills "
                "(consultant_id, name, category, level) "
                "VALUES (?, ?, ?, ?)",
                (consultant_id, s_name, category, s_level),
            )
            conn.commit()

    def update_interests(self, consultant_id: int, interests: List[str]):
        """
        Remplace la liste des centres d'interet d'un consultant

        Args:
            consultant_id: ID du consultant
            interests: Nouvelle liste de centres d'interet
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM interests WHERE consultant_id = ?", (consultant_id,))

            for interest_name in interests:
                if interest_name.strip():
                    cursor.execute(
                        "INSERT INTO interests (consultant_id, name, added_at) VALUES (?, ?, ?)",
                        (consultant_id, interest_name.strip(), now),
                    )

            # Update consultant updated_at
            cursor.execute(
                "UPDATE consultants SET updated_at = ? WHERE id = ?",
                (now, consultant_id),
            )
            conn.commit()

    def get_all_skills(self) -> Dict[str, List[str]]:
        """
        Recupere toutes les competences uniques groupees par categorie

        Returns:
            Dict avec 'technical' et 'sector' comme cles, listes de noms comme valeurs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT name, category FROM skills ORDER BY category, name")
            rows = cursor.fetchall()

            result = {"technical": [], "sector": []}
            for name, category in rows:
                if category in result:
                    result[category].append(name)

            return result

    def search_fulltext(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche textuelle dans les profils consultants

        Args:
            query: Terme de recherche

        Returns:
            Liste de consultants correspondants
        """
        pattern = f"%{query}%"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT c.id, c.name, c.title, c.bio,
                    (SELECT COUNT(*) FROM skills WHERE consultant_id = c.id) as skills_count,
                    (SELECT COUNT(*) FROM missions WHERE consultant_id = c.id) as missions_count
                FROM consultants c
                LEFT JOIN skills s ON s.consultant_id = c.id
                LEFT JOIN missions m ON m.consultant_id = c.id
                WHERE c.name LIKE ? OR c.title LIKE ? OR c.bio LIKE ?
                    OR s.name LIKE ? OR m.client_name LIKE ?
                ORDER BY c.name
            """,
                (pattern, pattern, pattern, pattern, pattern),
            )
            consultants = [dict(r) for r in cursor.fetchall()]

            skills_q = (
                "SELECT name, category, level FROM skills"
                " WHERE consultant_id = ?"
                " ORDER BY category, name LIMIT 10"
            )
            for consultant in consultants:
                cursor.execute(skills_q, (consultant["id"],))
                consultant["top_skills"] = [dict(r) for r in cursor.fetchall()]

            return consultants

    def is_imported(self) -> bool:
        """Verifie si des consultants ont deja ete importes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM consultants")
            return cursor.fetchone()[0] > 0

    def get_consultant_count(self) -> int:
        """Retourne le nombre de consultants"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM consultants")
            return cursor.fetchone()[0]

    def add_certification(
        self,
        consultant_id: int,
        cert_data: Dict[str, Any],
    ) -> int:
        """
        Ajoute une certification et met a jour les competences.

        Args:
            consultant_id: ID du consultant
            cert_data: Dict avec name, organization, date_obtained,
                description, skills_technical, skills_sector

        Returns:
            ID de la certification creee
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO certifications "
                "(consultant_id, name, organization, "
                "date_obtained, description, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    consultant_id,
                    cert_data.get("name", ""),
                    cert_data.get("organization", ""),
                    cert_data.get("date_obtained", ""),
                    cert_data.get("description", ""),
                    now,
                ),
            )
            cert_id = cursor.lastrowid
            cursor.execute(
                "UPDATE consultants SET updated_at = ? " "WHERE id = ?",
                (now, consultant_id),
            )
            conn.commit()

        # Add skills from certification
        for skill in cert_data.get("skills_technical", []):
            self.add_skill(consultant_id, skill, "technical")
        for skill in cert_data.get("skills_sector", []):
            self.add_skill(consultant_id, skill, "sector")

        return cert_id

    def update_disinterests(
        self,
        consultant_id: int,
        disinterests: List[str],
    ):
        """
        Remplace la liste des centres de desinteret.

        Args:
            consultant_id: ID du consultant
            disinterests: Nouvelle liste de desinterets
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM disinterests " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            for name in disinterests:
                if name.strip():
                    cursor.execute(
                        "INSERT INTO disinterests "
                        "(consultant_id, name, added_at) "
                        "VALUES (?, ?, ?)",
                        (consultant_id, name.strip(), now),
                    )
            cursor.execute(
                "UPDATE consultants SET updated_at = ? " "WHERE id = ?",
                (now, consultant_id),
            )
            conn.commit()

    def delete_consultant(self, consultant_id: int) -> bool:
        """
        Supprime un consultant et toutes ses donnees.

        Args:
            consultant_id: ID du consultant

        Returns:
            True si supprime, False si non trouve
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM consultants WHERE id = ?",
                (consultant_id,),
            )
            if not cursor.fetchone():
                return False
            cursor.execute(
                "DELETE FROM disinterests " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            cursor.execute(
                "DELETE FROM certifications " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            cursor.execute(
                "DELETE FROM interests " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            cursor.execute(
                "DELETE FROM missions " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            cursor.execute(
                "DELETE FROM skills " "WHERE consultant_id = ?",
                (consultant_id,),
            )
            cursor.execute(
                "DELETE FROM consultants WHERE id = ?",
                (consultant_id,),
            )
            conn.commit()
            return True

    def delete_all(self):
        """Supprime toutes les donnees (pour re-import)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM disinterests")
            cursor.execute("DELETE FROM certifications")
            cursor.execute("DELETE FROM interests")
            cursor.execute("DELETE FROM missions")
            cursor.execute("DELETE FROM skills")
            cursor.execute("DELETE FROM consultants")
            conn.commit()

    def update_photo_url(self, consultant_id: int, photo_url: str) -> bool:
        """
        Met a jour la photo de profil d'un consultant.

        Args:
            consultant_id: ID du consultant
            photo_url: URL ou chemin relatif vers la photo

        Returns:
            True si le consultant existe et a ete mis a jour, False sinon
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE consultants SET photo_url = ?, updated_at = ? WHERE id = ?",
                (photo_url, now, consultant_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_consultant_analysis(
        self,
        consultant_id: int,
        strengths: List[str],
        improvement_areas: List[str],
        management_suggestions: str,
    ):
        """
        Met a jour l'analyse forces/axes d'amelioration d'un consultant

        Args:
            consultant_id: ID du consultant
            strengths: Liste des points forts
            improvement_areas: Liste des axes d'amelioration
            management_suggestions: Suggestions manageriales
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE consultants
                SET strengths = ?, improvement_areas = ?,
                    management_suggestions = ?, updated_at = ?
                WHERE id = ?""",
                (
                    json.dumps(strengths, ensure_ascii=False),
                    json.dumps(improvement_areas, ensure_ascii=False),
                    management_suggestions,
                    now,
                    consultant_id,
                ),
            )
            conn.commit()

    def update_consultant_info(
        self,
        consultant_id: int,
        info: Dict[str, Any],
    ) -> bool:
        """
        Met a jour les informations de base d'un consultant.

        Args:
            consultant_id: ID du consultant.
            info: Dict pouvant contenir name, firstname, title, company,
                  linkedin_url, bio, consultant_theme (JSON str ou dict).

        Returns:
            True si le consultant existe et a ete mis a jour, False sinon.
        """
        now = datetime.now().isoformat()

        # Serialise le theme si c'est un dict
        theme = info.get("consultant_theme")
        if isinstance(theme, dict):
            theme = json.dumps(theme, ensure_ascii=False)

        fields: Dict[str, Any] = {}
        for key in ("name", "firstname", "title", "company", "linkedin_url", "bio"):
            if key in info:
                fields[key] = info[key]
        if theme is not None:
            fields["consultant_theme"] = theme
        fields["updated_at"] = now

        if len(fields) == 1:  # Que updated_at, rien a faire
            return False

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [consultant_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE consultants SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0
