# Constructs the mathematical compatibility relation between tutors and students.

from src.logic import CompatibilityLogic


class CompatibilityRelation:
    # Builds the relation of compatible tutor-student pairs.

    def __init__(self, logic=None):
        self.logic = logic or CompatibilityLogic()

    def get_tutors(self):
        """Retrieve all tutor IDs from the database."""

        query = """
            SELECT tutor_id
            FROM tutors
            ORDER BY tutor_id
        """

        rows = self.logic.sets.db.fetch_all(query)

        return [row["tutor_id"] for row in rows]

    def get_students(self):
        """Retrieve all student IDs from the database."""

        query = """
            SELECT student_id
            FROM students
            ORDER BY student_id
        """

        rows = self.logic.sets.db.fetch_all(query)

        return [row["student_id"] for row in rows]

    def construct_relation(self):
        """
        Evaluate every pair in T x S.

        Return only pairs for which Compatible(t, s) is True.
        """

        tutors = self.get_tutors()
        students = self.get_students()

        relation = []

        for tutor_id in tutors:
            for student_id in students:

                result = self.logic.evaluate(
                    tutor_id,
                    student_id
                )

                if result["compatible"]:
                    relation.append((tutor_id, student_id))

        return relation

    def display_relation(self):
        """Print the compatibility relation."""

        tutors = self.get_tutors()
        students = self.get_students()
        relation = self.construct_relation()

        print("Compatibility Relation")
        print("----------------------")

        for tutor_id, student_id in relation:
            print(f"({tutor_id}, {student_id})")

        print()
        print(f"Total tutors: {len(tutors)}")
        print(f"Total students: {len(students)}")
        print(f"Possible pairs: {len(tutors) * len(students)}")
        print(f"Compatible pairs: {len(relation)}")

        return relation

    def close(self):
        """Close database connections."""

        self.logic.close()
