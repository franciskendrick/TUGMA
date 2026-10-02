# Processes student schedules and tutor availability.
# Determines which time slots can be used for tutoring.

from datetime import datetime, time
from src.database import Database


class ScheduleManager:
    # Handles academic schedules and available tutoring times.

    DEFAULT_DAY_START = time(7, 0)
    DEFAULT_DAY_END = time(17, 0)
    SLOT_MINUTES = 15

    DAY_ORDER = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    def __init__(self, database=None):
        if database is None:
            database = Database()

        self.db = database

    # Helper methods ------------------------------------------
    def _to_time(self, value):
        """Convert an HH:MM string or time object into a time object."""
        if isinstance(value, time):
            return value

        return datetime.strptime(value, "%H:%M").time()

    def _overlap(self, start1, end1, start2, end2):
        """Return the overlapping time range between two intervals."""
        start = max(start1, start2)
        end = min(end1, end2)

        if start < end:
            return start, end

        return None

    def _round_up_to_15_minutes(self, value):
        """Round a time up to the nearest 15-minute interval."""
        total_minutes = value.hour * 60 + value.minute

        rounded_minutes = (
            (total_minutes + self.SLOT_MINUTES - 1)
            // self.SLOT_MINUTES
        ) * self.SLOT_MINUTES

        if rounded_minutes >= 24 * 60:
            return time(23, 59)

        return time(
            rounded_minutes // 60,
            rounded_minutes % 60
        )

    def _round_down_to_15_minutes(self, value):
        """Round a time down to the nearest 15-minute interval."""
        total_minutes = value.hour * 60 + value.minute

        rounded_minutes = (
            total_minutes // self.SLOT_MINUTES
        ) * self.SLOT_MINUTES

        return time(
            rounded_minutes // 60,
            rounded_minutes % 60
        )

    # Retrieve student's classes
    def get_student_schedule(self, student_id):
        """Retrieve a student's class schedule."""

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
            AND ss.day != 'Sunday'
            ORDER BY
                CASE ss.day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
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
        Determine the student's free time from Monday to Saturday.

        The default daily window is 07:00–17:00.
        Free time is represented using 15-minute intervals.
        """

        if day_start is None:
            day_start = self.DEFAULT_DAY_START

        if day_end is None:
            day_end = self.DEFAULT_DAY_END

        day_start = self._to_time(day_start)
        day_end = self._to_time(day_end)

        schedule = self.get_student_schedule(student_id)

        free_slots = []

        for day in self.DAY_ORDER:
            day_classes = [
                item
                for item in schedule
                if item["day"] == day
            ]

            current_time = day_start

            for class_item in day_classes:
                class_start = max(
                    class_item["start_time"],
                    day_start
                )

                class_end = min(
                    class_item["end_time"],
                    day_end
                )

                # Ignore classes completely outside the daily window.
                if class_end <= day_start or class_start >= day_end:
                    continue

                # Add free time before the class.
                if current_time < class_start:
                    free_start = self._round_up_to_15_minutes(
                        current_time
                    )

                    free_end = self._round_down_to_15_minutes(
                        class_start
                    )

                    if free_start < free_end:
                        free_slots.append({
                            "day": day,
                            "start_time": free_start,
                            "end_time": free_end
                        })

                if class_end > current_time:
                    current_time = class_end

            # Add free time after the final class.
            if current_time < day_end:
                free_start = self._round_up_to_15_minutes(
                    current_time
                )

                free_end = self._round_down_to_15_minutes(
                    day_end
                )

                if free_start < free_end:
                    free_slots.append({
                        "day": day,
                        "start_time": free_start,
                        "end_time": free_end
                    })

        return free_slots

    # Retrieve tutor availability
    def get_tutor_available_slots(self, tutor_id):
        """Retrieve tutor availability from Monday to Saturday."""

        query = """
            SELECT
                day,
                start_time,
                end_time
            FROM tutor_availability
            WHERE tutor_id = ?
            AND day != 'Sunday'
            ORDER BY
                CASE day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                END,
                start_time
        """

        rows = self.db.fetch_all(query, (tutor_id,))

        availability = []

        for row in rows:
            start_time = self._to_time(row["start_time"])
            end_time = self._to_time(row["end_time"])

            # Restrict tutor availability to the daily window.
            start_time = max(
                start_time,
                self.DEFAULT_DAY_START
            )

            end_time = min(
                end_time,
                self.DEFAULT_DAY_END
            )

            if start_time >= end_time:
                continue

            # Make availability compatible with 15-minute intervals.
            start_time = self._round_up_to_15_minutes(start_time)
            end_time = self._round_down_to_15_minutes(end_time)

            if start_time < end_time:
                availability.append({
                    "day": row["day"],
                    "start_time": start_time,
                    "end_time": end_time
                })

        return availability

    # Calculate common available times
    def find_common_slots(self, tutor, student):
        """
        Find times when both the tutor and student are available.

        The returned slots are compatible with 15-minute intervals.
        """

        student_free_slots = self.get_student_free_slots(student)
        tutor_slots = self.get_tutor_available_slots(tutor)

        common_slots = []

        for student_slot in student_free_slots:
            for tutor_slot in tutor_slots:

                if student_slot["day"] != tutor_slot["day"]:
                    continue

                overlap = self._overlap(
                    student_slot["start_time"],
                    student_slot["end_time"],
                    tutor_slot["start_time"],
                    tutor_slot["end_time"]
                )

                if overlap is None:
                    continue

                start_time, end_time = overlap

                start_time = self._round_up_to_15_minutes(
                    start_time
                )

                end_time = self._round_down_to_15_minutes(
                    end_time
                )

                if start_time < end_time:
                    common_slots.append({
                        "day": student_slot["day"],
                        "start_time": start_time,
                        "end_time": end_time
                    })

        return common_slots

    # Check schedule conflict
    def has_schedule_conflict(self, student, slot):
        """Check whether a proposed tutoring slot conflicts with a class."""

        schedule = self.get_student_schedule(student)

        slot_day = slot["day"]
        slot_start = self._to_time(slot["start_time"])
        slot_end = self._to_time(slot["end_time"])

        for class_item in schedule:

            if class_item["day"] != slot_day:
                continue

            conflict = self._overlap(
                slot_start,
                slot_end,
                class_item["start_time"],
                class_item["end_time"]
            )

            if conflict is not None:
                return True

        return False

    # Utility -------------------------------------------------
    def close(self):
        """Close the database connection."""
        self.db.close()