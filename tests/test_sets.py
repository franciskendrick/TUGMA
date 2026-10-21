from src.sets import SetOperations


def test_subject_intersection_from_database():
    operations = SetOperations()

    try:
        tutor = operations.db.fetch_one(
            "SELECT tutor_id FROM tutors LIMIT 1"
        )

        student = operations.db.fetch_one(
            "SELECT student_id FROM students LIMIT 1"
        )

        assert tutor is not None, "No tutors found in database."
        assert student is not None, "No students found in database."

        tutor_subjects = operations.get_tutor_subjects(
            tutor["tutor_id"]
        )

        student_needs = operations.get_student_needs(
            student["student_id"]
        )

        result = operations.subject_intersection(
            tutor_subjects,
            student_needs
        )

        print("Tutor Subjects:", tutor_subjects)
        print("Student Needs:", student_needs)
        print("Subject Intersection:", result)

    finally:
        operations.close()


if __name__ == "__main__":
    test_subject_intersection_from_database()
    print("Database-backed subject test completed.")