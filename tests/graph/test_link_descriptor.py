import unittest

from mnms.graph.graph_path import GraphPath
from mnms.graph.link_descriptor import LinkDescriptor


class TestLinkDescriptor(unittest.TestCase):

    def test_immutability(self):
        link = LinkDescriptor('A_B', 'A', 'B')

        # ruff: disable[B017] Which exception type is raised when trying
        # to modify an immutable field depends on how immutability is implemented.
        # Client code must not rely on these exception types.

        # Fields cannot be reassigned
        with self.assertRaises(Exception):
            link.id = 'X_Y'
        with self.assertRaises(Exception):
            link.upstream = 'X'
        with self.assertRaises(Exception):
            link.downstream = 'Y'

        # No new attribute can be added
        with self.assertRaises(Exception):
            link.foo = 1

        # ruff: enable[B017]

        # The link is left untouched by all the attempts above
        self.assertEqual(link, LinkDescriptor('A_B', 'A', 'B'))

    def test_from_path(self):
        path = GraphPath(['A', 'B', 'C'], ['A_B', 'B_C'])
        self.assertEqual(LinkDescriptor.from_path(path, 0), LinkDescriptor('A_B', 'A', 'B'))
        self.assertEqual(LinkDescriptor.from_path(path, 1), LinkDescriptor('B_C', 'B', 'C'))

    def test_from_path_invalid(self):

        # Regular path
        path = GraphPath(['A', 'B', 'C'], ['A_B', 'B_C'])
        for index in [-1, 2]:
            with self.subTest(index=index), self.assertRaises(IndexError):
                LinkDescriptor.from_path(path, index)

        # Empty path
        with self.assertRaises(IndexError):
            LinkDescriptor.from_path(GraphPath(['A'], []), 0)
