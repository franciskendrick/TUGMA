
from src.graph import BipartiteGraph
from src.relations import CompatibilityRelation


def test_bipartite_graph():
    compatibility = CompatibilityRelation()
    graph_builder = BipartiteGraph()

    try:
        # Retrieve actual data from the database through M6.
        tutors = compatibility.get_tutors()
        students = compatibility.get_students()
        relation = compatibility.construct_relation()

        # Test create_graph() and get_graph().
        graph_builder.create_graph(tutors, students, relation)
        graph = graph_builder.get_graph()

        # Verify the number of nodes in each partition.
        tutor_nodes = {
            node for node, data in graph.nodes(data=True)
            if data["bipartite"] == 0
        }
        student_nodes = {
            node for node, data in graph.nodes(data=True)
            if data["bipartite"] == 1
        }

        assert len(tutor_nodes) == len(tutors)
        assert len(student_nodes) == len(students)

        # Verify that every edge connects a tutor to a student.
        for u, v in graph.edges():
            assert u[0] != v[0]
            assert {u[0], v[0]} == {"tutor", "student"}

        # Verify that graph edges exactly match the compatibility relation.
        graph_edges = {
            (u[1], v[1]) if u[0] == "tutor" else (v[1], u[1])
            for u, v in graph.edges()
        }

        assert graph_edges == set(relation)

        # Verify the graph's built-in validation.
        verification = graph_builder.verify_graph()
        assert verification["valid"] is True

        # Test add_tutor() and add_student() on a separate graph.
        test_builder = BipartiteGraph()
        test_builder.add_tutor("TEST_TUTOR")
        test_builder.add_student("TEST_STUDENT")

        test_graph = test_builder.get_graph()

        assert ("tutor", "TEST_TUTOR") in test_graph
        assert ("student", "TEST_STUDENT") in test_graph
        assert test_graph.number_of_edges() == 0

        # Test that invalid compatibility pairs are rejected.
        test_builder.relation = set()

        try:
            test_builder.add_compatibility_edge(
                "TEST_TUTOR", "TEST_STUDENT"
            )
            assert False, "Expected ValueError for an invalid pair."
        except ValueError:
            pass

        # Display the graph built from the real database.
        graph_builder.display_graph()

        print("\nAll bipartite graph tests passed.")

    finally:
        compatibility.close()


if __name__ == "__main__":
    test_bipartite_graph()
