# Constructs the bipartite graph representing the compatibility relation.


import networkx as nx
from src.relations import CompatibilityRelation


class BipartiteGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.relation = set()

    def create_graph(self, tutors, students, relation):
        self.graph.clear()
        self.relation = set(relation)

        for tutor in tutors:
            self.add_tutor(tutor)

        for student in students:
            self.add_student(student)

        for tutor_id, student_id in self.relation:
            self.add_compatibility_edge(tutor_id, student_id)

        return self.graph

    def add_tutor(self, tutor):
        self.graph.add_node(
            ("tutor", tutor),
            bipartite=0,
            label=f"T{tutor}"
        )

    def add_student(self, student):
        self.graph.add_node(
            ("student", student),
            bipartite=1,
            label=f"S{student}"
        )

    def add_compatibility_edge(self, tutor_id, student_id):
        tutor_node = ("tutor", tutor_id)
        student_node = ("student", student_id)

        if tutor_node not in self.graph:
            raise ValueError(f"Tutor {tutor_id} does not exist.")

        if student_node not in self.graph:
            raise ValueError(f"Student {student_id} does not exist.")

        # Prevent edges that are not in the compatibility relation.
        if (tutor_id, student_id) not in self.relation:
            raise ValueError(
                f"({tutor_id}, {student_id}) is not a valid "
                "compatibility pair."
            )

        self.graph.add_edge(tutor_node, student_node)

    def get_graph(self):
        return self.graph

    def verify_graph(self):
        tutor_nodes = {
            node for node, data in self.graph.nodes(data=True)
            if data["bipartite"] == 0
        }
        student_nodes = {
            node for node, data in self.graph.nodes(data=True)
            if data["bipartite"] == 1
        }

        graph_edges = {
            (u[1], v[1]) if u[0] == "tutor" else (v[1], u[1])
            for u, v in self.graph.edges()
        }

        partitions_valid = (
            len(tutor_nodes) + len(student_nodes)
            == self.graph.number_of_nodes()
        )

        edges_valid = graph_edges == self.relation

        return {
            "partitions_valid": partitions_valid,
            "edges_valid": edges_valid,
            "valid": partitions_valid and edges_valid
        }

    def display_graph(self):
        tutors = [
            node for node, data in self.graph.nodes(data=True)
            if data["bipartite"] == 0
        ]
        students = [
            node for node, data in self.graph.nodes(data=True)
            if data["bipartite"] == 1
        ]

        print("Bipartite Compatibility Graph")
        print("-----------------------------")
        print(f"Tutors: {len(tutors)}")
        print(f"Students: {len(students)}")
        print(f"Edges: {self.graph.number_of_edges()}")

        print("\nCompatibility Edges:")
        for tutor_id, student_id in sorted(self.relation):
            print(f"(T{tutor_id}, S{student_id})")

        print("\nVerification:")
        for check, passed in self.verify_graph().items():
            print(f"{check}: {passed}")


if __name__ == "__main__":
    compatibility = CompatibilityRelation()

    try:
        tutors = compatibility.get_tutors()
        students = compatibility.get_students()
        relation = compatibility.construct_relation()

        graph_builder = BipartiteGraph()
        graph_builder.create_graph(tutors, students, relation)
        graph_builder.display_graph()

    finally:
        compatibility.close()
