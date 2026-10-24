
from src.relations import CompatibilityRelation
from src.graph import BipartiteGraph
from src.matching import CapacityMatcher


def test_capacity_matching():
    compatibility = CompatibilityRelation()
    graph_builder = BipartiteGraph()

    try:
        # Load actual project data.
        tutors = compatibility.get_tutors()
        students = compatibility.get_students()
        relation = compatibility.construct_relation()

        graph = graph_builder.create_graph(
            tutors, students, relation
        )

        # Temporary test capacities, not database values.
        capacities = {
            tutor_id: 5 for tutor_id in tutors
        }

        matcher = CapacityMatcher(graph, capacities)

        # Find the maximum-cardinality matching.
        matches = matcher.find_matching()
        unmatched = matcher.get_unmatched_students()
        remaining = matcher.get_remaining_capacity()

        # Every assignment must be a compatible pair.
        assert all(pair in set(relation) for pair in matches)

        # Each student can be assigned at most once.
        assigned_students = [
            student_id for _, student_id in matches
        ]
        assert len(assigned_students) == len(set(assigned_students))

        # Tutor capacities must not be exceeded.
        for tutor_id, capacity in capacities.items():
            tutor_load = sum(
                1 for assigned_tutor, _ in matches
                if assigned_tutor == tutor_id
            )
            assert tutor_load <= capacity
            assert remaining[tutor_id] == capacity - tutor_load
            assert remaining[tutor_id] >= 0

        # Every student is either matched or unmatched.
        assert set(assigned_students).isdisjoint(set(unmatched))
        assert set(assigned_students) | set(unmatched) == set(students)

        # The number of matches equals the number of assignments.
        assert len(matches) == len(assigned_students)

        # Verify that incompatible pairs cannot be assigned.
        invalid_pair_found = False

        for tutor_id in tutors:
            for student_id in students:
                if (tutor_id, student_id) not in set(relation):
                    assert not matcher.can_assign(tutor_id, student_id)
                    invalid_pair_found = True
                    break
            if invalid_pair_found:
                break

        # Display the results.
        print("Capacity-Constrained Matching")
        print("-----------------------------")
        print(f"Total tutors: {len(tutors)}")
        print(f"Total students: {len(students)}")
        print(f"Compatible pairs: {len(relation)}")
        print(f"Total assignments: {len(matches)}")

        print("\nAssignments:")
        for tutor_id, student_id in sorted(matches):
            print(f"T{tutor_id} -> S{student_id}")

        print("\nUnmatched Students:")
        if unmatched:
            for student_id in unmatched:
                print(f"S{student_id}")
        else:
            print("None")

        print("\nRemaining Tutor Capacity:")
        for tutor_id, capacity in sorted(remaining.items()):
            print(f"T{tutor_id}: {capacity}")

        print("\nAll capacity matching tests passed.")

    finally:
        compatibility.close()


if __name__ == "__main__":
    test_capacity_matching()
