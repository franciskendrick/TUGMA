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

# (target_version, script). Append new migrations here.
MIGRATIONS = [(1, MIGRATION_1_USERS)]


def migrate(db):
    """Apply every pending migration to `db` (a src.database.Database)."""
    connection = db.connect()
    version = connection.execute("PRAGMA user_version").fetchone()[0]

    for target, script in MIGRATIONS:
        if target > version:
            connection.executescript(script)
            version = target

    return version


def ensure_database(db_path=DB_PATH, schema=SCHEMA_PATH, seed=SEED_PATH):
    """Create the database from schema + seed if missing, then migrate."""
    from src.database import Database

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
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
