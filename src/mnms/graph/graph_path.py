from __future__ import annotations

from collections.abc import Sequence

from hipop.graph import OrientedGraph, OrientedGraphPath


class GraphPath:
    """Path in a graph, described by the IDs of the nodes and of the links it goes through.

    This class is functionally similar to hipop.graph.OrientedGraphPath, except that it stores
    IDs instead of references to the Node and Link objects of a graph. Hence, a GraphPath remains
    valid whatever happens to the graph (deletion of links, graph rebuilt, etc...), and two
    GraphPath are equal as soon as they go through the same nodes and links.

    GraphPath objects are immutable: all the operations return a new GraphPath.

    The node and link IDs are consistent: links[i] goes from nodes[i] to nodes[i+1], hence
    len(nodes) == len(links) + 1. A path contains at least one node (a path made of a single
    node and no link is valid). The number of nodes and links is checked at construction,
    but checking that the links actually connect the nodes requires the graph (see method check).
    """

    __slots__ = ('_links', '_nodes')

    def __init__(self, nodes: Sequence[str], links: Sequence[str]):
        """Build a path from the IDs of its nodes and links.

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
        """Build the path equivalent to a HiPOP path."""
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

    def check(self, graph: OrientedGraph):
        """Check that the links of the path exist in the graph and actually connect the nodes of the path.

        Raises:
            -ValueError: if the path is not valid in the graph
        """
        for i, lid in enumerate(self._links):
            if lid not in graph.links:
                raise ValueError(f'Link {lid} of path {self} does not exist in the graph')
            link = graph.links[lid]
            if link.upstream != self._nodes[i] or link.downstream != self._nodes[i+1]:
                raise ValueError(f'Link {lid} of path {self} goes from {link.upstream} to {link.downstream}, '
                    f'not from {self._nodes[i]} to {self._nodes[i+1]}')
        if not self._links and self._nodes[0] not in graph.nodes:
            raise ValueError(f'Node {self._nodes[0]} of path {self} does not exist in the graph')

    def sub_path(self, pos: int, link_count: int | None = None) -> GraphPath:
        """Return a part of the path.

        Args:
            -pos: the index of the first link of the sub-path (0 <= pos <= len(self.links)),
             i.e. the index of its first node
            -link_count: the number of links of the sub-path, None (or a number exceeding the
             number of remaining links) to go till the end of the path

        Raises:
            -IndexError: if pos is out of range
        """
        if not 0 <= pos <= len(self._links):
            raise IndexError(f'Invalid position {pos} in path {self}')
        if link_count is not None and link_count < 0:
            raise ValueError(f'Invalid link count {link_count}')
        stop = len(self._links) if link_count is None else min(pos + link_count, len(self._links))
        return GraphPath(self._nodes[pos:stop+1], self._links[pos:stop])

    def add(self, other: GraphPath) -> GraphPath:
        """Return the concatenation of this path and of another one.

        Raises:
            -ValueError: if the other path does not start where this path ends
        """
        if other.origin != self.destination:
            raise ValueError(f'Cannot concatenate path {self} with path {other}: {other.origin} != {self.destination}')
        return GraphPath(self._nodes + other._nodes[1:], self._links + other._links)

    def __add__(self, other: GraphPath) -> GraphPath:
        if not isinstance(other, GraphPath):
            return NotImplemented
        return self.add(other)

    def starts_with(self, prefix: GraphPath) -> bool:
        """Whether the path starts with another one."""
        return self._matches_at(prefix, 0)

    def ends_with(self, suffix: GraphPath) -> bool:
        """Whether the path ends with another one."""
        return self._matches_at(suffix, len(self._links) - len(suffix._links))

    def find(self, sub: GraphPath) -> list[int]:
        """Find all the occurrences of another path in this path.

        Returns:
            -positions: the indices of the first link (i.e. of the first node) of each occurrence, in increasing order
        """
        return [pos for pos in range(len(self._links) - len(sub._links) + 1) if self._matches_at(sub, pos)]

    def replace(self, old: GraphPath, new: GraphPath) -> GraphPath:
        """Return the path where the unique occurrence of a part of path is replaced by another path.

        Args:
            -old: the part of path to replace, it must appear exactly once in the path
            -new: the path to insert instead, it must have the same origin and destination as old

        Raises:
            -ValueError: if old and new do not have the same ends, or if old does not appear exactly once
        """
        if old.origin != new.origin or old.destination != new.destination:
            raise ValueError(f'Cannot replace {old} by {new}: they do not have the same origin and destination')
        positions = self.find(old)
        if len(positions) != 1:
            raise ValueError(f'Cannot replace {old} in path {self}: found {len(positions)} times instead of once')
        pos = positions[0]
        return self.sub_path(0, pos) + new + self.sub_path(pos + len(old._links))

    def replace_from(self, pos: int, new: GraphPath) -> GraphPath:
        """Return the path where the part starting from a given node is replaced by another path.

        Args:
            -pos: the index of the node from which the path is replaced (0 <= pos <= len(self.links))
            -new: the path to insert instead, it must start with the node at index pos

        Raises:
            -IndexError: if pos is out of range
            -ValueError: if new does not start with the node at index pos
        """
        if not 0 <= pos <= len(self._links):
            raise IndexError(f'Invalid position {pos} in path {self}')
        return self.sub_path(0, pos) + new

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
