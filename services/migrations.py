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

MIGRATION_4_TUTOR_PROFILES = """
BEGIN;
CREATE TABLE IF NOT EXISTS tutor_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id INTEGER NOT NULL REFERENCES tutors(tutor_id) ON DELETE CASCADE ON UPDATE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    session_reference TEXT NOT NULL, review_date TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    UNIQUE (tutor_id, session_reference)
);
CREATE TABLE IF NOT EXISTS tutor_review_scores (
    review_id INTEGER NOT NULL REFERENCES tutor_reviews(review_id) ON DELETE CASCADE ON UPDATE CASCADE,
    criterion TEXT NOT NULL CHECK (criterion IN ('Clear explanations','Patience','Prepared for the session','Uses worked examples','Arrives on time')),
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    PRIMARY KEY (review_id, criterion)
);
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id INTEGER PRIMARY KEY AUTOINCREMENT, certificate_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL, category TEXT NOT NULL CHECK (category IN ('teaching','subject','milestone')),
    tier TEXT CHECK (tier IN ('Bronze','Silver','Gold')), description TEXT NOT NULL,
    requirement_label TEXT NOT NULL, target_value INTEGER NOT NULL CHECK (target_value > 0)
);
CREATE TABLE IF NOT EXISTS tutor_certificates (
    tutor_id INTEGER NOT NULL REFERENCES tutors(tutor_id) ON DELETE CASCADE ON UPDATE CASCADE,
    certificate_id INTEGER NOT NULL REFERENCES certificates(certificate_id) ON DELETE CASCADE ON UPDATE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('earned','in_progress')),
    progress_value INTEGER NOT NULL DEFAULT 0 CHECK (progress_value >= 0), earned_date TEXT,
    PRIMARY KEY (tutor_id, certificate_id),
    CHECK (status != 'earned' OR earned_date IS NOT NULL),
    CHECK (status != 'in_progress' OR earned_date IS NULL)
);
INSERT OR IGNORE INTO certificates
(certificate_id,certificate_code,title,category,tier,description,requirement_label,target_value) VALUES
(1,'CLEAR_EXPLAINER','Clear Explainer','teaching','Gold','Recognized for consistently clear explanations across tutoring sessions.','Ratings of 4.5+ for clear explanations',5),
(2,'PATIENT_GUIDE','Patient Guide','teaching','Gold','Recognized for patience and supportive guidance.','Ratings of 4.5+ for patience',5),
(3,'WORKED_EXAMPLE_PRO','Worked-Example Pro','teaching','Silver','Uses relevant worked examples to explain difficult concepts.','Positive mentions of worked examples',10),
(4,'DISCRETE_STRUCTURES_TUTOR','Discrete Structures Tutor','subject','Silver','Subject certificate for Discrete Structures tutoring.','Rated sessions in Discrete Structures',10),
(5,'ALWAYS_ON_TIME','Always On Time','milestone',NULL,'Punctuality recognition milestone.','Ratings of 4.5+ for punctuality',10),
(6,'NUMBER_THEORY_TUTOR','Number Theory Tutor','subject',NULL,'Subject certificate for Number Theory tutoring.','Rated Number Theory sessions at 4.5+',5);
INSERT OR IGNORE INTO tutor_reviews (review_id,tutor_id,student_id,session_reference,review_date,is_demo) VALUES
(1,1,1,'DEMO-TA-01','2026-10-02',1),
(2,1,2,'DEMO-TA-02','2026-10-03',1),
(3,1,3,'DEMO-TA-03','2026-10-04',1),
(4,1,4,'DEMO-TA-04','2026-10-05',1),
(5,1,5,'DEMO-TA-05','2026-10-06',1),
(6,1,6,'DEMO-TA-06','2026-10-07',1),
(7,1,7,'DEMO-TA-07','2026-10-08',1),
(8,1,1,'DEMO-TA-08','2026-10-09',1),
(9,1,2,'DEMO-TA-09','2026-10-10',1),
(10,1,3,'DEMO-TA-10','2026-10-11',1),
(11,1,4,'DEMO-TA-11','2026-10-12',1),
(12,1,5,'DEMO-TA-12','2026-10-13',1),
(13,1,6,'DEMO-TA-13','2026-10-14',1),
(14,1,7,'DEMO-TA-14','2026-10-15',1),
(15,1,1,'DEMO-TA-15','2026-10-16',1),
(16,1,2,'DEMO-TA-16','2026-10-17',1),
(17,1,3,'DEMO-TA-17','2026-10-18',1),
(18,1,4,'DEMO-TA-18','2026-10-19',1),
(19,1,5,'DEMO-TA-19','2026-10-20',1),
(20,1,6,'DEMO-TA-20','2026-10-21',1),
(21,1,7,'DEMO-TA-21','2026-10-22',1),
(22,1,1,'DEMO-TA-22','2026-10-23',1),
(23,1,2,'DEMO-TA-23','2026-10-24',1);
INSERT OR IGNORE INTO tutor_review_scores (review_id,criterion,score) VALUES
(1,'Clear explanations',5),
(1,'Patience',5),
(1,'Prepared for the session',5),
(1,'Uses worked examples',5),
(1,'Arrives on time',5),
(2,'Clear explanations',5),
(2,'Patience',5),
(2,'Prepared for the session',5),
(2,'Uses worked examples',5),
(2,'Arrives on time',5),
(3,'Clear explanations',5),
(3,'Patience',5),
(3,'Prepared for the session',5),
(3,'Uses worked examples',5),
(3,'Arrives on time',5),
(4,'Clear explanations',5),
(4,'Patience',5),
(4,'Prepared for the session',5),
(4,'Uses worked examples',5),
(4,'Arrives on time',5),
(5,'Clear explanations',5),
(5,'Patience',5),
(5,'Prepared for the session',5),
(5,'Uses worked examples',5),
(5,'Arrives on time',5),
(6,'Clear explanations',5),
(6,'Patience',5),
(6,'Prepared for the session',5),
(6,'Uses worked examples',5),
(6,'Arrives on time',5),
(7,'Clear explanations',5),
(7,'Patience',5),
(7,'Prepared for the session',5),
(7,'Uses worked examples',5),
(7,'Arrives on time',5),
(8,'Clear explanations',5),
(8,'Patience',5),
(8,'Prepared for the session',5),
(8,'Uses worked examples',5),
(8,'Arrives on time',5),
(9,'Clear explanations',5),
(9,'Patience',5),
(9,'Prepared for the session',5),
(9,'Uses worked examples',5),
(9,'Arrives on time',5),
(10,'Clear explanations',5),
(10,'Patience',5),
(10,'Prepared for the session',5),
(10,'Uses worked examples',5),
(10,'Arrives on time',4),
(11,'Clear explanations',5),
(11,'Patience',5),
(11,'Prepared for the session',5),
(11,'Uses worked examples',5),
(11,'Arrives on time',4),
(12,'Clear explanations',5),
(12,'Patience',5),
(12,'Prepared for the session',5),
(12,'Uses worked examples',5),
(12,'Arrives on time',4),
(13,'Clear explanations',5),
(13,'Patience',5),
(13,'Prepared for the session',5),
(13,'Uses worked examples',5),
(13,'Arrives on time',4),
(14,'Clear explanations',5),
(14,'Patience',5),
(14,'Prepared for the session',5),
(14,'Uses worked examples',5),
(14,'Arrives on time',4),
(15,'Clear explanations',5),
(15,'Patience',5),
(15,'Prepared for the session',5),
(15,'Uses worked examples',5),
(15,'Arrives on time',4),
(16,'Clear explanations',5),
(16,'Patience',5),
(16,'Prepared for the session',5),
(16,'Uses worked examples',5),
(16,'Arrives on time',4),
(17,'Clear explanations',5),
(17,'Patience',5),
(17,'Prepared for the session',4),
(17,'Uses worked examples',5),
(17,'Arrives on time',4),
(18,'Clear explanations',5),
(18,'Patience',5),
(18,'Prepared for the session',4),
(18,'Uses worked examples',5),
(18,'Arrives on time',4),
(19,'Clear explanations',5),
(19,'Patience',4),
(19,'Prepared for the session',4),
(19,'Uses worked examples',5),
(19,'Arrives on time',4),
(20,'Clear explanations',5),
(20,'Patience',4),
(20,'Prepared for the session',4),
(20,'Uses worked examples',5),
(20,'Arrives on time',4),
(21,'Clear explanations',5),
(21,'Patience',4),
(21,'Prepared for the session',4),
(21,'Uses worked examples',5),
(21,'Arrives on time',4),
(22,'Clear explanations',4),
(22,'Patience',4),
(22,'Prepared for the session',4),
(22,'Uses worked examples',4),
(22,'Arrives on time',4),
(23,'Clear explanations',4),
(23,'Patience',4),
(23,'Prepared for the session',4),
(23,'Uses worked examples',4),
(23,'Arrives on time',3);
INSERT OR IGNORE INTO tutor_certificates (tutor_id,certificate_id,status,progress_value,earned_date) VALUES
(1,1,'earned',5,'2026-11-12'),(1,2,'earned',5,'2026-11-05'),(1,3,'earned',10,'2026-10-28'),(1,4,'earned',10,'2026-10-20'),(1,5,'in_progress',6,NULL),(1,6,'in_progress',3,NULL);
PRAGMA user_version = 4;
COMMIT;
"""

# (target_version, script). Append new migrations here.
MIGRATIONS = [
    (1, MIGRATION_1_USERS),
    (2, MIGRATION_2_DUAL_ROLE),
    (3, MIGRATION_3_SESSIONS),
    (4, MIGRATION_4_TUTOR_PROFILES),
]


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
