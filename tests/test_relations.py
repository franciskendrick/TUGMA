
from src.relations import CompatibilityRelation


def test_compatibility_relation():
    compatibility = CompatibilityRelation()

    try:
        tutors = compatibility.get_tutors()
        students = compatibility.get_students()

        relation = compatibility.construct_relation()

        # Every relation pair must contain an existing tutor and student.
        assert all(
            tutor_id in tutors and student_id in students
            for tutor_id, student_id in relation
        )

        # No duplicate pairs should exist.
        assert len(relation) == len(set(relation))

        # Every included pair must satisfy the compatibility predicate.
        for tutor_id, student_id in relation:
            result = compatibility.logic.evaluate(
                tutor_id,
                student_id
            )

            assert result["compatible"] is True

        # The relation cannot contain more pairs than T x S.
        assert len(relation) <= len(tutors) * len(students)

        compatibility.display_relation()

    finally:
        compatibility.close()


if __name__ == "__main__":
    test_compatibility_relation()
    print("\nCompatibility relation test passed.")
