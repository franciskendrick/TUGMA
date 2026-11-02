# Creates visual representations of TUGMA's mathematical structures and results.

import matplotlib.pyplot as plt
import networkx as nx


class TUGMAVisualizer:

    def _get_positions(self, graph):
        """Arrange tutors on the left and students on the right."""

        tutors = sorted(
            [
                node for node, data in graph.nodes(data=True)
                if data.get("bipartite") == 0
            ],
            key=lambda node: node[1]
        )

        students = sorted(
            [
                node for node, data in graph.nodes(data=True)
                if data.get("bipartite") == 1
            ],
            key=lambda node: node[1]
        )

        positions = {}

        for index, tutor in enumerate(tutors):
            y = (
                0 if len(tutors) == 1
                else 1 - 2 * index / (len(tutors) - 1)
            )
            positions[tutor] = (0, y)

        for index, student in enumerate(students):
            y = (
                0 if len(students) == 1
                else 1 - 2 * index / (len(students) - 1)
            )
            positions[student] = (1, y)

        return positions

    def _draw_nodes(self, graph, positions, ax):
        """Draw tutor and student vertices with their labels."""

        tutors = [
            node for node, data in graph.nodes(data=True)
            if data.get("bipartite") == 0
        ]

        students = [
            node for node, data in graph.nodes(data=True)
            if data.get("bipartite") == 1
        ]

        labels = {
            node: graph.nodes[node].get("label", str(node))
            for node in graph.nodes()
        }

        nx.draw_networkx_nodes(
            graph, positions,
            nodelist=tutors,
            ax=ax
        )

        nx.draw_networkx_nodes(
            graph, positions,
            nodelist=students,
            ax=ax
        )

        nx.draw_networkx_labels(
            graph, positions,
            labels=labels,
            ax=ax
        )

    def draw_before_matching(self, graph):
        """Display all valid compatibility edges."""

        positions = self._get_positions(graph)

        fig, ax = plt.subplots(figsize=(9, 6))

        self._draw_nodes(graph, positions, ax)

        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=list(graph.edges()),
            ax=ax,
            width=1.5
        )

        ax.set_title("TUGMA - Compatibility Graph")
        ax.axis("off")

        fig.tight_layout()

        return fig

    def draw_after_matching(self, graph, matches):
        """Display only the selected matching edges."""

        positions = self._get_positions(graph)

        matching_edges = [
            (("tutor", tutor_id), ("student", student_id))
            for tutor_id, student_id in matches
        ]

        # Ensure every selected pair exists in the graph.
        for tutor_node, student_node in matching_edges:
            if not graph.has_edge(tutor_node, student_node):
                raise ValueError(
                    f"Matching pair {tutor_node}, {student_node} "
                    "is not a compatibility edge."
                )

        fig, ax = plt.subplots(figsize=(9, 6))

        self._draw_nodes(graph, positions, ax)

        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=matching_edges,
            ax=ax,
            width=3
        )

        ax.set_title("TUGMA - Selected Matching")
        ax.axis("off")

        fig.tight_layout()

        return fig
