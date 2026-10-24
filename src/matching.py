# Implements the capacity-constrained matching algorithm.
# Attempts to maximize the number of students accommodated
# while respecting tutor capacity.


import networkx as nx


class CapacityMatcher:
    def __init__(self, graph, tutor_capacities):
        self.graph = graph
        self.tutor_capacities = dict(tutor_capacities)
        self.assignments = []
        self.unmatched_students = []
        self.remaining_capacity = dict(tutor_capacities)

    def find_matching(self):
        """Find a maximum-cardinality matching using maximum flow."""
        self.assignments = []
        self.unmatched_students = []

        tutor_nodes = [
            node for node, data in self.graph.nodes(data=True)
            if data.get("bipartite") == 0
        ]

        student_nodes = [
            node for node, data in self.graph.nodes(data=True)
            if data.get("bipartite") == 1
        ]

        tutor_ids = {node[1] for node in tutor_nodes}
        student_ids = {node[1] for node in student_nodes}

        # Validate capacities before running the algorithm.
        for tutor_id in tutor_ids:
            if tutor_id not in self.tutor_capacities:
                raise ValueError(
                    f"Missing capacity for tutor {tutor_id}."
                )

            capacity = self.tutor_capacities[tutor_id]

            if (
                not isinstance(capacity, int)
                or isinstance(capacity, bool)
                or capacity < 0
            ):
                raise ValueError(
                    f"Capacity for tutor {tutor_id} "
                    "must be a non-negative integer."
                )

        source = ("source",)
        sink = ("sink",)
        flow_network = nx.DiGraph()

        # Source -> Tutor: tutor capacity.
        for tutor_node in tutor_nodes:
            tutor_id = tutor_node[1]
            flow_network.add_edge(
                source,
                tutor_node,
                capacity=self.tutor_capacities[tutor_id]
            )

        # Tutor -> Student: one unit for each compatible pair.
        for tutor_node, student_node in self.graph.edges():
            if tutor_node[0] == "student":
                tutor_node, student_node = student_node, tutor_node

            if (
                tutor_node[0] != "tutor"
                or student_node[0] != "student"
            ):
                raise ValueError(
                    "The graph contains an invalid bipartite edge."
                )

            flow_network.add_edge(
                tutor_node, student_node, capacity=1
            )

        # Student -> Sink: each student can be assigned once.
        for student_node in student_nodes:
            flow_network.add_edge(
                student_node, sink, capacity=1
            )

        # Calculate the maximum possible number of assignments.
        _, flow = nx.maximum_flow(
            flow_network, source, sink
        )

        # Store the assignments represented by positive flow.
        for tutor_node in tutor_nodes:
            for student_node in self.graph.neighbors(tutor_node):
                if flow[tutor_node].get(student_node, 0) == 1:
                    self.assign(tutor_node[1], student_node[1])

        # Students who did not receive an assignment.
        assigned_students = {
            student_id for _, student_id in self.assignments
        }

        self.unmatched_students = [
            student_id for student_id in student_ids
            if student_id not in assigned_students
        ]

        self.unmatched_students.sort()
        self.remaining_capacity = self.get_remaining_capacity()

        return self.get_matches()

    def can_assign(self, tutor, student):
        """Check compatibility and current capacity constraints."""
        tutor_node = ("tutor", tutor)
        student_node = ("student", student)

        # Both nodes must exist.
        if (
            tutor_node not in self.graph
            or student_node not in self.graph
        ):
            return False

        # The pair must be a compatibility edge.
        if not self.graph.has_edge(tutor_node, student_node):
            return False

        # The tutor must have a defined capacity.
        if tutor not in self.tutor_capacities:
            return False

        # A student may only be assigned once.
        if any(
            assigned_student == student
            for _, assigned_student in self.assignments
        ):
            return False

        # The tutor must have remaining capacity.
        tutor_load = sum(
            1 for assigned_tutor, _ in self.assignments
            if assigned_tutor == tutor
        )

        return tutor_load < self.tutor_capacities[tutor]

    def assign(self, tutor, student):
        """Record an assignment only if it is valid."""
        if not self.can_assign(tutor, student):
            raise ValueError(
                f"Cannot assign student {student} "
                f"to tutor {tutor}."
            )

        self.assignments.append((tutor, student))
        self.remaining_capacity[tutor] = (
            self.tutor_capacities[tutor]
            - sum(
                1 for assigned_tutor, _ in self.assignments
                if assigned_tutor == tutor
            )
        )

    def get_matches(self):
        return list(self.assignments)

    def get_unmatched_students(self):
        return list(self.unmatched_students)

    def get_remaining_capacity(self):
        remaining = {}

        for tutor, capacity in self.tutor_capacities.items():
            tutor_load = sum(
                1 for assigned_tutor, _ in self.assignments
                if assigned_tutor == tutor
            )
            remaining[tutor] = capacity - tutor_load

        return remaining
