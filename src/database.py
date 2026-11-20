# Handles all communication between the Python application and SQLite.

import sqlite3
from pathlib import Path


class Database:
    # Manages SQLite database connections and transactions.

    def __init__(self, db_path=None):
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            db_path = project_root / "database" / "tugma.db"
            print(db_path)

        self.db_path = Path(db_path)
        self.connection = None

    def connect(self):
        """Connect to the SQLite database."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")

        return self.connection

    def execute(self, query, parameters=None):
        """Execute INSERT, UPDATE, DELETE, or other non-SELECT queries."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)
        connection.commit()

        return cursor

    def fetch_one(self, query, parameters=None):
        """Execute a SELECT query and return one row."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)

        return cursor.fetchone()

    def fetch_all(self, query, parameters=None):
        """Execute a SELECT query and return all rows."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)

        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    # ------------------------------------------------------ tutor profile data
    def get_tutor_rating_summary(self, tutor_id):
        """Return the overall review average and distinct review counts."""
        return self.fetch_one(
            """
            SELECT ROUND(AVG(review_average), 2) AS overall_rating,
                   COUNT(*) AS rated_sessions,
                   COUNT(DISTINCT student_id) AS rated_students
            FROM (
                SELECT r.review_id, r.student_id, AVG(s.score) AS review_average
                FROM tutor_reviews r
                JOIN tutor_review_scores s ON s.review_id = r.review_id
                WHERE r.tutor_id = ?
                GROUP BY r.review_id, r.student_id
            )
            """,
            (tutor_id,),
        )

    def get_tutor_rating_breakdown(self, tutor_id):
        """Return criterion averages and rating counts for a tutor."""
        return self.fetch_all(
            """
            SELECT criterion, ROUND(AVG(score), 2) AS average_rating,
                   COUNT(*) AS rating_count
            FROM tutor_review_scores scores
            JOIN tutor_reviews reviews USING (review_id)
            WHERE reviews.tutor_id = ?
            GROUP BY criterion
            ORDER BY CASE criterion
                WHEN 'Clear explanations' THEN 1
                WHEN 'Patience' THEN 2
                WHEN 'Prepared for the session' THEN 3
                WHEN 'Uses worked examples' THEN 4
                WHEN 'Arrives on time' THEN 5 ELSE 6 END
            """,
            (tutor_id,),
        )

    def get_tutor_certificates(self, tutor_id):
        """Return earned and in-progress certificates in display order."""
        return self.fetch_all(
            """
            SELECT c.certificate_id, c.certificate_code, c.title, c.category,
                   c.tier, c.description, c.requirement_label, c.target_value,
                   tc.status, tc.progress_value, tc.earned_date
            FROM tutor_certificates tc
            JOIN certificates c USING (certificate_id)
            WHERE tc.tutor_id = ?
            ORDER BY CASE tc.status WHEN 'earned' THEN 0 ELSE 1 END,
                     CASE c.tier WHEN 'Gold' THEN 0 WHEN 'Silver' THEN 1
                                 WHEN 'Bronze' THEN 2 ELSE 3 END,
                     c.title
            """,
            (tutor_id,),
        )

    def get_tutor_profile(self, tutor_id):
        """Fetch the public academic profile fields used by the profile page."""
        return self.fetch_one(
            """
            SELECT tutor_id, name, grade_level, course, verified, capacity
            FROM tutors WHERE tutor_id = ?
            """,
            (tutor_id,),
        )
    # ----------------------------------------------------- student profile data
    def get_student_profile(self, student_id):
        """Fetch student details and the linked account metadata, if available."""
        return self.fetch_one(
            """
            SELECT s.student_id, s.name, s.grade_level, s.course,
                   s.bio, s.study_notes, s.interests,
                   u.email, u.created_at, u.is_active
            FROM students s
            LEFT JOIN users u ON u.student_id = s.student_id
            WHERE s.student_id = ?
            """,
            (student_id,),
        )

    def get_student_subjects(self, student_id):
        """Return the subjects a student registered as needing help with."""
        return self.fetch_all(
            """
            SELECT sub.subject_id, sub.subject_code, sub.subject_name, ss.note
            FROM student_subjects ss
            JOIN subjects sub USING (subject_id)
            WHERE ss.student_id = ?
            ORDER BY sub.subject_code
            """,
            (student_id,),
        )

    def get_student_languages(self, student_id):
        """Return the languages listed on a student's profile."""
        return self.fetch_all(
            "SELECT language FROM student_languages WHERE student_id = ? ORDER BY language",
            (student_id,),
        )

    def get_student_class_schedule(self, student_id):
        """Return the student's registered weekly class schedule."""
        return self.fetch_all(
            """
            SELECT ss.schedule_id, ss.day, ss.start_time, ss.end_time,
                   sub.subject_code, sub.subject_name
            FROM student_schedule ss
            JOIN subjects sub USING (subject_id)
            WHERE ss.student_id = ?
            ORDER BY CASE ss.day
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END,
                ss.start_time
            """,
            (student_id,),
        )

