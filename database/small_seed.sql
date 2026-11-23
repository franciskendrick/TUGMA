-- TUGMA small seed: 7 students and 5 tutors with Filipino names.
-- Same data as the original controlled seed; only the names changed.
-- Rename to database/seed.sql (and rebuild the database) to use it.

PRAGMA foreign_keys = ON;

-- 1. SUBJECTS
INSERT INTO subjects (subject_id, subject_code, subject_name) VALUES
    (1, 'S-ITCS111', 'INTRODUCTION TO COMPUTING'),
    (2, 'S-ITCS112', 'FUNDAMENTALS OF PROGRAMMING'),
    (3, 'S-ITCS123', 'INTERMEDIATE PROGRAMMING'),
    (4, 'S-ITCS214', 'DATA STRUCTURES AND ALGORITHMS'),
    (5, 'S-ITCS215', 'HUMAN COMPUTER INTERACTION'),
    (6, 'S-ITCS226', 'INFORMATION MANAGEMENT'),
    (7, 'S-ITCS227', 'APPLICATION DEVELOPMENT AND EMERGING TECHNOLOGIES'),
    (8, 'S-ITCS318', 'INFORMATION ASSURANCE AND SECURITY 1'),
    (9, 'S-ITCS329', 'SOCIAL ISSUES AND PROFESSIONAL PRACTICE'),
    (10, 'S-CSPC121', 'OBJECT-ORIENTED PROGRAMMING'),
    (11, 'S-CSPC212', 'DISCRETE STRUCTURES 1'),
    (12, 'S-CSPC223', 'PROGRAMMING LANGUAGES'),
    (13, 'S-CSPC224', 'DISCRETE STRUCTURES 2'),
    (14, 'S-CSPC315', 'ALGORITHMS AND COMPLEXITY'),
    (15, 'S-CSPC316', 'ARCHITECTURE AND ORGANIZATION'),
    (16, 'S-CSPC327', 'AUTOMATA THEORY AND FORMAL LANGUAGES'),
    (17, 'S-CSPC428', 'NETWORKS AND COMMUNICATIONS'),
    (18, 'S-CSPC429', 'OPERATING SYSTEMS');

-- 2. STUDENTS
INSERT INTO students (student_id, name, grade_level, course) VALUES
    (1, 'Angelo Bautista', 2, 'BCS'),
    (2, 'Bianca Mendoza', 2, 'BCS'),
    (3, 'Carlo Navarro', 2, 'BIT'),
    (4, 'Danica Ramos', 1, 'BCS'),
    (5, 'Enrico Castillo', 2, 'BIT'),
    (6, 'Francesca Aquino', 2, 'BCS'),
    (7, 'Gabriel Salazar', 2, 'BCS');

-- 3. TUTORS
INSERT INTO tutors (tutor_id, name, grade_level, course, verified) VALUES
    (1, 'Aldrin Pascual', 3, 'BCS', 1),
    (2, 'Beatriz Manalo', 3, 'BCS', 1),
    (3, 'Carmina Gonzales', 3, 'BIT', 1),
    (4, 'Dennis Garcia', 2, 'BCS', 1),
    (5, 'Erika Villareal', 3, 'BCS', 1);

-- 4. STUDENT SUBJECT NEEDS
INSERT INTO student_subjects (student_id, subject_id) VALUES
    (1, 11),
    (2, 11),
    (3, 10),
    (4, 2),
    (5, 6),
    (6, 11),
    (6, 4),
    (7, 11);

-- 5. TUTOR SUBJECTS
INSERT INTO tutor_subjects (tutor_id, subject_id) VALUES
    (1, 11),
    (2, 11),
    (3, 10),
    (4, 2),
    (5, 4);

-- 6. STUDENT LANGUAGES
INSERT INTO student_languages (student_id, language) VALUES
    (1, 'Filipino'), (1, 'English'),
    (2, 'English'),
    (3, 'Filipino'),
    (4, 'English'),
    (5, 'Filipino'),
    (6, 'Filipino'), (6, 'English'),
    (7, 'Filipino');

-- 7. TUTOR LANGUAGES
INSERT INTO tutor_languages (tutor_id, language) VALUES
    (1, 'Filipino'), (1, 'English'),
    (2, 'English'),
    (3, 'Filipino'),
    (4, 'English'),
    (5, 'Filipino'), (5, 'English');

-- 8. STUDENT ACADEMIC SCHEDULE
INSERT INTO student_schedule
    (schedule_id, student_id, day, start_time, end_time, subject_id)
VALUES
    (1, 1, 'Monday', '10:00', '12:00', 11),
    (2, 2, 'Tuesday', '08:00', '10:00', 11),
    (3, 3, 'Wednesday', '09:00', '11:00', 10),
    (4, 4, 'Thursday', '08:00', '10:00', 2),
    (5, 5, 'Friday', '08:00', '10:00', 6),
    (6, 6, 'Monday', '08:00', '09:00', 11),
    (7, 6, 'Tuesday', '08:00', '09:00', 4),
    (8, 7, 'Tuesday', '08:00', '10:00', 11);

-- 9. TUTOR AVAILABILITY
INSERT INTO tutor_availability
    (availability_id, tutor_id, day, start_time, end_time)
VALUES
    (1, 1, 'Monday', '10:00', '12:00'),
    (2, 1, 'Monday', '09:00', '11:00'),
    (3, 2, 'Tuesday', '10:00', '12:00'),
    (4, 2, 'Tuesday', '10:00', '12:00'),
    (5, 2, 'Monday', '09:00', '11:00'),
    (6, 3, 'Wednesday', '13:00', '15:00'),
    (7, 4, 'Thursday', '10:00', '12:00'),
    (8, 5, 'Tuesday', '09:00', '11:00');

-- Expected edge cases (checked against the matching engine):
-- A. Normal compatibility: Carlo Navarro <-> Carmina Gonzales (Object-Oriented
--    Programming, Filipino, Wednesday afternoon). Dennis Garcia <-> Danica Ramos likewise.
-- B. No subject match: Enrico Castillo needs Information Management and no tutor
--    teaches it, so he is always unmatched.
-- C. Partial time overlap: Angelo Bautista has class Monday 10:00-12:00 and
--    Aldrin Pascual lists Monday 10:00-12:00, which alone would conflict. His second
--    row, Monday 09:00-11:00, overlaps Angelo's free 09:00-10:00, so they ARE
--    compatible. Any overlap counts; there is no minimum session length.
-- D. Language conflict: Gabriel Salazar (Filipino only) <-> Beatriz Manalo (English
--    only) match on subject and time but share no language. Gabriel can only be
--    matched with Aldrin Pascual.
-- E. Multiple compatible tutors: Bianca Mendoza (and Angelo Bautista) can use
--    Aldrin Pascual or Beatriz Manalo for Discrete Structures 1.
-- F. Multiple subjects: Francesca Aquino needs Discrete Structures 1 and Data
--    Structures and Algorithms; she is compatible with Aldrin Pascual, Beatriz Manalo
--    and Erika Villareal. She still receives only one tutor in the matching.
-- G. Unmatched student: Enrico Castillo (see B).
-- H. Capacity: tutors use the schema default of 5, so capacity never binds here.
--    Use the same-capacity setting (for example 1 per tutor) to see students left out.