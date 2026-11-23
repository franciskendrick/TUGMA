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
INSERT INTO students
    (student_id, name, grade_level, course,
     bio, study_notes, interests,
     learning_style, preferred_setup, free_time)
VALUES
    (1, 'Angelo Bautista', 2, 'BCS',
     'Second-year Computer Science student. I learn best from worked examples and am looking for help with Discrete Structures and Number Theory this term.',
     'Prefers a short recap at the start of each session, then guided practice problems. Brings his own problem sets.',
     'Chess, Basketball, Mobile photography',
     'Worked examples', 'Online or face-to-face', 'Tue 1:00-2:00 PM'),
    (2, 'Bianca Mendoza', 2, 'BCS',
     'CS sophomore focusing on Discrete Structures 1. I like step-by-step walkthroughs before attempting exercises on my own.',
     'Needs practice sets between sessions. Avoids pure lecture-style review.',
     'Reading, Badminton, Podcasts',
     'Step-by-step walkthroughs', 'Online', 'Mon 7:00-8:00 PM'),
    (3, 'Carlo Navarro', 2, 'BIT',
     'BIT student working through Object-Oriented Programming. I respond well to live coding and small debugging drills.',
     'Bring a debugger; prefers to type the solution himself after seeing one example.',
     'Gaming, Coffee brewing, Cycling',
     'Live coding', 'Face-to-face', 'Wed 4:00-5:00 PM'),
    (4, 'Danica Ramos', 1, 'BCS',
     'First-year CS student taking Fundamentals of Programming. Still building confidence with syntax and problem decomposition.',
     'Needs encouragement and short check-ins. Benefits from pseudocode before code.',
     'Drawing, K-dramas, Journaling',
     'Scaffolded practice', 'Online', 'Thu 6:00-7:00 PM'),
    (5, 'Enrico Castillo', 2, 'BIT',
     'BIT student looking for support with Information Management. Interested in database design and normalisation.',
     'Prefers ERD-first explanations. Likes quick quizzes at the end of a session.',
     'Chess, Tabletop games, Running',
     'Concept-first, then practice', 'Online or face-to-face', 'Fri 5:00-6:00 PM'),
    (6, 'Francesca Aquino', 2, 'BCS',
     'Second-year CS student juggling Discrete Structures 1 and Data Structures and Algorithms. Wants worked examples for both.',
     'Requests a 5-minute recap, then two worked examples, then independent practice.',
     'Reading, Photography, Hiking',
     'Worked examples', 'Online or face-to-face', 'Tue 8:00-9:00 AM'),
    (7, 'Gabriel Salazar', 2, 'BCS',
     'CS student focusing on Discrete Structures 1. Prefers explanations in Filipino with English technical terms.',
     'Needs bilingual explanations. Brings past quiz items to review.',
     'Basketball, Music production, Cooking',
     'Bilingual explanations', 'Face-to-face', 'Tue 6:00-7:00 PM');

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

-- ============================================================
-- 10. TUTOR REVIEWS (fictional demo data)
-- ============================================================
INSERT INTO tutor_reviews
    (tutor_id, student_id, session_reference, review_date, is_demo)
VALUES
    (1, 1, 'S-2026-001', '2026-10-05', 1),
    (1, 2, 'S-2026-002', '2026-10-12', 1),
    (1, 6, 'S-2026-003', '2026-10-19', 1),
    (1, 7, 'S-2026-004', '2026-10-26', 1),
    (1, 1, 'S-2026-005', '2026-11-02', 1),
    (1, 2, 'S-2026-006', '2026-11-09', 1),
    (1, 6, 'S-2026-007', '2026-11-16', 1),
    (1, 7, 'S-2026-008', '2026-11-23', 1),
    (1, 1, 'S-2026-009', '2026-11-30', 1),
    (1, 2, 'S-2026-010', '2026-12-07', 1),
    (1, 6, 'S-2026-011', '2026-12-14', 1),
    (1, 7, 'S-2026-012', '2026-12-21', 1),
    (1, 1, 'S-2026-013', '2027-01-04', 1),
    (1, 2, 'S-2026-014', '2027-01-11', 1),
    (1, 6, 'S-2026-015', '2027-01-18', 1),
    (1, 7, 'S-2026-016', '2027-01-25', 1),
    (1, 1, 'S-2026-017', '2027-02-01', 1),
    (1, 2, 'S-2026-018', '2027-02-08', 1),
    (1, 6, 'S-2026-019', '2027-02-15', 1),
    (1, 7, 'S-2026-020', '2027-02-22', 1),
    (1, 1, 'S-2026-021', '2027-03-01', 1),
    (1, 2, 'S-2026-022', '2027-03-08', 1),
    (1, 6, 'S-2026-023', '2027-03-15', 1),
    (2, 2, 'S-2026-101', '2026-11-04', 1),
    (2, 6, 'S-2026-102', '2026-11-11', 1),
    (2, 1, 'S-2026-103', '2026-11-18', 1),
    (2, 7, 'S-2026-104', '2026-11-25', 1),
    (2, 2, 'S-2026-105', '2026-12-02', 1);

