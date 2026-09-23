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
    student_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    grade_level INTEGER NOT NULL CHECK (grade_level > 0),
    course      TEXT NOT NULL
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
-- END OF SCHEMA
-- ============================================================