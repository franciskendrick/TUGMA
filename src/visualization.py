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

    def _figure(self, graph):
        """Taller figures for bigger graphs so labels never overlap."""
        rows = max(
            sum(1 for _, d in graph.nodes(data=True) if d.get("bipartite") == 0),
            sum(1 for _, d in graph.nodes(data=True) if d.get("bipartite") == 1),
        )
        return plt.subplots(figsize=(9, max(6, 0.3 * rows + 1.5)))

    def _draw_nodes(self, graph, positions, ax):
        """Draw tutors (left) and students (right) with name labels and
        a column header over each side."""

        sides = (
            (0, "Tutors", "#0b6b3a", "right", -0.03),
            (1, "Students", "#2b6cb0", "left", 0.03),
        )
        rows = max(
            sum(1 for _, d in graph.nodes(data=True) if d.get("bipartite") == side)
            for side in (0, 1)
        )
        fontsize = 10 if rows <= 12 else 8 if rows <= 30 else 7

        for side, title, color, align, offset in sides:
            nodes = [
                node for node, data in graph.nodes(data=True)
                if data.get("bipartite") == side
            ]

            nx.draw_networkx_nodes(
                graph, positions, nodelist=nodes, node_color=color,
                node_size=70, ax=ax
            )

            for node in nodes:
                x, y = positions[node]
                ax.text(
                    x + offset, y,
                    graph.nodes[node].get("label", str(node)),
                    ha=align, va="center", fontsize=fontsize,
                )

            ax.text(
                side, 1.0 + 0.12 * (2 / max(rows, 6)) + 0.06, title,
                ha="center", va="bottom", fontsize=13,
                fontweight="bold", color=color,
            )

        ax.set_xlim(-0.55, 1.55)
        ax.set_ylim(-1.04, 1.14)

    def draw_before_matching(self, graph):
        """Display all valid compatibility edges."""

        positions = self._get_positions(graph)

        fig, ax = self._figure(graph)

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

        fig, ax = self._figure(graph)

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