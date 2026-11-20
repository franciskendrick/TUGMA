-- Controlled Seed Data

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
    (1, 'Student A', 2, 'BCS'),
    (2, 'Student B', 2, 'BCS'),
    (3, 'Student C', 2, 'BIT'),
    (4, 'Student D', 1, 'BCS'),
    (5, 'Student E', 2, 'BIT'),
    (6, 'Student F', 2, 'BCS'),
    (7, 'Student G', 2, 'BCS');

-- 3. TUTORS
INSERT INTO tutors (tutor_id, name, grade_level, course, verified) VALUES
    (1, 'Tutor A', 3, 'BCS', 1),
    (2, 'Tutor B', 3, 'BCS', 1),
    (3, 'Tutor C', 3, 'BIT', 1),
    (4, 'Tutor D', 2, 'BCS', 1),
    (5, 'Tutor E', 3, 'BCS', 1);

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

-- Expected edge cases:
-- A. Normal compatibility: Student C ↔ Tutor C.
-- B. No subject match: Student E has Information Management;
--    no tutor teaches it, so Student E is unmatched.
-- C. Schedule conflict: Student A ↔ Tutor A has the same
--    Monday 10:00–12:00 interval, so TimeMatch is false.
-- D. Language conflict: Student G ↔ Tutor B has compatible
--    subject/time but Filipino ∩ English = ∅.
-- E. Multiple compatible tutors: Student B can use Tutor A
--    or Tutor B for Discrete Structures 1.
-- F. Multiple subjects: Student F needs Discrete Structures 1
--    and Data Structures and Algorithms.
-- G. Unmatched student: Student E has no subject-compatible tutor.
-- H. Capacity constraint: apply capacities in matching.py,
--    e.g. c_t = 1 for each tutor, since capacity is not stored here.

-- 10. DEMONSTRATION TUTOR REVIEWS (not genuine student feedback)
-- Seven existing demo students contribute 23 sample session reviews for Tutor A.
-- Each review has all five teaching criteria; no student/tutor matching data is changed.
INSERT INTO tutor_reviews (tutor_id, student_id, session_reference, review_date, is_demo) VALUES
    (1, 1, 'DEMO-TA-01', '2026-10-02', 1),
    (1, 2, 'DEMO-TA-02', '2026-10-03', 1),
    (1, 3, 'DEMO-TA-03', '2026-10-04', 1),
    (1, 4, 'DEMO-TA-04', '2026-10-05', 1),
    (1, 5, 'DEMO-TA-05', '2026-10-06', 1),
    (1, 6, 'DEMO-TA-06', '2026-10-07', 1),
    (1, 7, 'DEMO-TA-07', '2026-10-08', 1),
    (1, 1, 'DEMO-TA-08', '2026-10-09', 1),
    (1, 2, 'DEMO-TA-09', '2026-10-10', 1),
    (1, 3, 'DEMO-TA-10', '2026-10-11', 1),
    (1, 4, 'DEMO-TA-11', '2026-10-12', 1),
    (1, 5, 'DEMO-TA-12', '2026-10-13', 1),
    (1, 6, 'DEMO-TA-13', '2026-10-14', 1),
    (1, 7, 'DEMO-TA-14', '2026-10-15', 1),
    (1, 1, 'DEMO-TA-15', '2026-10-16', 1),
    (1, 2, 'DEMO-TA-16', '2026-10-17', 1),
    (1, 3, 'DEMO-TA-17', '2026-10-18', 1),
    (1, 4, 'DEMO-TA-18', '2026-10-19', 1),
    (1, 5, 'DEMO-TA-19', '2026-10-20', 1),
    (1, 6, 'DEMO-TA-20', '2026-10-21', 1),
    (1, 7, 'DEMO-TA-21', '2026-10-22', 1),
    (1, 1, 'DEMO-TA-22', '2026-10-23', 1),
    (1, 2, 'DEMO-TA-23', '2026-10-24', 1);