-- ============================================================
-- 11. TUTOR REVIEW SCORES (5 criteria per review, 4–5 scores)
-- ============================================================
INSERT INTO tutor_review_scores (review_id, criterion, score)
SELECT r.review_id, s.criterion, s.score
FROM tutor_reviews r
JOIN (
    SELECT 'S-2026-001' AS ref, 'Clear explanations'         AS criterion, 5 AS score UNION ALL
    SELECT 'S-2026-001', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-001', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-001', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-001', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-002', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-002', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-002', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-002', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-002', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-003', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-003', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-003', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-003', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-003', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-004', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-004', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-004', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-004', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-004', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-005', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-005', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-005', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-005', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-005', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-006', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-006', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-006', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-006', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-006', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-007', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-007', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-007', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-007', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-007', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-008', 'Clear explanations',                4 UNION ALL
    SELECT 'S-2026-008', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-008', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-008', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-008', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-009', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-009', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-009', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-009', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-009', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-010', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-010', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-010', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-010', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-010', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-011', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-011', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-011', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-011', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-011', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-012', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-012', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-012', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-012', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-012', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-013', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-013', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-013', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-013', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-013', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-014', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-014', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-014', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-014', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-014', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-015', 'Clear explanations',                4 UNION ALL
    SELECT 'S-2026-015', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-015', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-015', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-015', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-016', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-016', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-016', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-016', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-016', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-017', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-017', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-017', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-017', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-017', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-018', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-018', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-018', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-018', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-018', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-019', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-019', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-019', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-019', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-019', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-020', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-020', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-020', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-020', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-020', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-021', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-021', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-021', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-021', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-021', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-022', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-022', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-022', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-022', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-022', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-023', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-023', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-023', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-023', 'Uses worked examples',              5 UNION ALL
    SELECT 'S-2026-023', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-101', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-101', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-101', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-101', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-101', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-102', 'Clear explanations',                4 UNION ALL
    SELECT 'S-2026-102', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-102', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-102', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-102', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-103', 'Clear explanations',                4 UNION ALL
    SELECT 'S-2026-103', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-103', 'Prepared for the session',          5 UNION ALL
    SELECT 'S-2026-103', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-103', 'Arrives on time',                   5 UNION ALL

    SELECT 'S-2026-104', 'Clear explanations',                4 UNION ALL
    SELECT 'S-2026-104', 'Patience',                          4 UNION ALL
    SELECT 'S-2026-104', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-104', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-104', 'Arrives on time',                   4 UNION ALL

    SELECT 'S-2026-105', 'Clear explanations',                5 UNION ALL
    SELECT 'S-2026-105', 'Patience',                          5 UNION ALL
    SELECT 'S-2026-105', 'Prepared for the session',          4 UNION ALL
    SELECT 'S-2026-105', 'Uses worked examples',              4 UNION ALL
    SELECT 'S-2026-105', 'Arrives on time',                   4
) AS s ON r.session_reference = s.ref;

-- ============================================================
-- 12. CERTIFICATE CATALOG
-- ============================================================
INSERT INTO certificates
    (certificate_code, title, category, tier, description, requirement_label, target_value)
VALUES
    ('TEACH-CLEAR-GOLD',    'Clear Explainer',          'teaching',  'Gold',
     'Rated 4.9 or higher on clear explanations across 20 sessions.',
     'Rated 4.9 on clear explanations across 20 sessions', 20),
    ('TEACH-PATIENT-SILVER','Patient Guide',            'teaching',  'Silver',
     'Rated 4.8 or higher on patience by 10 students.',
     'Rated 4.8 on patience by 10 students', 10),
    ('TEACH-WORKED-SILVER', 'Worked-Example Pro',       'teaching',  'Silver',
     'Students praised worked examples 10 times.',
     'Students praised worked examples 10 times', 10),
    ('TEACH-PUNCTUAL-BRONZE','Always On Time',          'teaching',  'Bronze',
     'Rated 4.5 or higher on punctuality across 10 sessions.',
     'Rated 4.5 on punctuality across 10 sessions', 10),
    ('SUBJ-DS-BRONZE',      'Discrete Structures Tutor','subject',   'Bronze',
     'Subject certificate: 4.8 average in 5 sessions.',
     '4.8 average in 5 sessions', 5),
    ('SUBJ-DSA-BRONZE',     'Data Structures Tutor',    'subject',   'Bronze',
     'Subject certificate: 4.5 average in 5 sessions.',
     '4.5 average in 5 sessions', 5),
    ('MILESTONE-10',        '10 Sessions',              'milestone', 'Bronze',
     'Completed 10 tutoring sessions.',
     '10 completed sessions', 10),
    ('MILESTONE-25',        '25 Sessions',              'milestone', 'Silver',
     'Completed 25 tutoring sessions.',
     '25 completed sessions', 25);

-- ============================================================
-- 13. TUTOR CERTIFICATE AWARDS
-- ============================================================
INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'earned', c.target_value, '2026-11-12'
FROM certificates c WHERE c.certificate_code = 'TEACH-CLEAR-GOLD';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'earned', c.target_value, '2026-11-05'
FROM certificates c WHERE c.certificate_code = 'TEACH-PATIENT-SILVER';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'earned', c.target_value, '2026-10-28'
FROM certificates c WHERE c.certificate_code = 'TEACH-WORKED-SILVER';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'earned', c.target_value, '2026-10-20'
FROM certificates c WHERE c.certificate_code = 'SUBJ-DS-BRONZE';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'in_progress', 6, NULL
FROM certificates c WHERE c.certificate_code = 'TEACH-PUNCTUAL-BRONZE';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 1, c.certificate_id, 'in_progress', 3, NULL
FROM certificates c WHERE c.certificate_code = 'SUBJ-DSA-BRONZE';

INSERT INTO tutor_certificates (tutor_id, certificate_id, status, progress_value, earned_date)
SELECT 2, c.certificate_id, 'earned', c.target_value, '2026-12-10'
FROM certificates c WHERE c.certificate_code = 'MILESTONE-10';