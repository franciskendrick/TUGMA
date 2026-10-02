# Processes student schedules and tutor availability.
# Determines which time slots can be used for tutoring.

from datetime import datetime, time
from src.database import Database


class ScheduleManager:
    # Handles academic schedules and available tutoring times.

    DEFAULT_DAY_START = time(7, 0)  # start: 7am
    DEFAULT_DAY_END = time(17, 0)  # end: 5pm

    DAY_ORDER = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    def __init__(self, database=None):
        self.db = database if database is not None else Database()

    # Helper methods ------------------------------------------
    @staticmethod
    def _to_time(value):
        """Convert HH:MM text into a datetime.time object."""
        if isinstance(value, time):
            return value

        return datetime.strptime(value, "%H:%M").time()

    @staticmethod
    def _format_time(value):
        """Convert a datetime.time object into HH:MM text."""
        return value.strftime("%H:%M")

    @staticmethod
    def _overlap(start1, end1, start2, end2):
        """Return the overlapping interval between two time ranges."""

        start = max(start1, start2)
        end = min(end1, end2)

        if start >= end:
            return None

        return start, end

    # Retrieve student's classes
    def get_student_schedule(self, student_id):
        """Retrieve all classes belonging to a student."""

        query = """
            SELECT
                ss.day,
                ss.start_time,
                ss.end_time,
                s.subject_code,
                s.subject_name
            FROM student_schedule ss
            JOIN subjects s
                ON ss.subject_id = s.subject_id
            WHERE ss.student_id = ?
            ORDER BY
                CASE ss.day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                END,
                ss.start_time
        """

        rows = self.db.fetch_all(query, (student_id,))

        schedule = []

        for row in rows:
            schedule.append({
                "day": row["day"],
                "start_time": self._to_time(row["start_time"]),
                "end_time": self._to_time(row["end_time"]),
                "subject_code": row["subject_code"],
                "subject_name": row["subject_name"],
            })

        return schedule

    # Determine student's free time
    def get_student_free_slots(
        self,
        student_id,
        day_start=None,
        day_end=None
    ):
        """
        Determine when a student is free.

        The default tutoring window is 08:00–18:00.
        This can be changed when calling the method.
        """

        if day_start is None:
            day_start = self.DEFAULT_DAY_START

        if day_end is None:
            day_end = self.DEFAULT_DAY_END

        schedule = self.get_student_schedule(student_id)

        free_slots = []

        for day in self.DAY_ORDER:
            classes = [
                item for item in schedule
                if item["day"] == day
            ]

            if not classes:
                free_slots.append({
                    "day": day,
                    "start_time": day_start,
                    "end_time": day_end,
                })
                continue

            current_time = day_start

            for class_item in classes:
                class_start = max(
                    class_item["start_time"],
                    day_start
                )

                class_end = min(
                    class_item["end_time"],
                    day_end
                )

                # Ignore classes outside the tutoring window.
                if class_end <= day_start or class_start >= day_end:
                    continue

                # Free time before this class.
                if current_time < class_start:
                    free_slots.append({
                        "day": day,
                        "start_time": current_time,
                        "end_time": class_start,
                    })

                # Move past the class.
                if class_end > current_time:
                    current_time = class_end

            # Free time after the final class.
            if current_time < day_end:
                free_slots.append({
                    "day": day,
                    "start_time": current_time,
                    "end_time": day_end,
                })

        return free_slots

    # Retrieve tutor availability
    def get_tutor_available_slots(self, tutor_id):
        """Retrieve all availability periods belonging to a tutor."""

        query = """
            SELECT
                day,
                start_time,
                end_time
            FROM tutor_availability
            WHERE tutor_id = ?
            ORDER BY
                CASE day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                END,
                start_time
        """

        rows = self.db.fetch_all(query, (tutor_id,))

        availability = []

        for row in rows:
            availability.append({
                "day": row["day"],
                "start_time": self._to_time(row["start_time"]),
                "end_time": self._to_time(row["end_time"]),
            })

        return availability

    # Calculate common available times
    def find_common_slots(self, tutor, student):
        """
        Find common available periods between a tutor and a student.

        tutor and student are IDs.
        """

        student_free = self.get_student_free_slots(student)
        tutor_available = self.get_tutor_available_slots(tutor)

        common_slots = []

        for student_slot in student_free:
            for tutor_slot in tutor_available:

                if student_slot["day"] != tutor_slot["day"]:
                    continue

                overlap = self._overlap(
                    student_slot["start_time"],
                    student_slot["end_time"],
                    tutor_slot["start_time"],
                    tutor_slot["end_time"],
                )

                if overlap is None:
                    continue

                start, end = overlap

                common_slots.append({
                    "day": student_slot["day"],
                    "start_time": start,
                    "end_time": end,
                })

        return common_slots

    # Check schedule conflict
    def has_schedule_conflict(self, student, slot):
        """
        Check whether a proposed tutoring slot conflicts
        with any of the student's classes.

        slot must contain:
            day
            start_time
            end_time
        """

        schedule = self.get_student_schedule(student)

        slot_start = self._to_time(slot["start_time"])
        slot_end = self._to_time(slot["end_time"])

        for class_item in schedule:

            if class_item["day"] != slot["day"]:
                continue

            overlap = self._overlap(
                class_item["start_time"],
                class_item["end_time"],
                slot_start,
                slot_end,
            )

            if overlap is not None:
                return True

        return False

    # Utility -------------------------------------------------
    def close(self):
        """Close the database connection."""
        self.db.close()