INSERT INTO tutor_review_scores (review_id, criterion, score) VALUES
    (1, 'Clear explanations', 5),
    (1, 'Patience', 5),
    (1, 'Prepared for the session', 5),
    (1, 'Uses worked examples', 5),
    (1, 'Arrives on time', 5),
    (2, 'Clear explanations', 5),
    (2, 'Patience', 5),
    (2, 'Prepared for the session', 5),
    (2, 'Uses worked examples', 5),
    (2, 'Arrives on time', 5),
    (3, 'Clear explanations', 5),
    (3, 'Patience', 5),
    (3, 'Prepared for the session', 5),
    (3, 'Uses worked examples', 5),
    (3, 'Arrives on time', 5),
    (4, 'Clear explanations', 5),
    (4, 'Patience', 5),
    (4, 'Prepared for the session', 5),
    (4, 'Uses worked examples', 5),
    (4, 'Arrives on time', 5),
    (5, 'Clear explanations', 5),
    (5, 'Patience', 5),
    (5, 'Prepared for the session', 5),
    (5, 'Uses worked examples', 5),
    (5, 'Arrives on time', 5),
    (6, 'Clear explanations', 5),
    (6, 'Patience', 5),
    (6, 'Prepared for the session', 5),
    (6, 'Uses worked examples', 5),
    (6, 'Arrives on time', 5),
    (7, 'Clear explanations', 5),
    (7, 'Patience', 5),
    (7, 'Prepared for the session', 5),
    (7, 'Uses worked examples', 5),
    (7, 'Arrives on time', 5),
    (8, 'Clear explanations', 5),
    (8, 'Patience', 5),
    (8, 'Prepared for the session', 5),
    (8, 'Uses worked examples', 5),
    (8, 'Arrives on time', 5),
    (9, 'Clear explanations', 5),
    (9, 'Patience', 5),
    (9, 'Prepared for the session', 5),
    (9, 'Uses worked examples', 5),
    (9, 'Arrives on time', 5),
    (10, 'Clear explanations', 5),
    (10, 'Patience', 5),
    (10, 'Prepared for the session', 5),
    (10, 'Uses worked examples', 5),
    (10, 'Arrives on time', 5),
    (11, 'Clear explanations', 5),
    (11, 'Patience', 5),
    (11, 'Prepared for the session', 5),
    (11, 'Uses worked examples', 5),
    (11, 'Arrives on time', 5),
    (12, 'Clear explanations', 5),
    (12, 'Patience', 5),
    (12, 'Prepared for the session', 5),
    (12, 'Uses worked examples', 5),
    (12, 'Arrives on time', 4),
    (13, 'Clear explanations', 5),
    (13, 'Patience', 5),
    (13, 'Prepared for the session', 5),
    (13, 'Uses worked examples', 5),
    (13, 'Arrives on time', 4),
    (14, 'Clear explanations', 5),
    (14, 'Patience', 5),
    (14, 'Prepared for the session', 5),
    (14, 'Uses worked examples', 5),
    (14, 'Arrives on time', 4),
    (15, 'Clear explanations', 5),
    (15, 'Patience', 5),
    (15, 'Prepared for the session', 5),
    (15, 'Uses worked examples', 5),
    (15, 'Arrives on time', 4),
    (16, 'Clear explanations', 5),
    (16, 'Patience', 5),
    (16, 'Prepared for the session', 5),
    (16, 'Uses worked examples', 5),
    (16, 'Arrives on time', 4),
    (17, 'Clear explanations', 5),
    (17, 'Patience', 5),
    (17, 'Prepared for the session', 5),
    (17, 'Uses worked examples', 5),
    (17, 'Arrives on time', 4),
    (18, 'Clear explanations', 5),
    (18, 'Patience', 5),
    (18, 'Prepared for the session', 5),
    (18, 'Uses worked examples', 5),
    (18, 'Arrives on time', 4),
    (19, 'Clear explanations', 5),
    (19, 'Patience', 5),
    (19, 'Prepared for the session', 4),
    (19, 'Uses worked examples', 5),
    (19, 'Arrives on time', 4),
    (20, 'Clear explanations', 5),
    (20, 'Patience', 5),
    (20, 'Prepared for the session', 4),
    (20, 'Uses worked examples', 5),
    (20, 'Arrives on time', 4),
    (21, 'Clear explanations', 5),
    (21, 'Patience', 4),
    (21, 'Prepared for the session', 4),
    (21, 'Uses worked examples', 5),
    (21, 'Arrives on time', 4),
    (22, 'Clear explanations', 4),
    (22, 'Patience', 4),
    (22, 'Prepared for the session', 4),
    (22, 'Uses worked examples', 4),
    (22, 'Arrives on time', 4),
    (23, 'Clear explanations', 4),
    (23, 'Patience', 4),
    (23, 'Prepared for the session', 4),
    (23, 'Uses worked examples', 4),
    (23, 'Arrives on time', 4);

-- 11. CERTIFICATE DEFINITIONS AND TUTOR A PROGRESS
INSERT INTO certificates
    (certificate_id, certificate_code, title, category, tier, description, requirement_label, target_value)
VALUES
    (1, 'CLEAR_EXPLAINER', 'Clear Explainer', 'teaching', 'Gold', 'Recognized for consistently clear explanations across tutoring sessions.', 'Ratings of 4.5+ for clear explanations', 5),
    (2, 'PATIENT_GUIDE', 'Patient Guide', 'teaching', 'Gold', 'Recognized for patience and supportive guidance.', 'Ratings of 4.5+ for patience', 5),
    (3, 'WORKED_EXAMPLE_PRO', 'Worked-Example Pro', 'teaching', 'Silver', 'Uses relevant worked examples to explain difficult concepts.', 'Positive mentions of worked examples', 10),
    (4, 'DISCRETE_STRUCTURES_TUTOR', 'Discrete Structures Tutor', 'subject', 'Silver', 'Subject certificate for Discrete Structures tutoring.', 'Rated sessions in Discrete Structures', 10),
    (5, 'ALWAYS_ON_TIME', 'Always On Time', 'milestone', NULL, 'Punctuality recognition milestone.', 'Ratings of 4.5+ for punctuality', 10),
    (6, 'NUMBER_THEORY_TUTOR', 'Number Theory Tutor', 'subject', NULL, 'Subject certificate for Number Theory tutoring.', 'Rated Number Theory sessions at 4.5+', 5);

INSERT INTO tutor_certificates
    (tutor_id, certificate_id, status, progress_value, earned_date)
VALUES
    (1, 1, 'earned', 5, '2026-11-12'),
    (1, 2, 'earned', 5, '2026-11-05'),
    (1, 3, 'earned', 10, '2026-10-28'),
    (1, 4, 'earned', 10, '2026-10-20'),
    (1, 5, 'in_progress', 6, NULL),
    (1, 6, 'in_progress', 3, NULL);
