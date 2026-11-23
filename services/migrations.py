# Database bootstrap and versioned, idempotent migrations.
#
# The schema version is stored in SQLite's PRAGMA user_version.
# Version 0 = the original schema.sql tables; each migration below
# only ADDS structure, so existing students, tutors, subjects and
# schedules are never touched.

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "tugma.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
SEED_PATH = ROOT / "database" / "seed.sql"

MIGRATION_1_USERS = """
BEGIN;
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL
                  CHECK (role IN ('student', 'tutor', 'admin')),
    student_id    INTEGER UNIQUE
                  REFERENCES students(student_id)
                  ON DELETE CASCADE ON UPDATE CASCADE,
    tutor_id      INTEGER UNIQUE
                  REFERENCES tutors(tutor_id)
                  ON DELETE CASCADE ON UPDATE CASCADE,
    display_name  TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1
                  CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- An account must point at exactly the profile its role needs.
    CHECK (
        (role = 'student' AND student_id IS NOT NULL AND tutor_id IS NULL)
        OR (role = 'tutor' AND tutor_id IS NOT NULL AND student_id IS NULL)
        OR (role = 'admin' AND student_id IS NULL AND tutor_id IS NULL
            AND display_name IS NOT NULL)
    )
);
PRAGMA user_version = 1;
COMMIT;
"""

# Migration 2: one account may hold a student profile, a tutor profile, or
# both. SQLite cannot alter a CHECK, so the table is rebuilt (nothing else
# references users). Old 'student'/'tutor' accounts become 'member'.
MIGRATION_2_DUAL_ROLE = """
BEGIN;
CREATE TABLE users_new (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('member', 'admin')),
    student_id    INTEGER UNIQUE
                  REFERENCES students(student_id)
                  ON DELETE CASCADE ON UPDATE CASCADE,
    tutor_id      INTEGER UNIQUE
                  REFERENCES tutors(tutor_id)
                  ON DELETE CASCADE ON UPDATE CASCADE,
    display_name  TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (role = 'member' AND (student_id IS NOT NULL OR tutor_id IS NOT NULL))
        OR (role = 'admin' AND student_id IS NULL AND tutor_id IS NULL
            AND display_name IS NOT NULL)
    )
);
INSERT INTO users_new
    (user_id, email, password_hash, role, student_id, tutor_id,
     display_name, is_active, created_at)
SELECT user_id, email, password_hash,
       CASE WHEN role = 'admin' THEN 'admin' ELSE 'member' END,
       student_id, tutor_id, display_name, is_active, created_at
FROM users;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
PRAGMA user_version = 2;
COMMIT;
"""

# Migration 3: tutoring sessions (request -> confirm) and a "stuck on" note.
MIGRATION_3_SESSIONS = """
BEGIN;
ALTER TABLE student_subjects ADD COLUMN note TEXT;
CREATE TABLE sessions (
    session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL
                 REFERENCES students(student_id)
                 ON DELETE CASCADE ON UPDATE CASCADE,
    tutor_id     INTEGER NOT NULL
                 REFERENCES tutors(tutor_id)
                 ON DELETE CASCADE ON UPDATE CASCADE,
    subject_id   INTEGER NOT NULL
                 REFERENCES subjects(subject_id)
                 ON DELETE RESTRICT ON UPDATE CASCADE,
    session_date TEXT NOT NULL
                 CHECK (session_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    start_time   TEXT NOT NULL
                 CHECK (start_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    end_time     TEXT NOT NULL
                 CHECK (end_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    note         TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'confirmed', 'declined', 'cancelled')),
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (start_time < end_time)
);
PRAGMA user_version = 3;
COMMIT;
"""


# Migration 4: data behind the profile pages (views/profile.py).
#   * students.bio / study_notes / interests
#   * tutor reviews with per-criterion scores, and tutor certificates
# Written as a function so it is safe whether or not these columns or tables
# already exist (for example if schema.sql was edited to include them).
def _migration_4_profiles(connection):
    existing = {row[1] for row in connection.execute("PRAGMA table_info(students)")}

    connection.execute("BEGIN")
    try:
        for column in ("bio", "study_notes", "interests"):
            if column not in existing:
                connection.execute(f"ALTER TABLE students ADD COLUMN {column} TEXT")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS tutor_reviews (
                review_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                tutor_id   INTEGER NOT NULL
                           REFERENCES tutors(tutor_id)
                           ON DELETE CASCADE ON UPDATE CASCADE,
                student_id INTEGER NOT NULL
                           REFERENCES students(student_id)
                           ON DELETE CASCADE ON UPDATE CASCADE,
                is_demo    INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tutor_review_scores (
                review_id INTEGER NOT NULL
                          REFERENCES tutor_reviews(review_id)
                          ON DELETE CASCADE ON UPDATE CASCADE,
                criterion TEXT NOT NULL,
                score     INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
                PRIMARY KEY (review_id, criterion)
            )""")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                certificate_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_code  TEXT NOT NULL UNIQUE,
                title             TEXT NOT NULL,
                category          TEXT NOT NULL,
                tier              TEXT CHECK (tier IN ('Gold', 'Silver', 'Bronze')),
                description       TEXT NOT NULL,
                requirement_label TEXT NOT NULL,
                target_value      INTEGER NOT NULL CHECK (target_value > 0)
            )""")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tutor_certificates (
                tutor_id       INTEGER NOT NULL
                               REFERENCES tutors(tutor_id)
                               ON DELETE CASCADE ON UPDATE CASCADE,
                certificate_id INTEGER NOT NULL
                               REFERENCES certificates(certificate_id)
                               ON DELETE CASCADE ON UPDATE CASCADE,
                status         TEXT NOT NULL DEFAULT 'in_progress'
                               CHECK (status IN ('earned', 'in_progress')),
                progress_value INTEGER NOT NULL DEFAULT 0 CHECK (progress_value >= 0),
                earned_date    TEXT,
                PRIMARY KEY (tutor_id, certificate_id)
            )""")
        connection.execute("PRAGMA user_version = 4")
        connection.commit()
    except Exception:
        connection.rollback()
        raise

# (target_version, script or function). Append new migrations here.
MIGRATIONS = [
    (1, MIGRATION_1_USERS),
    (2, MIGRATION_2_DUAL_ROLE),
    (3, MIGRATION_3_SESSIONS),
    (4, _migration_4_profiles),
]


def migrate(db):
    """Apply every pending migration to `db` (a src.database.Database)."""
    connection = db.connect()
    version = connection.execute("PRAGMA user_version").fetchone()[0]

    for target, script in MIGRATIONS:
        if target > version:
            if callable(script):
                script(connection)
            else:
                connection.executescript(script)
            version = target

    return version


def _has_schema(db_path):
    """False for a missing or empty file (for example one a stray connection
    created), so such a file is built from schema + seed instead of crashing."""
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchone() is not None
    finally:
        connection.close()


def ensure_database(db_path=DB_PATH, schema=SCHEMA_PATH, seed=SEED_PATH):
    """Create the database from schema + seed if missing, then migrate."""
    from src.database import Database

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not _has_schema(db_path):
        connection = sqlite3.connect(db_path)
        try:
            connection.executescript(Path(schema).read_text(encoding="utf-8"))
            connection.executescript(Path(seed).read_text(encoding="utf-8"))
            connection.commit()
        except Exception:
            connection.close()
            db_path.unlink(missing_ok=True)
            raise
        connection.close()

    db = Database(db_path)
    try:
        return migrate(db)
    finally:
        db.close()