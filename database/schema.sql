-- Defines the complete relational structure of the TUGMA database.
--
-- Contains:
--   - Students
--   - Tutors
--   - Subjects
--   - Student/tutor subject relationships
--   - Student/tutor language relationships
--   - Student academic schedules
--   - Tutor availability

PRAGMA foreign_keys = ON;


-- ============================================================
-- 1. STUDENTS
-- ============================================================

CREATE TABLE students (
    student_id      INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    grade_level     INTEGER NOT NULL CHECK (grade_level > 0),
    course          TEXT NOT NULL,
    bio             TEXT,
    study_notes     TEXT,
    interests       TEXT,
    learning_style  TEXT,
    preferred_setup TEXT,
    free_time       TEXT
);


-- ============================================================
-- 2. TUTORS
-- ============================================================

CREATE TABLE tutors (
    tutor_id    INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    grade_level INTEGER NOT NULL CHECK (grade_level > 0),
    course      TEXT NOT NULL,
    verified    INTEGER NOT NULL DEFAULT 0
                CHECK (verified IN (0, 1)),
    capacity    INTEGER NOT NULL DEFAULT 5
                CHECK (capacity > 0)
);


-- ============================================================
-- 3. SUBJECTS
-- ============================================================

CREATE TABLE subjects (
    subject_id   INTEGER PRIMARY KEY,
    subject_code TEXT NOT NULL UNIQUE,
    subject_name TEXT NOT NULL
);


-- ============================================================
-- 4. STUDENT SUBJECT NEEDS
-- ============================================================

CREATE TABLE student_subjects (
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,

    PRIMARY KEY (student_id, subject_id),

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- 5. TUTOR SUBJECTS
-- ============================================================

CREATE TABLE tutor_subjects (
    tutor_id   INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,

    PRIMARY KEY (tutor_id, subject_id),

    FOREIGN KEY (tutor_id)
        REFERENCES tutors(tutor_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- 6. STUDENT LANGUAGES
-- ============================================================

CREATE TABLE student_languages (
    student_id INTEGER NOT NULL,
    language   TEXT NOT NULL,

    PRIMARY KEY (student_id, language),

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- 7. TUTOR LANGUAGES
-- ============================================================

CREATE TABLE tutor_languages (
    tutor_id INTEGER NOT NULL,
    language TEXT NOT NULL,

    PRIMARY KEY (tutor_id, language),

    FOREIGN KEY (tutor_id)
        REFERENCES tutors(tutor_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- 8. STUDENT ACADEMIC SCHEDULE
-- ============================================================

CREATE TABLE student_schedule (
    schedule_id INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL,
    day         TEXT NOT NULL
                CHECK (
                    day IN (
                        'Monday',
                        'Tuesday',
                        'Wednesday',
                        'Thursday',
                        'Friday',
                        'Saturday',
                        'Sunday'
                    )
                ),
    start_time  TEXT NOT NULL
                CHECK (
                    start_time GLOB '[0-2][0-9]:[0-5][0-9]'
                ),
    end_time    TEXT NOT NULL
                CHECK (
                    end_time GLOB '[0-2][0-9]:[0-5][0-9]'
                ),
    subject_id  INTEGER NOT NULL,

    CHECK (start_time < end_time),

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);


-- ============================================================
-- 9. TUTOR AVAILABILITY
-- ============================================================

CREATE TABLE tutor_availability (
    availability_id INTEGER PRIMARY KEY,
    tutor_id        INTEGER NOT NULL,
    day             TEXT NOT NULL
                    CHECK (
                        day IN (
                            'Monday',
                            'Tuesday',
                            'Wednesday',
                            'Thursday',
                            'Friday',
                            'Saturday',
                            'Sunday'
                        )
                    ),
    start_time      TEXT NOT NULL
                    CHECK (
                        start_time GLOB '[0-2][0-9]:[0-5][0-9]'
                    ),
    end_time        TEXT NOT NULL
                    CHECK (
                        end_time GLOB '[0-2][0-9]:[0-5][0-9]'
                    ),

    CHECK (start_time < end_time),

    FOREIGN KEY (tutor_id)
        REFERENCES tutors(tutor_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- ============================================================
-- 10. TUTOR TEACHING REVIEWS AND CRITERION SCORES
-- ============================================================

CREATE TABLE tutor_reviews (
    review_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id          INTEGER NOT NULL REFERENCES tutors(tutor_id)
                      ON DELETE CASCADE ON UPDATE CASCADE,
    student_id        INTEGER NOT NULL REFERENCES students(student_id)
                      ON DELETE CASCADE ON UPDATE CASCADE,
    session_reference TEXT NOT NULL,
    review_date       TEXT NOT NULL,
    is_demo           INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    UNIQUE (tutor_id, session_reference)
);

CREATE TABLE tutor_review_scores (
    review_id   INTEGER NOT NULL REFERENCES tutor_reviews(review_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
    criterion   TEXT NOT NULL CHECK (criterion IN (
                    'Clear explanations',
                    'Patience',
                    'Prepared for the session',
                    'Uses worked examples',
                    'Arrives on time'
                )),
    score       INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    PRIMARY KEY (review_id, criterion)
);

-- ============================================================
-- 11. CERTIFICATE CATALOG AND TUTOR AWARDS
-- ============================================================

CREATE TABLE certificates (
    certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_code TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL CHECK (category IN ('teaching', 'subject', 'milestone')),
    tier            TEXT CHECK (tier IN ('Bronze', 'Silver', 'Gold')),
    description     TEXT NOT NULL,
    requirement_label TEXT NOT NULL,
    target_value    INTEGER NOT NULL CHECK (target_value > 0)
);

CREATE TABLE tutor_certificates (
    tutor_id        INTEGER NOT NULL REFERENCES tutors(tutor_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
    certificate_id INTEGER NOT NULL REFERENCES certificates(certificate_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
    status          TEXT NOT NULL CHECK (status IN ('earned', 'in_progress')),
    progress_value  INTEGER NOT NULL DEFAULT 0 CHECK (progress_value >= 0),
    earned_date     TEXT,
    PRIMARY KEY (tutor_id, certificate_id),
    CHECK (status != 'earned' OR earned_date IS NOT NULL),
    CHECK (status != 'in_progress' OR earned_date IS NULL)
);

-- END OF SCHEMA
-- ============================================================