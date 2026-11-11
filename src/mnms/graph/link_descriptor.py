from __future__ import annotations

from dataclasses import dataclass

from mnms.graph.graph_path import GraphPath


@dataclass(frozen=True, slots=True)
class LinkDescriptor:
    """Link of a graph, described by its ID and by the IDs of its upstream and downstream nodes.

    This class stores IDs instead of a reference to the Link object of a graph,
    hence it remains valid whatever happens to the graph (e.g. deletion of the link).
    """

    id: str
    upstream: str
    downstream: str

    @classmethod
    def from_path(cls, path: GraphPath, index: int) -> LinkDescriptor:
        """Build the descriptor of the link at the given index in a path.

        Raises:
            -IndexError: if index is out of range (0 <= index < len(path.links))
        """
        if not 0 <= index < len(path.links):
            raise IndexError(f'Invalid link index {index} in path {path}')
        return cls(path.links[index], path.nodes[index], path.nodes[index+1])
