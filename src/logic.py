# Implements Propositional and Predicate Logic for determining whether a tutor and student are compatible.
# Applies predicate logic to determine tutor-student compatibility.

from src.sets import SetOperations
from src.scheduling import ScheduleManager


class CompatibilityLogic:
    # Evaluates compatibility and explains the result.

    def __init__(self, set_operations=None, schedule_manager=None):
        self.sets = set_operations or SetOperations()
        self.schedules = schedule_manager or ScheduleManager()

    def subject_match(self, tutor_id, student_id):
        """Check whether the tutor teaches a subject the student needs."""

        tutor_subjects = self.sets.get_tutor_subjects(tutor_id)
        student_needs = self.sets.get_student_needs(student_id)

        common_subjects = self.sets.subject_intersection(
            tutor_subjects,
            student_needs
        )

        return bool(common_subjects)

    def time_match(self, tutor_id, student_id):
        """Check whether the tutor and student share available time."""

        student_free = self.schedules.get_student_free_slots(student_id)
        tutor_available = self.schedules.get_tutor_available_slots(tutor_id)

        common_slots = self.sets.availability_intersection(
            student_free,
            tutor_available
        )

        return bool(common_slots)

    def language_match(self, tutor_id, student_id):
        """Check whether the tutor and student share a language."""

        tutor_languages = self.sets.get_tutor_languages(tutor_id)
        student_languages = self.sets.get_student_languages(student_id)

        common_languages = self.sets.language_intersection(
            tutor_languages,
            student_languages
        )

        return bool(common_languages)

    def evaluate(self, tutor_id, student_id):
        """
        Evaluate all predicates and return a detailed compatibility report.
        """

        subject_result = self.subject_match(tutor_id, student_id)
        time_result = self.time_match(tutor_id, student_id)
        language_result = self.language_match(tutor_id, student_id)

        compatible = (
            subject_result
            and time_result
            and language_result
        )

        return {
            "tutor_id": tutor_id,
            "student_id": student_id,
            "subject_match": subject_result,
            "time_match": time_result,
            "language_match": language_result,
            "compatible": compatible
        }

    def explain(self, tutor_id, student_id):
        """Print a readable explanation of the compatibility result."""

        result = self.evaluate(tutor_id, student_id)

        print(f"Tutor: {result['tutor_id']}")
        print(f"Student: {result['student_id']}")
        print()

        print("Compatibility Report")
        print("--------------------")
        print(
            f"Subject:   {'✓' if result['subject_match'] else '✗'}"
        )
        print(
            f"Schedule:  {'✓' if result['time_match'] else '✗'}"
        )
        print(
            f"Language:  {'✓' if result['language_match'] else '✗'}"
        )
        print()

        if result["compatible"]:
            print("Result: COMPATIBLE")
        else:
            print("Result: INCOMPATIBLE")

        return result

    def close(self):
        """Close database connections used by the components."""

        self.sets.close()

        # Avoid closing the same database connection twice.
        if self.schedules.db is not self.sets.db:
            self.schedules.close()
