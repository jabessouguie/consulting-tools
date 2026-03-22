"""
Base de données pour TenderScout AI
Stockage et consultation des appels d'offres collectés et analysés.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TenderDatabase:
    """Gestion de la base de données des appels d'offres."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_dir = base_dir / "data" / "tenderscout"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "tenders.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialise les tables si elles n'existent pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tenders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT UNIQUE NOT NULL,
                    titre TEXT NOT NULL,
                    acheteur TEXT,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    date_publication TEXT,
                    date_limite TEXT,
                    description TEXT,
                    decision TEXT,
                    score INTEGER,
                    analyse TEXT,
                    scraped_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tenders_decision
                ON tenders(decision)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tenders_source
                ON tenders(source)
                """
            )

            conn.commit()

            # Migration : ajout de cv_match_score (idempotent)
            try:
                cursor.execute(
                    "ALTER TABLE tenders ADD COLUMN cv_match_score INTEGER"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Colonne déjà existante

    def save_tenders(self, tenders: List[Dict[str, Any]]) -> int:
        """Sauvegarde les appels d'offres (ignore les doublons via reference UNIQUE).

        Args:
            tenders: Liste de dicts avec reference, titre, acheteur, source,
                     url, date_publication, date_limite, description.

        Returns:
            Nombre de nouveaux AOs insérés.
        """
        saved_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for tender in tenders:
                try:
                    cursor.execute(
                        """
                        INSERT INTO tenders
                        (reference, titre, acheteur, source, url,
                         date_publication, date_limite, description, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tender.get("reference", ""),
                            tender.get("titre", ""),
                            tender.get("acheteur", ""),
                            tender.get("source", ""),
                            tender.get("url", ""),
                            tender.get("date_publication", ""),
                            tender.get("date_limite", ""),
                            tender.get("description", ""),
                            datetime.now().isoformat(),
                        ),
                    )
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # AO déjà présent (reference unique)
                    continue

            conn.commit()

        return saved_count

    def update_analysis(self, reference: str, analysis: Dict[str, Any]):
        """Met à jour la décision Gemini pour un AO existant.

        Args:
            reference: Référence unique de l'AO.
            analysis: Dict avec decision, score, et le reste du JSON Gemini.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE tenders
                SET decision = ?, score = ?, cv_match_score = ?, analyse = ?
                WHERE reference = ?
                """,
                (
                    analysis.get("decision"),
                    analysis.get("score"),
                    analysis.get("cv_pertinence"),
                    json.dumps(analysis, ensure_ascii=False),
                    reference,
                ),
            )
            conn.commit()

    def get_tenders(
        self,
        source: Optional[str] = None,
        decision: Optional[str] = None,
        min_cv_match: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Récupère les AOs avec filtres optionnels.

        Args:
            source: Filtrer par source ('boamp' | 'francemarches').
            decision: Filtrer par décision ('GO' | 'NO-GO' | 'A_ETUDIER').
            min_cv_match: Score minimum de pertinence CV (0-100).
            limit: Nombre maximum d'AOs retournés.

        Returns:
            Liste de dicts.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM tenders WHERE 1=1"
            params: List[Any] = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if decision:
                query += " AND decision = ?"
                params.append(decision)

            if min_cv_match is not None:
                query += " AND cv_match_score >= ?"
                params.append(min_cv_match)

            query += " ORDER BY scraped_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_unanalyzed_references(self, references: List[str]) -> List[str]:
        """Retourne les références parmi celles fournies qui n'ont pas encore de décision.

        Args:
            references: Liste de références à vérifier.

        Returns:
            Sous-liste des références sans analyse.
        """
        if not references:
            return []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            placeholders = ",".join("?" * len(references))
            cursor.execute(
                f"SELECT reference FROM tenders WHERE reference IN ({placeholders}) AND decision IS NULL",
                references,
            )
            rows = cursor.fetchall()

        return [row["reference"] for row in rows]

    def export_to_excel(self, path: str):
        """Exporte tous les AOs vers un fichier Excel.

        Args:
            path: Chemin de destination du fichier .xlsx.
        """
        import pandas as pd

        rows = self.get_tenders(limit=10000)

        # Préparer les colonnes pour l'export
        export_rows = []
        for row in rows:
            analyse = {}
            if row.get("analyse"):
                try:
                    analyse = json.loads(row["analyse"])
                except (ValueError, TypeError):
                    analyse = {}

            export_rows.append(
                {
                    "Référence": row.get("reference", ""),
                    "Source": row.get("source", ""),
                    "Titre": row.get("titre", ""),
                    "Acheteur": row.get("acheteur", ""),
                    "Date publication": row.get("date_publication", ""),
                    "Date limite": row.get("date_limite", ""),
                    "Décision": row.get("decision", ""),
                    "Score": row.get("score", ""),
                    "Match CV": row.get("cv_match_score", ""),
                    "Compétences correspondantes": ", ".join(
                        analyse.get("competences_correspondantes", [])
                    ),
                    "Résumé": analyse.get("resume", ""),
                    "Budget estimé": analyse.get("budget_estime", ""),
                    "Recommandation": analyse.get("recommandation", ""),
                    "URL": row.get("url", ""),
                    "Scraping": row.get("scraped_at", ""),
                }
            )

        df = pd.DataFrame(export_rows)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, index=False, engine="openpyxl")
