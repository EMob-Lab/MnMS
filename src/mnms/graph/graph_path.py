from __future__ import annotations

from collections.abc import Sequence

from hipop.graph import OrientedGraph, OrientedGraphPath


class GraphPath:
    """Path in a graph, described by the IDs of the nodes and of the links it goes through.

    This class is functionally similar to hipop.graph.OrientedGraphPath, except that it stores
    IDs instead of references to the Node and Link objects of a graph. Hence, a GraphPath remains
    valid whatever happens to the graph (deletion of links, graph rebuilt, etc...).

    GraphPath objects are immutable: all the operations return a new GraphPath.

    The node and link IDs are consistent: links[i] goes from nodes[i] to nodes[i+1],
    hence len(nodes) == len(links) + 1. Also, there is always at least one node in a path.
    This invariant may be checked with method check_consistency (which requires the underlying graph).
    """

    __slots__ = ('_links', '_nodes')

    def __init__(self, nodes: Sequence[str], links: Sequence[str]):
        """Build a GraphPath from the IDs of its nodes and links.

        Args:
            -nodes: the IDs of the nodes the path goes through
            -links: the IDs of the links the path goes through (links[i] goes from nodes[i] to nodes[i+1])
        """
        nodes = tuple(nodes)
        links = tuple(links)
        if len(nodes) != len(links) + 1:
            raise ValueError(f'Inconsistent path: {len(nodes)} nodes {nodes} and {len(links)} links {links}')
        self._nodes = nodes
        self._links = links

    @classmethod
    def from_hipop(cls, path: OrientedGraphPath) -> GraphPath:
        """Build a GraphPath instance equivalent to the given HiPOP path."""
        return cls(path.nodes.ids(), path.links.ids())

    @property
    def nodes(self) -> tuple[str, ...]:
        """The IDs of the nodes of the path."""
        return self._nodes

    @property
    def links(self) -> tuple[str, ...]:
        """The IDs of the links of the path."""
        return self._links

    @property
    def origin(self) -> str:
        """The ID of the first node of the path."""
        return self._nodes[0]

    @property
    def destination(self) -> str:
        """The ID of the last node of the path."""
        return self._nodes[-1]

    def has_loop(self) -> bool:
        """Whether the path goes several times through the same node."""
        return len(set(self._nodes)) != len(self._nodes)

    def check_consistency(self, graph: OrientedGraph):
        """Check that the node IDs and link IDs of the path actually refer to existing nodes and links
        in the given graph, and that the node/link relationships are consistent (i.e. that for each link
        corresponding to the ID links[i], its upstream and downstream nodes actually corresponds to
        nodes[i] and nodes[i+1] respectively).

        Raises:
            -ValueError: if any of the conditions above is not satisfied
        """

        # REMARK: this method assumes that the number of nodes and links is consistent
        # (i.e. `len(nodes) == len(links) + 1`). This is guaranteed by the constructor.

        # For an empty path (i.e. a path with no link), just validate that the single node
        # actually exists in the graph.
        if len(self._links) == 0:
            if self._nodes[0] not in graph.nodes:
                raise ValueError(f'Node {self._nodes[0]} does not exist in the graph')

        # Regular case: check that each link exists in the graph, and that it has the expected
        # upstream and downstream nodes. The existence of the nodes themselves is not explicitly checked,
        # because the HiPOP graph structure ensures their existence as long as a link references them
        # as `link.upstream` or `link.downstream`.
        else:
            for i, lid in enumerate(self._links):
                if lid not in graph.links:
                    raise ValueError(f'Link {lid} does not exist in the graph')
                link = graph.links[lid]
                if link.upstream != self._nodes[i] or link.downstream != self._nodes[i+1]:
                    raise ValueError(f'Link {lid} goes from {link.upstream} to {link.downstream}, '
                        f'not from {self._nodes[i]} to {self._nodes[i+1]}')

    def compute_length(self, graph: OrientedGraph) -> float:
        """Compute the length of the path (i.e. the sum of the lengths of its links in the given graph)."""
        return sum(graph.links[lid].length for lid in self._links)

    def compute_cost(self, graph: OrientedGraph, cost_metric: str, chosen_mservices: dict[str, str]) -> float:
        """Compute the cost of the path in the given graph.

        Args:
            -graph: the graph
            -cost_metric: the type of cost (e.g. "time", "generalized_cost", etc.)
            -chosen_mservices: the dict specifying which mobility service is used on each layer
             (the layer of a link being given by its label)
        """
        path_cost = 0
        for lid in self._links:
            link = graph.links[lid]
            path_cost += link.costs[chosen_mservices[link.label]][cost_metric]
        return path_cost

    def sub_path(self, pos: int, link_count: int | None = None) -> GraphPath:
        """Return a part of the path.

        Args:
            -pos: the index of the first node of the sub-path (0 <= pos < len(self.nodes))
            -link_count: the number of links of the sub-path, or None (or a number exceeding
             the number of remaining links) to go till the end of the path

        Raises:
            -IndexError: if pos is out of range
            -ValueError: if link_count is negative
        """
        if not 0 <= pos < len(self._nodes):
            raise IndexError(f'Invalid node index {pos} in path {self}')
        if link_count is not None and link_count < 0:
            raise ValueError(f'Invalid link count {link_count}')
        stop = len(self._links) if link_count is None else min(pos + link_count, len(self._links))
        return GraphPath(self._nodes[pos:stop+1], self._links[pos:stop])

    def __add__(self, other: GraphPath) -> GraphPath:
        """Concatenate the current path with another one.

        Raises:
            -ValueError: if the other path does not start where the current path ends
        """
        if not isinstance(other, GraphPath):
            return NotImplemented
        if other.origin != self.destination:
            raise ValueError(f'Cannot concatenate path {self} with path {other}: {other.origin} != {self.destination}')
        return GraphPath(self._nodes + other._nodes[1:], self._links + other._links)

    def starts_with(self, prefix: GraphPath) -> bool:
        """Whether the path starts with another one."""
        return self._matches_at(prefix, 0)

    def ends_with(self, suffix: GraphPath) -> bool:
        """Whether the path ends with another one."""
        return self._matches_at(suffix, len(self._links) - len(suffix._links))

    def find(self, sub: GraphPath) -> list[int]:
        """Find all the occurrences of another path in this path.

        Returns:
            -positions: the indices of the first node of each occurrence, in increasing order
        """
        return [pos for pos in range(len(self._links) - len(sub._links) + 1) if self._matches_at(sub, pos)]

    def replace_in_between(self, start: int, end: int, new: GraphPath) -> GraphPath:
        """Return the path where the part between two nodes is replaced by another path.

        Example: with path = A-B-C-D-E-F, start = 1 (pointing at node B), end = 3 (pointing at node D),
        and new = B-X-Y-D, the result is A-B-X-Y-D-E-F.

        Args:
            -start: the index of the first node of the part to replace
            -end: the index of the last node of the part to replace (0 <= start <= end <= len(self.links))
            -new: the path to insert instead, it must start with the node at index start
                and end with the node at index end

        Raises:
            -IndexError: if start or end is out of range
            -ValueError: if new does not start and end with the nodes at index start and end
        """
        if not 0 <= start <= end < len(self._nodes):
            raise IndexError(f'Invalid node indices {start} and/or {end} in path {self}')
        if new.origin != self._nodes[start] or new.destination != self._nodes[end]:
            raise ValueError(f'Cannot replace the part of path {self} between {self._nodes[start]} and '
                f'{self._nodes[end]} by {new}: they do not have the same origin and destination')
        return self.sub_path(0, start) + new + self.sub_path(end)

    def replace_first(self, old: GraphPath, new: GraphPath) -> GraphPath:
        """Return the path where the first occurrence of a part of path is replaced by another path.

        Args:
            -old: the part of path to replace
            -new: the path to insert instead, it must have the same origin and destination as old

        Raises:
            -ValueError: if old and new do not have the same ends, or if old is not found
        """
        pos = self._find_for_replacement(old, new)[0]
        return self.replace_in_between(pos, pos + len(old._links), new)

    def replace_last(self, old: GraphPath, new: GraphPath) -> GraphPath:
        """Return the path where the last occurrence of a part of path is replaced by another path.

        Args:
            -old: the part of path to replace
            -new: the path to insert instead, it must have the same origin and destination as old

        Raises:
            -ValueError: if old and new do not have the same ends, or if old is not found
        """
        pos = self._find_for_replacement(old, new)[-1]
        return self.replace_in_between(pos, pos + len(old._links), new)

    def _find_for_replacement(self, old: GraphPath, new: GraphPath) -> list[int]:
        """Check that old can be replaced by new, and return the positions of old in this path (not empty)."""
        if old.origin != new.origin or old.destination != new.destination:
            raise ValueError(f'Cannot replace {old} by {new}: they do not have the same origin and destination')
        positions = self.find(old)
        if len(positions) == 0:
            raise ValueError(f'Cannot replace {old} in path {self}: not found')
        return positions

    def _matches_at(self, sub: GraphPath, pos: int) -> bool:
        """Whether another path appears in this path, starting at node index pos."""
        if pos < 0 or pos + len(sub._links) > len(self._links):
            return False
        return self._nodes[pos:pos+len(sub._nodes)] == sub._nodes and self._links[pos:pos+len(sub._links)] == sub._links

    def __eq__(self, other) -> bool:
        if not isinstance(other, GraphPath):
            return NotImplemented
        return self._nodes == other._nodes and self._links == other._links

    def __hash__(self) -> int:
        return hash((self._nodes, self._links))

    def __repr__(self) -> str:
        return f'GraphPath(from={self.origin} links=[{" ".join(self._links)}] to={self.destination})'
