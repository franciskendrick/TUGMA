# Implements the Set Theory portion of TUGMA.
# Performs intersections between tutor and student requirements.

from src.database import Database


class SetOperations:
    # Handles set operations for subjects, languages, and availability.

    def __init__(self, database=None):
        if database is None:
            database = Database()

        self.db = database

    def get_tutor_subjects(self, tutor_id):
        """Return the subjects a tutor can teach as a set."""

        query = """
            SELECT s.subject_code
            FROM tutor_subjects ts
            JOIN subjects s
                ON ts.subject_id = s.subject_id
            WHERE ts.tutor_id = ?
        """

        rows = self.db.fetch_all(query, (tutor_id,))

        return {row["subject_code"] for row in rows}

    def get_student_needs(self, student_id):
        """Return the subjects a student needs as a set."""

        query = """
            SELECT s.subject_code
            FROM student_subjects ss
            JOIN subjects s
                ON ss.subject_id = s.subject_id
            WHERE ss.student_id = ?
        """

        rows = self.db.fetch_all(query, (student_id,))

        return {row["subject_code"] for row in rows}

    def get_tutor_languages(self, tutor_id):
        """Return the languages a tutor speaks as a set."""

        query = """
            SELECT language
            FROM tutor_languages
            WHERE tutor_id = ?
        """

        rows = self.db.fetch_all(query, (tutor_id,))

        return {row["language"] for row in rows}

    def get_student_languages(self, student_id):
        """Return the languages a student speaks as a set."""

        query = """
            SELECT language
            FROM student_languages
            WHERE student_id = ?
        """

        rows = self.db.fetch_all(query, (student_id,))

        return {row["language"] for row in rows}

    def subject_intersection(self, tutor_subjects, student_needs):
        """Find subjects the tutor teaches that the student needs."""

        return set(tutor_subjects) & set(student_needs)

    def language_intersection(self, tutor_languages, student_languages):
        """Find languages shared by the tutor and student."""

        return set(tutor_languages) & set(student_languages)

    def availability_intersection(self, student_free, tutor_available):
        """
        Find overlapping available time intervals.

        Each slot must contain:
        day, start_time, and end_time.

        Times can be datetime.time objects or HH:MM strings.
        """

        common_slots = []

        for student_slot in student_free:
            for tutor_slot in tutor_available:

                # Both slots must be on the same day.
                if student_slot["day"] != tutor_slot["day"]:
                    continue

                # Convert times to minutes for comparison.
                student_start = self._to_minutes(
                    student_slot["start_time"]
                )
                student_end = self._to_minutes(
                    student_slot["end_time"]
                )
                tutor_start = self._to_minutes(
                    tutor_slot["start_time"]
                )
                tutor_end = self._to_minutes(
                    tutor_slot["end_time"]
                )

                # Calculate the intersection of the intervals.
                start = max(student_start, tutor_start)
                end = min(student_end, tutor_end)

                if start < end:
                    common_slots.append({
                        "day": student_slot["day"],
                        "start_time": self._to_time_string(start),
                        "end_time": self._to_time_string(end)
                    })

        # Remove duplicate slots and return them in chronological order.
        unique_slots = {
            (
                slot["day"],
                slot["start_time"],
                slot["end_time"]
            )
            for slot in common_slots
        }

        day_order = {
            "Monday": 1,
            "Tuesday": 2,
            "Wednesday": 3,
            "Thursday": 4,
            "Friday": 5,
            "Saturday": 6
        }

        return [
            {
                "day": day,
                "start_time": start,
                "end_time": end
            }
            for day, start, end in sorted(
                unique_slots,
                key=lambda slot: (
                    day_order.get(slot[0], 7),
                    slot[1]
                )
            )
        ]

    def _to_minutes(self, value):
        """Convert a time value to minutes after midnight."""

        if isinstance(value, str):
            hour, minute = map(int, value.split(":"))
        else:
            hour = value.hour
            minute = value.minute

        return hour * 60 + minute

    def _to_time_string(self, minutes):
        """Convert minutes after midnight to HH:MM."""

        hour = minutes // 60
        minute = minutes % 60

        return f"{hour:02d}:{minute:02d}"

    def close(self):
        """Close the database connection."""

        self.db.close()
