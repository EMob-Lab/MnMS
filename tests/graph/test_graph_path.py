import copy
import pickle
import unittest
from itertools import pairwise

from hipop.graph import OrientedGraph
from hipop.graph import make_empty_path as make_empty_hipop_path
from hipop.graph import make_path as make_hipop_path

from mnms.graph.graph_path import GraphPath


def make_path(*nodes: str) -> GraphPath:
    """Build a path going through the given nodes, the link from A to B being named A_B."""
    return GraphPath(nodes, [f'{u}_{d}' for u, d in pairwise(nodes)])


def make_empty_path(node: str) -> GraphPath:
    """Build a path made of a single node and no link."""
    return GraphPath([node], [])


class TestGraphPath(unittest.TestCase):

    def test_construction(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(path.nodes, ('A', 'B', 'C', 'D', 'E'))
        self.assertEqual(path.links, ('A_B', 'B_C', 'C_D', 'D_E'))
        self.assertEqual(path.origin, 'A')
        self.assertEqual(path.destination, 'E')

    def test_construction_single_node(self):
        p = make_empty_path('A')
        self.assertEqual(p.nodes, ('A',))
        self.assertEqual(p.links, ())
        self.assertEqual(p.origin, 'A')
        self.assertEqual(p.destination, 'A')

    def test_construction_inconsistent(self):
        with self.assertRaises(ValueError):
            GraphPath([], [])
        with self.assertRaises(ValueError):
            GraphPath(['A', 'B'], [])
        with self.assertRaises(ValueError):
            GraphPath(['A', 'B'], ['A_B', 'B_C'])

    def test_construction_copies_input(self):
        nodes = ['A', 'B']
        links = ['A_B']
        p = GraphPath(nodes, links)
        nodes.append('C')
        links.append('B_C')
        self.assertEqual(p, make_path('A', 'B'))

    def test_immutability(self):
        path = make_path('A', 'B', 'C', 'D', 'E')

        # ruff: disable[B017] Which exception type is raised when trying
        # to modify an immutable field depends on how immutability is implemented.
        # Client code must not rely on these exception types.

        # Public attributes cannot be reassigned...
        with self.assertRaises(Exception):
            path.nodes = ('X', 'Y')
        with self.assertRaises(Exception):
            path.links = ('X_Y',)
        with self.assertRaises(Exception):
            path.origin = 'X'
        with self.assertRaises(Exception):
            path.destination = 'Y'

        # ... nor modified in place
        with self.assertRaises(Exception):
            path.nodes[0] = 'X'
        with self.assertRaises(Exception):
            path.links[0] = 'X_B'

        # No new attribute can be added
        with self.assertRaises(Exception):
            path.foo = 1

        # ruff: enable[B017]

        # The path is left untouched by all the attempts above
        self.assertEqual(path, make_path('A', 'B', 'C', 'D', 'E'))

    def test_equality_and_hash(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(path, make_path('A', 'B', 'C', 'D', 'E'))
        self.assertEqual(hash(path), hash(make_path('A', 'B', 'C', 'D', 'E')))
        self.assertNotEqual(path, make_path('A', 'B', 'C', 'D'))
        # Same nodes but different links (e.g. parallel links)
        self.assertNotEqual(make_path('A', 'B'), GraphPath(['A', 'B'], ['A_B_bis']))
        self.assertNotEqual(path, ('A', 'B', 'C', 'D', 'E'))

    def test_repr(self):
        self.assertEqual(repr(make_path('A', 'B', 'C')), 'GraphPath(from=A links=[A_B B_C] to=C)')
        self.assertEqual(repr(make_empty_path('A')), 'GraphPath(from=A links=[] to=A)')

    def test_copy_and_pickle(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(copy.copy(path), path)
        self.assertEqual(copy.deepcopy(path), path)
        self.assertEqual(pickle.loads(pickle.dumps(path)), path)

    def test_has_loop(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertFalse(path.has_loop())
        self.assertFalse(make_empty_path('A').has_loop())
        self.assertTrue(make_path('A', 'B', 'C', 'A').has_loop())
        self.assertTrue(make_path('A', 'B', 'C', 'D', 'B', 'E', 'F').has_loop())
        self.assertTrue(make_path('A', 'B', 'B', 'C').has_loop()) # Self-loop

    def test_sub_path(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(path.sub_path(0), path)
        self.assertEqual(path.sub_path(1), make_path('B', 'C', 'D', 'E'))
        self.assertEqual(path.sub_path(1, 2), make_path('B', 'C', 'D'))
        self.assertEqual(path.sub_path(1, 0), make_empty_path('B'))
        self.assertEqual(path.sub_path(4), make_empty_path('E'))
        self.assertEqual(path.sub_path(4, 1), make_empty_path('E'))
        # Link count exceeding the remaining number of links
        self.assertEqual(path.sub_path(2, 10), make_path('C', 'D', 'E'))

    def test_sub_path_invalid(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        with self.assertRaises(IndexError):
            path.sub_path(5)
        with self.assertRaises(IndexError):
            path.sub_path(-1)
        with self.assertRaises(ValueError):
            path.sub_path(1, -1)

    def test_concatenate(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(make_path('A', 'B', 'C') + make_path('C', 'D', 'E'), path)
        self.assertEqual(path + make_empty_path('E'), path)
        self.assertEqual(make_empty_path('A') + path, path)

    def test_concatenate_invalid(self):
        with self.assertRaises(ValueError):
            make_path('A', 'B') + make_path('C', 'D')
        with self.assertRaises(ValueError):
            make_path('A', 'B') + make_empty_path('C')
        with self.assertRaises(ValueError):
            make_empty_path('A') + make_path('B', 'C')
        with self.assertRaises(ValueError):
            make_empty_path('A') + make_empty_path('B')
        with self.assertRaises(TypeError):
            make_path('A', 'B', 'C') + ['C', 'D', 'E']

    def test_starts_with(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertTrue(path.starts_with(make_path('A', 'B', 'C')))
        self.assertTrue(path.starts_with(make_empty_path('A')))
        self.assertTrue(path.starts_with(path))
        self.assertFalse(path.starts_with(make_path('B', 'C')))
        self.assertFalse(path.starts_with(GraphPath(['A', 'B'], ['A_B_bis'])))
        self.assertFalse(make_path('A', 'B').starts_with(path))

    def test_ends_with(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertTrue(path.ends_with(make_path('C', 'D', 'E')))
        self.assertTrue(path.ends_with(make_empty_path('E')))
        self.assertTrue(path.ends_with(path))
        self.assertFalse(path.ends_with(make_path('C', 'D')))
        self.assertFalse(path.ends_with(GraphPath(['D', 'E'], ['D_E_bis'])))
        self.assertFalse(make_path('D', 'E').ends_with(path))

    def test_find(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(path.find(make_path('B', 'C', 'D')), [1])
        self.assertEqual(path.find(path), [0])
        self.assertEqual(path.find(make_path('B', 'D')), [])
        self.assertEqual(path.find(make_empty_path('C')), [2])
        self.assertEqual(make_path('A', 'B', 'A', 'B').find(make_path('A', 'B')), [0, 2])
        # Same nodes but different links
        self.assertEqual(path.find(GraphPath(['B', 'C'], ['B_C_bis'])), [])

    def test_replace_in_between(self):

        path = make_path('A', 'B', 'C', 'D', 'E')
        self.assertEqual(path.replace_in_between(1, 3, make_path('B', 'X', 'Y', 'D')),
            make_path('A', 'B', 'X', 'Y', 'D', 'E'))
        self.assertEqual(path.replace_in_between(1, 3, make_path('B', 'D')), make_path('A', 'B', 'D', 'E'))
        self.assertEqual(path.replace_in_between(0, 4, make_path('A', 'X', 'E')), make_path('A', 'X', 'E'))
        self.assertEqual(path.replace_in_between(0, 1, make_path('A', 'X', 'B')),
            make_path('A', 'X', 'B', 'C', 'D', 'E'))
        self.assertEqual(path.replace_in_between(3, 4, make_path('D', 'X', 'E')),
            make_path('A', 'B', 'C', 'D', 'X', 'E'))

        # Same start and end nodes: insertion of a loop
        self.assertEqual(path.replace_in_between(2, 2, make_path('C', 'X', 'C')),
            make_path('A', 'B', 'C', 'X', 'C', 'D', 'E'))
        self.assertEqual(path.replace_in_between(2, 2, make_empty_path('C')), path)

        # Removal of a loop
        path = make_path('A', 'B', 'C', 'B', 'D')
        self.assertEqual(path.replace_in_between(1, 3, make_empty_path('B')), make_path('A', 'B', 'D'))

    def test_replace_in_between_invalid(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        with self.assertRaises(IndexError):
            path.replace_in_between(-1, 2, make_path('A', 'B', 'C'))
        with self.assertRaises(IndexError):
            path.replace_in_between(3, 2, make_path('D', 'C'))
        with self.assertRaises(IndexError):
            path.replace_in_between(3, 5, make_path('D', 'E'))
        with self.assertRaises(ValueError):
            path.replace_in_between(1, 3, make_path('B', 'X'))
        with self.assertRaises(ValueError):
            path.replace_in_between(1, 3, make_path('X', 'D'))

    def test_replace_first_or_last(self):
        for replace in [GraphPath.replace_first, GraphPath.replace_last]:
            with self.subTest(replacement_method=replace.__name__):

                path = make_path('A', 'B', 'C', 'D', 'E')
                self.assertEqual(replace(path, make_path('B', 'C', 'D'), make_path('B', 'X', 'Y', 'D')),
                    make_path('A', 'B', 'X', 'Y', 'D', 'E'))
                self.assertEqual(replace(path, make_path('B', 'C', 'D'), make_path('B', 'D')),
                    make_path('A', 'B', 'D', 'E'))
                self.assertEqual(replace(path, path, make_path('A', 'X', 'E')), make_path('A', 'X', 'E'))

                # Replacement of a link by a parallel link
                self.assertEqual(replace(path, make_path('B', 'C'), GraphPath(['B', 'C'], ['B_C_bis'])),
                    GraphPath(['A', 'B', 'C', 'D', 'E'], ['A_B', 'B_C_bis', 'C_D', 'D_E']))

                # Part to replace without link: insertion of a loop
                self.assertEqual(replace(path, make_empty_path('C'), make_path('C', 'X', 'C')),
                    make_path('A', 'B', 'C', 'X', 'C', 'D', 'E'))

                # Removal of a loop
                path = make_path('A', 'B', 'C', 'B', 'D')
                self.assertEqual(replace(path, make_path('B', 'C', 'B'), make_empty_path('B')), make_path('A', 'B', 'D'))

        # Ensure only the first/last occurrence is replaced in case of multiple occurrences
        path = make_path('A', 'B', 'A', 'B')
        self.assertEqual(path.replace_first(make_path('A', 'B'), make_path('A', 'X', 'B')),
            make_path('A', 'X', 'B', 'A', 'B'))
        self.assertEqual(path.replace_last(make_path('A', 'B'), make_path('A', 'X', 'B')),
            make_path('A', 'B', 'A', 'X', 'B'))

    def test_replace_first_or_last_invalid(self):
        path = make_path('A', 'B', 'C', 'D', 'E')
        for replace in [path.replace_first, path.replace_last]:
            with self.subTest(replacement_method=replace.__name__):
                # Different ends
                with self.assertRaises(ValueError):
                    replace(make_path('B', 'C', 'D'), make_path('B', 'X'))
                with self.assertRaises(ValueError):
                    replace(make_path('B', 'C', 'D'), make_path('X', 'D'))
                # Part to replace not found
                with self.assertRaises(ValueError):
                    replace(make_path('B', 'D'), make_path('B', 'X', 'D'))
                # Same nodes but different links
                with self.assertRaises(ValueError):
                    replace(GraphPath(['B', 'C'], ['B_C_bis']), make_path('B', 'X', 'C'))


class TestGraphPathWithGraph(unittest.TestCase):

    def setUp(self):
        # Create the following line graph:
        #
        #          A_B             B_C             C_D
        #   A ------------> B ------------> C ------------> D
        #      length=10       length=20       length=30
        #      layer=L1        layer=L1        layer=L2
        #      cost:           cost:           cost:
        #      -S1/time=1      -S1/time=2      -S1/time=3
        #      -S2/time=11     -S2/time=21     -S2/time=31
        #
        self.graph = OrientedGraph()
        self.graph.add_node('A', 0, 0, '')
        self.graph.add_node('B', 10, 0, '')
        self.graph.add_node('C', 30, 0, '')
        self.graph.add_node('D', 60, 0, '')
        self.graph.add_link('A_B', 'A', 'B', 10, {'S1': {'time': 1}, 'S2': {'time': 11}}, 'L1')
        self.graph.add_link('B_C', 'B', 'C', 20, {'S1': {'time': 2}, 'S2': {'time': 21}}, 'L1')
        self.graph.add_link('C_D', 'C', 'D', 30, {'S1': {'time': 3}, 'S2': {'time': 31}}, 'L2')

    def test_from_hipop(self):
        hipop_path = make_hipop_path(self.graph, ['A_B', 'B_C', 'C_D'])
        self.assertEqual(GraphPath.from_hipop(hipop_path), make_path('A', 'B', 'C', 'D'))

    def test_from_hipop_single_node(self):
        hipop_path = make_empty_hipop_path(self.graph, 'B')
        self.assertEqual(GraphPath.from_hipop(hipop_path), make_empty_path('B'))

    def test_compute_length(self):
        self.assertEqual(make_path('A', 'B', 'C', 'D').compute_length(self.graph), 60)
        self.assertEqual(make_path('B', 'C').compute_length(self.graph), 20)
        self.assertEqual(make_empty_path('B').compute_length(self.graph), 0)

    def test_compute_cost(self):
        self.assertEqual(make_path('A', 'B', 'C', 'D').compute_cost(self.graph, 'time', {'L1': 'S1', 'L2': 'S2'}), 34)
        self.assertEqual(make_path('B', 'C', 'D').compute_cost(self.graph, 'time', {'L1': 'S2', 'L2': 'S1'}), 24)
        self.assertEqual(make_empty_path('B').compute_cost(self.graph, 'time', {}), 0)

    def test_check_consistency(self):
        make_path('A', 'B', 'C').check_consistency(self.graph)
        make_empty_path('B').check_consistency(self.graph)

    def test_check_consistency_invalid(self):

        # Unknown link
        with self.assertRaises(ValueError):
            GraphPath(['A', 'B'], ['A_Z']).check_consistency(self.graph)

        # Link not connecting the nodes
        with self.assertRaises(ValueError):
            GraphPath(['A', 'C'], ['A_B']).check_consistency(self.graph)
        with self.assertRaises(ValueError):
            GraphPath(['B', 'A'], ['A_B']).check_consistency(self.graph)

        # Unknown node (can only happen with an empty path)
        with self.assertRaises(ValueError):
            make_empty_path('Z').check_consistency(self.graph)
