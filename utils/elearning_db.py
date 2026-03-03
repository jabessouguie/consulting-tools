"""
Base de donnees pour la plateforme E-learning Adaptatif par IA
Stockage des cours, quiz, sessions etudiants et parcours d'apprentissage
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ElearningDatabase:
    """Gestion de la base de donnees E-learning"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_dir = base_dir / "data" / "elearning"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "elearning.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialise les tables si elles n'existent pas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    topic TEXT NOT NULL,
                    target_audience TEXT,
                    difficulty_level TEXT NOT NULL,
                    duration_hours INTEGER,
                    learning_objectives TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    module_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    estimated_duration_minutes INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (course_id)
                        REFERENCES courses(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id INTEGER NOT NULL,
                    lesson_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_markdown TEXT NOT NULL,
                    key_takeaways TEXT,
                    practical_exercises TEXT,
                    estimated_duration_minutes INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (module_id)
                        REFERENCES modules(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quizzes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    lesson_id INTEGER,
                    title TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (course_id)
                        REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (lesson_id)
                        REFERENCES lessons(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quiz_id INTEGER NOT NULL,
                    question_number INTEGER NOT NULL,
                    question_type TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    options TEXT,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT,
                    difficulty_level TEXT NOT NULL,
                    bloom_level TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (quiz_id)
                        REFERENCES quizzes(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS student_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_identifier TEXT NOT NULL UNIQUE,
                    started_at TEXT NOT NULL,
                    last_active TEXT NOT NULL
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    quiz_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    current_difficulty TEXT NOT NULL,
                    score_percentage REAL,
                    total_questions INTEGER,
                    correct_answers INTEGER,
                    FOREIGN KEY (session_id)
                        REFERENCES student_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (quiz_id)
                        REFERENCES quizzes(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS answer_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    student_answer TEXT NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    time_spent_seconds INTEGER,
                    answered_at TEXT NOT NULL,
                    FOREIGN KEY (attempt_id)
                        REFERENCES quiz_attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY (question_id)
                        REFERENCES questions(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    stated_goals TEXT,
                    current_progress_percentage REAL DEFAULT 0,
                    knowledge_gaps TEXT,
                    recommendations TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id)
                        REFERENCES student_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id)
                        REFERENCES courses(id) ON DELETE CASCADE
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS module_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    learning_path_id INTEGER NOT NULL,
                    module_id INTEGER NOT NULL,
                    completion_percentage REAL DEFAULT 0,
                    mastery_level TEXT DEFAULT 'none',
                    last_accessed TEXT,
                    FOREIGN KEY (learning_path_id)
                        REFERENCES learning_paths(id) ON DELETE CASCADE,
                    FOREIGN KEY (module_id)
                        REFERENCES modules(id) ON DELETE CASCADE
                )
            """
            )

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_modules_course " "ON modules(course_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_module " "ON lessons(module_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_quiz " "ON questions(quiz_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session "
                "ON quiz_attempts(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz " "ON quiz_attempts(quiz_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_answer_records_attempt "
                "ON answer_records(attempt_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_paths_session "
                "ON learning_paths(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_module_progress_path "
                "ON module_progress(learning_path_id)"
            )

            conn.commit()

    # ==================
    # COURSES
    # ==================

    def save_course(self, data: Dict[str, Any]) -> int:
        """
        Sauvegarde un cours avec ses modules et lecons

        Args:
            data: Dict avec title, description, topic, target_audience,
                  difficulty_level, duration_hours, learning_objectives,
                  modules: [{title, description, estimated_duration_minutes,
                  lessons: [{title, content_markdown, key_takeaways,
                  practical_exercises, estimated_duration_minutes}]}]

        Returns:
            ID du cours
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO courses
                (title, description, topic, target_audience,
                 difficulty_level, duration_hours, learning_objectives,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.get("title", ""),
                    data.get("description", ""),
                    data.get("topic", ""),
                    data.get("target_audience", ""),
                    data.get("difficulty_level", "intermediate"),
                    data.get("duration_hours", 1),
                    json.dumps(
                        data.get("learning_objectives", []),
                        ensure_ascii=False,
                    ),
                    now,
                    now,
                ),
            )
            course_id = cursor.lastrowid

            for i, module in enumerate(data.get("modules", []), 1):
                cursor.execute(
                    """
                    INSERT INTO modules
                    (course_id, module_number, title, description,
                     estimated_duration_minutes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        course_id,
                        module.get("module_number", i),
                        module.get("title", ""),
                        module.get("description", ""),
                        module.get("estimated_duration_minutes", 30),
                        now,
                    ),
                )
                module_id = cursor.lastrowid

                for j, lesson in enumerate(module.get("lessons", []), 1):
                    cursor.execute(
                        """
                        INSERT INTO lessons
                        (module_id, lesson_number, title,
                         content_markdown, key_takeaways,
                         practical_exercises,
                         estimated_duration_minutes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            module_id,
                            lesson.get("lesson_number", j),
                            lesson.get("title", ""),
                            lesson.get("content_markdown", ""),
                            json.dumps(
                                lesson.get("key_takeaways", []),
                                ensure_ascii=False,
                            ),
                            json.dumps(
                                lesson.get("practical_exercises", []),
                                ensure_ascii=False,
                            ),
                            lesson.get("estimated_duration_minutes", 15),
                            now,
                        ),
                    )

            conn.commit()

        return course_id

    def get_course(self, course_id: int) -> Optional[Dict[str, Any]]:
        """Recupere un cours complet avec modules et lecons"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM courses WHERE id = ?",
                (course_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            course = dict(row)
            try:
                course["learning_objectives"] = json.loads(
                    course.get("learning_objectives") or "[]"
                )
            except (json.JSONDecodeError, TypeError):
                course["learning_objectives"] = []

            # Load modules with lessons
            cursor.execute(
                "SELECT * FROM modules WHERE course_id = ? " "ORDER BY module_number",
                (course_id,),
            )
            modules = []
            for mod_row in cursor.fetchall():
                module = dict(mod_row)

                cursor.execute(
                    "SELECT * FROM lessons WHERE module_id = ? " "ORDER BY lesson_number",
                    (module["id"],),
                )
                lessons = []
                for les_row in cursor.fetchall():
                    lesson = dict(les_row)
                    for field in (
                        "key_takeaways",
                        "practical_exercises",
                    ):
                        try:
                            lesson[field] = json.loads(lesson.get(field) or "[]")
                        except (json.JSONDecodeError, TypeError):
                            lesson[field] = []
                    lessons.append(lesson)

                module["lessons"] = lessons
                modules.append(module)

            course["modules"] = modules
            return course

    def get_all_courses(self) -> List[Dict[str, Any]]:
        """Liste resume de tous les cours"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT c.id, c.title, c.topic, c.difficulty_level,
                    c.duration_hours, c.target_audience, c.created_at,
                    (SELECT COUNT(*) FROM modules
                     WHERE course_id = c.id) as modules_count,
                    (SELECT COUNT(*) FROM lessons l
                     JOIN modules m ON l.module_id = m.id
                     WHERE m.course_id = c.id) as lessons_count
                FROM courses c
                ORDER BY c.created_at DESC
            """
            )
            return [dict(r) for r in cursor.fetchall()]

    def delete_course(self, course_id: int) -> bool:
        """Supprime un cours et toutes ses donnees"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM courses WHERE id = ?",
                (course_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_course(self, course_id: int, data: Dict[str, Any]) -> bool:
        """Met a jour les champs d'un cours"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE courses
                SET title = ?, description = ?, learning_objectives = ?,
                    updated_at = ?
                WHERE id = ?
            """,
                (
                    data.get("title", ""),
                    data.get("description", ""),
                    json.dumps(
                        data.get("learning_objectives", []),
                        ensure_ascii=False,
                    ),
                    now,
                    course_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    # ==================
    # QUIZZES
    # ==================

    def save_quiz(self, data: Dict[str, Any]) -> int:
        """
        Sauvegarde un quiz avec ses questions

        Args:
            data: Dict avec title, difficulty_level, course_id, lesson_id,
                  questions: [{question_type, question_text, options,
                  correct_answer, explanation, difficulty_level, bloom_level}]

        Returns:
            ID du quiz
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO quizzes
                (course_id, lesson_id, title, difficulty_level, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    data.get("course_id"),
                    data.get("lesson_id"),
                    data.get("title", ""),
                    data.get("difficulty_level", "medium"),
                    now,
                ),
            )
            quiz_id = cursor.lastrowid

            for i, q in enumerate(data.get("questions", []), 1):
                cursor.execute(
                    """
                    INSERT INTO questions
                    (quiz_id, question_number, question_type,
                     question_text, options, correct_answer,
                     explanation, difficulty_level, bloom_level,
                     created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        quiz_id,
                        q.get("question_number", i),
                        q.get("question_type", "mcq"),
                        q.get("question_text", ""),
                        json.dumps(
                            q.get("options", []),
                            ensure_ascii=False,
                        ),
                        q.get("correct_answer", ""),
                        q.get("explanation", ""),
                        q.get("difficulty_level", "medium"),
                        q.get("bloom_level", "understand"),
                        now,
                    ),
                )

            conn.commit()

        return quiz_id

    def get_quiz(self, quiz_id: int) -> Optional[Dict[str, Any]]:
        """Recupere un quiz avec ses questions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM quizzes WHERE id = ?",
                (quiz_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            quiz = dict(row)

            cursor.execute(
                "SELECT * FROM questions WHERE quiz_id = ? " "ORDER BY question_number",
                (quiz_id,),
            )
            questions = []
            for q_row in cursor.fetchall():
                q = dict(q_row)
                try:
                    q["options"] = json.loads(q.get("options") or "[]")
                except (json.JSONDecodeError, TypeError):
                    q["options"] = []
                questions.append(q)

            quiz["questions"] = questions
            return quiz

    def get_quizzes_for_course(self, course_id: int) -> List[Dict[str, Any]]:
        """Liste les quiz d'un cours"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT q.*, COUNT(qu.id) as questions_count
                FROM quizzes q
                LEFT JOIN questions qu ON qu.quiz_id = q.id
                WHERE q.course_id = ?
                GROUP BY q.id
                ORDER BY q.created_at DESC
            """,
                (course_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_questions_by_difficulty(self, quiz_id: int, difficulty: str) -> List[Dict[str, Any]]:
        """Recupere les questions d'un quiz par difficulte"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM questions "
                "WHERE quiz_id = ? AND difficulty_level = ? "
                "ORDER BY question_number",
                (quiz_id, difficulty),
            )
            questions = []
            for q_row in cursor.fetchall():
                q = dict(q_row)
                try:
                    q["options"] = json.loads(q.get("options") or "[]")
                except (json.JSONDecodeError, TypeError):
                    q["options"] = []
                questions.append(q)
            return questions

    # ==================
    # SESSIONS
    # ==================

    def init_session(self, identifier: str = None) -> Dict[str, Any]:
        """Cree ou recupere une session etudiant"""
        if not identifier:
            identifier = str(uuid.uuid4())[:8]

        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM student_sessions " "WHERE session_identifier = ?",
                (identifier,),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE student_sessions " "SET last_active = ? WHERE id = ?",
                    (now, row["id"]),
                )
                conn.commit()
                return dict(row)

            cursor.execute(
                "INSERT INTO student_sessions "
                "(session_identifier, started_at, last_active) "
                "VALUES (?, ?, ?)",
                (identifier, now, now),
            )
            conn.commit()
            return {
                "id": cursor.lastrowid,
                "session_identifier": identifier,
                "started_at": now,
                "last_active": now,
            }

    def get_session(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Recupere une session par identifiant"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM student_sessions " "WHERE session_identifier = ?",
                (identifier,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================
    # QUIZ ATTEMPTS
    # ==================

    def create_attempt(self, session_id: int, quiz_id: int, difficulty: str = "medium") -> int:
        """Cree une tentative de quiz"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO quiz_attempts
                (session_id, quiz_id, started_at,
                 current_difficulty, total_questions, correct_answers)
                VALUES (?, ?, ?, ?, 0, 0)
            """,
                (session_id, quiz_id, now, difficulty),
            )
            conn.commit()
            return cursor.lastrowid

    def record_answer(
        self,
        attempt_id: int,
        question_id: int,
        student_answer: str,
        is_correct: bool,
        time_spent: int = 0,
    ) -> int:
        """Enregistre une reponse"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO answer_records
                (attempt_id, question_id, student_answer,
                 is_correct, time_spent_seconds, answered_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    attempt_id,
                    question_id,
                    student_answer,
                    is_correct,
                    time_spent,
                    now,
                ),
            )

            # Update attempt counters
            cursor.execute(
                "UPDATE quiz_attempts SET total_questions = " "total_questions + 1 WHERE id = ?",
                (attempt_id,),
            )
            if is_correct:
                cursor.execute(
                    "UPDATE quiz_attempts SET correct_answers = "
                    "correct_answers + 1 WHERE id = ?",
                    (attempt_id,),
                )

            conn.commit()
            return cursor.lastrowid

    def complete_attempt(self, attempt_id: int) -> Dict[str, Any]:
        """Complete une tentative et calcule le score"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM quiz_attempts WHERE id = ?",
                (attempt_id,),
            )
            attempt = cursor.fetchone()
            if not attempt:
                return {}

            total = attempt["total_questions"]
            correct = attempt["correct_answers"]
            score = (correct / total * 100) if total > 0 else 0

            cursor.execute(
                "UPDATE quiz_attempts "
                "SET completed_at = ?, score_percentage = ? "
                "WHERE id = ?",
                (now, score, attempt_id),
            )
            conn.commit()

            return {
                "attempt_id": attempt_id,
                "score_percentage": score,
                "total_questions": total,
                "correct_answers": correct,
                "completed_at": now,
            }

    def update_attempt_difficulty(self, attempt_id: int, difficulty: str):
        """Met a jour la difficulte courante d'une tentative"""
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().execute(
                "UPDATE quiz_attempts " "SET current_difficulty = ? WHERE id = ?",
                (difficulty, attempt_id),
            )
            conn.commit()

    def get_attempt_results(self, attempt_id: int) -> Optional[Dict[str, Any]]:
        """Recupere les resultats detailles d'une tentative"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM quiz_attempts WHERE id = ?",
                (attempt_id,),
            )
            attempt = cursor.fetchone()
            if not attempt:
                return None

            result = dict(attempt)

            cursor.execute(
                """
                SELECT ar.*, q.question_text, q.question_type,
                    q.correct_answer, q.explanation, q.options,
                    q.difficulty_level, q.bloom_level
                FROM answer_records ar
                JOIN questions q ON ar.question_id = q.id
                WHERE ar.attempt_id = ?
                ORDER BY ar.answered_at
            """,
                (attempt_id,),
            )
            answers = []
            for row in cursor.fetchall():
                a = dict(row)
                try:
                    a["options"] = json.loads(a.get("options") or "[]")
                except (json.JSONDecodeError, TypeError):
                    a["options"] = []
                answers.append(a)

            result["answers"] = answers
            return result

    def get_recent_answers(self, attempt_id: int, limit: int = 3) -> List[Dict[str, Any]]:
        """Recupere les N dernieres reponses d'une tentative"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM answer_records "
                "WHERE attempt_id = ? "
                "ORDER BY answered_at DESC LIMIT ?",
                (attempt_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]

    # ==================
    # LEARNING PATHS
    # ==================

    def save_learning_path(self, data: Dict[str, Any]) -> int:
        """Sauvegarde un parcours d'apprentissage"""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            # Check if path exists for session+course
            cursor.execute(
                "SELECT id FROM learning_paths " "WHERE session_id = ? AND course_id = ?",
                (data["session_id"], data["course_id"]),
            )
            existing = cursor.fetchone()

            if existing:
                path_id = existing[0]
                cursor.execute(
                    """
                    UPDATE learning_paths
                    SET stated_goals = ?, knowledge_gaps = ?,
                        recommendations = ?,
                        current_progress_percentage = ?,
                        updated_at = ?
                    WHERE id = ?
                """,
                    (
                        json.dumps(
                            data.get("stated_goals", []),
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            data.get("knowledge_gaps", []),
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            data.get("recommendations", []),
                            ensure_ascii=False,
                        ),
                        data.get("current_progress_percentage", 0),
                        now,
                        path_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO learning_paths
                    (session_id, course_id, stated_goals,
                     current_progress_percentage, knowledge_gaps,
                     recommendations, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["session_id"],
                        data["course_id"],
                        json.dumps(
                            data.get("stated_goals", []),
                            ensure_ascii=False,
                        ),
                        data.get("current_progress_percentage", 0),
                        json.dumps(
                            data.get("knowledge_gaps", []),
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            data.get("recommendations", []),
                            ensure_ascii=False,
                        ),
                        now,
                        now,
                    ),
                )
                path_id = cursor.lastrowid

            conn.commit()

        return path_id

    def get_learning_path(self, session_id: int, course_id: int) -> Optional[Dict[str, Any]]:
        """Recupere un parcours d'apprentissage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM learning_paths " "WHERE session_id = ? AND course_id = ?",
                (session_id, course_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            path = dict(row)
            for field in (
                "stated_goals",
                "knowledge_gaps",
                "recommendations",
            ):
                try:
                    path[field] = json.loads(path.get(field) or "[]")
                except (json.JSONDecodeError, TypeError):
                    path[field] = []

            # Load module progress
            cursor.execute(
                "SELECT * FROM module_progress " "WHERE learning_path_id = ?",
                (path["id"],),
            )
            path["module_progress"] = [dict(r) for r in cursor.fetchall()]

            return path

    def update_module_progress(
        self,
        learning_path_id: int,
        module_id: int,
        completion_pct: float,
        mastery_level: str,
    ):
        """Met a jour la progression d'un module"""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM module_progress " "WHERE learning_path_id = ? AND module_id = ?",
                (learning_path_id, module_id),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE module_progress
                    SET completion_percentage = ?,
                        mastery_level = ?,
                        last_accessed = ?
                    WHERE id = ?
                """,
                    (completion_pct, mastery_level, now, existing[0]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO module_progress
                    (learning_path_id, module_id,
                     completion_percentage, mastery_level,
                     last_accessed)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        learning_path_id,
                        module_id,
                        completion_pct,
                        mastery_level,
                        now,
                    ),
                )

            # Recalculate overall progress
            cursor.execute(
                "SELECT AVG(completion_percentage) "
                "FROM module_progress "
                "WHERE learning_path_id = ?",
                (learning_path_id,),
            )
            avg = cursor.fetchone()[0] or 0
            cursor.execute(
                "UPDATE learning_paths "
                "SET current_progress_percentage = ?, "
                "updated_at = ? WHERE id = ?",
                (avg, now, learning_path_id),
            )

            conn.commit()

    def get_session_quiz_results(self, session_id: int, course_id: int) -> List[Dict[str, Any]]:
        """Recupere tous les resultats de quiz d'une session pour un cours"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT qa.*, q.title as quiz_title,
                    q.lesson_id
                FROM quiz_attempts qa
                JOIN quizzes q ON qa.quiz_id = q.id
                WHERE qa.session_id = ? AND q.course_id = ?
                    AND qa.completed_at IS NOT NULL
                ORDER BY qa.completed_at DESC
            """,
                (session_id, course_id),
            )
            return [dict(r) for r in cursor.fetchall()]
