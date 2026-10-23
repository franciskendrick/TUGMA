
from src.logic import CompatibilityLogic


def test_compatibility_from_database():
    logic = CompatibilityLogic()

    try:
        tutor = logic.sets.db.fetch_one(
            "SELECT tutor_id FROM tutors ORDER BY tutor_id LIMIT 1"
        )

        student = logic.sets.db.fetch_one(
            "SELECT student_id FROM students ORDER BY student_id LIMIT 1"
        )

        assert tutor is not None, "No tutors found in the database."
        assert student is not None, "No students found in the database."

        result = logic.explain(
            tutor["tutor_id"],
            student["student_id"]
        )

        # The result must be deterministic and contain all predicates.
        assert isinstance(result["subject_match"], bool)
        assert isinstance(result["time_match"], bool)
        assert isinstance(result["language_match"], bool)

        assert result["compatible"] == (
            result["subject_match"]
            and result["time_match"]
            and result["language_match"]
        )

    finally:
        logic.close()


if __name__ == "__main__":
    test_compatibility_from_database()
    print("\nDatabase-backed predicate logic test passed.")
