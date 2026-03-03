"""
Base de donnees pour la veille technologique
Stockage et consultation des articles collectes
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArticleDatabase:
    """Gestion de la base de donnees des articles de veille"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_dir = base_dir / "data" / "veille"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "articles.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialise les tables si elles n'existent pas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Table articles
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    link TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    content TEXT,
                    date TEXT,
                    source TEXT,
                    keywords TEXT,
                    collected_at TEXT NOT NULL,
                    read BOOLEAN DEFAULT 0,
                    favorite BOOLEAN DEFAULT 0
                )
            """
            )

            # Table digests
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    content TEXT NOT NULL,
                    num_articles INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    file_path TEXT
                )
            """
            )

            # Index pour recherche rapide
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_articles_date
                ON articles(date DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_articles_source
                ON articles(source)
            """
            )

            conn.commit()

    def save_articles(self, articles: List[Dict[str, Any]]) -> int:
        """
        Sauvegarde des articles (ignore les doublons)

        Args:
            articles: Liste d articles avec title, link, summary, date, source

        Returns:
            Nombre d articles sauvegardes
        """
        saved_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for article in articles:
                try:
                    cursor.execute(
                        """
                        INSERT INTO articles
                        (title, link, summary, date, source, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            article.get("title", ""),
                            article.get("link", ""),
                            article.get("summary", ""),
                            article.get("date"),
                            article.get("source", ""),
                            datetime.now().isoformat(),
                        ),
                    )
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # Article deja existant (link unique)
                    continue

            conn.commit()

        return saved_count

    def get_articles(
        self,
        limit: int = 50,
        offset: int = 0,
        source: Optional[str] = None,
        keyword: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupere des articles avec filtres

        Args:
            limit: Nombre max d articles
            offset: Offset pour pagination
            source: Filtrer par source
            keyword: Filtrer par mot-cle dans titre/summary
            days: Articles des X derniers jours

        Returns:
            Liste d articles
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM articles WHERE 1=1"
            params = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if keyword:
                query += " AND (title LIKE ? OR summary LIKE ?)"
                kw_pattern = f"%{keyword}%"
                params.extend([kw_pattern, kw_pattern])

            if days:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                query += " AND date >= ?"
                params.append(cutoff)

            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_article_stats(self) -> Dict[str, Any]:
        """Statistiques sur les articles stockes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total articles
            cursor.execute("SELECT COUNT(*) FROM articles")
            total = cursor.fetchone()[0]

            # Articles par source
            cursor.execute(
                """
                SELECT source, COUNT(*) as count
                FROM articles
                GROUP BY source
                ORDER BY count DESC
                LIMIT 10
            """
            )
            by_source = [{"source": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Articles des 7 derniers jours
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("SELECT COUNT(*) FROM articles WHERE date >= ?", (week_ago,))
            last_week = cursor.fetchone()[0]

            return {"total_articles": total, "last_week": last_week, "by_source": by_source}

    def save_digest(
        self, period: str, content: str, num_articles: int, file_path: str = None
    ) -> int:
        """Sauvegarde un digest genere"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO digests (period, content, num_articles, generated_at, file_path)
                VALUES (?, ?, ?, ?, ?)
            """,
                (period, content, num_articles, datetime.now().isoformat(), file_path),
            )

            conn.commit()
            return cursor.lastrowid

    def get_latest_digest(self, period: str = "daily") -> Optional[Dict[str, Any]]:
        """Recupere le dernier digest genere"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM digests
                WHERE period = ?
                ORDER BY generated_at DESC
                LIMIT 1
            """,
                (period,),
            )

            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_as_read(self, article_id: int):
        """Marque un article comme lu"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE articles SET read = 1 WHERE id = ?", (article_id,))
            conn.commit()

    def toggle_favorite(self, article_id: int):
        """Toggle favori sur un article"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE articles
                SET favorite = NOT favorite
                WHERE id = ?
            """,
                (article_id,),
            )
            conn.commit()
