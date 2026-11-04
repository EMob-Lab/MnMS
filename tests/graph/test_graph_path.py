import copy
import pickle
import unittest
from itertools import pairwise

from hipop.shortest_path import dijkstra

from mnms.generation.layers import generate_layer_from_roads
from mnms.generation.roads import generate_line_road
from mnms.graph.graph_path import GraphPath


def make_path(*nodes: str) -> GraphPath:
    """Build a path going through the given nodes, the link from A to B being named A_B."""
    return GraphPath(nodes, [f'{u}_{d}' for u, d in pairwise(nodes)])


class TestGraphPath(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """
        self.path = make_path('A', 'B', 'C', 'D', 'E')

    def tearDown(self):
        """Concludes and closes the test.
        """

    def test_construction(self):
        self.assertEqual(self.path.nodes, ('A', 'B', 'C', 'D', 'E'))
        self.assertEqual(self.path.links, ('A_B', 'B_C', 'C_D', 'D_E'))
        self.assertEqual(self.path.origin, 'A')
        self.assertEqual(self.path.destination, 'E')

    def test_construction_single_node(self):
        p = GraphPath(['A'], [])
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

    def test_equality_and_hash(self):
        self.assertEqual(self.path, make_path('A', 'B', 'C', 'D', 'E'))
        self.assertEqual(hash(self.path), hash(make_path('A', 'B', 'C', 'D', 'E')))
        self.assertNotEqual(self.path, make_path('A', 'B', 'C', 'D'))
        # Same nodes but different links (e.g. parallel links)
        self.assertNotEqual(make_path('A', 'B'), GraphPath(['A', 'B'], ['A_B_bis']))
        self.assertNotEqual(self.path, ('A', 'B', 'C', 'D', 'E'))

    def test_repr(self):
        self.assertEqual(repr(make_path('A', 'B', 'C')), 'GraphPath(from=A links=[A_B B_C] to=C)')
        self.assertEqual(repr(GraphPath(['A'], [])), 'GraphPath(from=A links=[] to=A)')

    def test_copy_and_pickle(self):
        self.assertEqual(copy.copy(self.path), self.path)
        self.assertEqual(copy.deepcopy(self.path), self.path)
        self.assertEqual(pickle.loads(pickle.dumps(self.path)), self.path)

    def test_has_loop(self):
        self.assertFalse(self.path.has_loop())
        self.assertFalse(GraphPath(['A'], []).has_loop())
        self.assertTrue(make_path('A', 'B', 'C', 'A').has_loop())

    def test_sub_path(self):
        self.assertEqual(self.path.sub_path(0), self.path)
        self.assertEqual(self.path.sub_path(1), make_path('B', 'C', 'D', 'E'))
        self.assertEqual(self.path.sub_path(1, 2), make_path('B', 'C', 'D'))
        self.assertEqual(self.path.sub_path(1, 0), GraphPath(['B'], []))
        self.assertEqual(self.path.sub_path(4), GraphPath(['E'], []))
        # Link count exceeding the remaining number of links
        self.assertEqual(self.path.sub_path(2, 10), make_path('C', 'D', 'E'))

    def test_sub_path_invalid(self):
        with self.assertRaises(IndexError):
            self.path.sub_path(5)
        with self.assertRaises(IndexError):
            self.path.sub_path(-1)
        with self.assertRaises(ValueError):
            self.path.sub_path(1, -1)

    def test_add(self):
        expected = self.path
        self.assertEqual(make_path('A', 'B', 'C').add(make_path('C', 'D', 'E')), expected)
        self.assertEqual(make_path('A', 'B', 'C') + make_path('C', 'D', 'E'), expected)
        self.assertEqual(self.path + GraphPath(['E'], []), self.path)
        self.assertEqual(GraphPath(['A'], []) + self.path, self.path)

    def test_add_invalid(self):
        with self.assertRaises(ValueError):
            make_path('A', 'B') + make_path('C', 'D')
        with self.assertRaises(TypeError):
            self.path + ['E', 'F']

    def test_starts_with(self):
        self.assertTrue(self.path.starts_with(make_path('A', 'B', 'C')))
        self.assertTrue(self.path.starts_with(GraphPath(['A'], [])))
        self.assertTrue(self.path.starts_with(self.path))
        self.assertFalse(self.path.starts_with(make_path('B', 'C')))
        self.assertFalse(self.path.starts_with(GraphPath(['A', 'B'], ['A_B_bis'])))
        self.assertFalse(make_path('A', 'B').starts_with(self.path))

    def test_ends_with(self):
        self.assertTrue(self.path.ends_with(make_path('C', 'D', 'E')))
        self.assertTrue(self.path.ends_with(GraphPath(['E'], [])))
        self.assertTrue(self.path.ends_with(self.path))
        self.assertFalse(self.path.ends_with(make_path('C', 'D')))
        self.assertFalse(make_path('D', 'E').ends_with(self.path))

    def test_find(self):
        self.assertEqual(self.path.find(make_path('B', 'C', 'D')), [1])
        self.assertEqual(self.path.find(self.path), [0])
        self.assertEqual(self.path.find(make_path('B', 'D')), [])
        self.assertEqual(self.path.find(GraphPath(['C'], [])), [2])
        self.assertEqual(make_path('A', 'B', 'A', 'B').find(make_path('A', 'B')), [0, 2])
        # Same nodes but different links
        self.assertEqual(self.path.find(GraphPath(['B', 'C'], ['B_C_bis'])), [])

    def test_replace(self):
        self.assertEqual(self.path.replace(make_path('B', 'C', 'D'), make_path('B', 'X', 'Y', 'D')),
            make_path('A', 'B', 'X', 'Y', 'D', 'E'))
        self.assertEqual(self.path.replace(make_path('B', 'C', 'D'), make_path('B', 'D')),
            make_path('A', 'B', 'D', 'E'))
        self.assertEqual(self.path.replace(self.path, make_path('A', 'X', 'E')), make_path('A', 'X', 'E'))
        self.assertEqual(self.path.replace(make_path('A', 'B'), make_path('A', 'X', 'B')),
            make_path('A', 'X', 'B', 'C', 'D', 'E'))
        self.assertEqual(self.path.replace(make_path('D', 'E'), make_path('D', 'X', 'E')),
            make_path('A', 'B', 'C', 'D', 'X', 'E'))
        # Replacement of a link by a parallel link
        self.assertEqual(self.path.replace(make_path('B', 'C'), GraphPath(['B', 'C'], ['B_C_bis'])),
            GraphPath(['A', 'B', 'C', 'D', 'E'], ['A_B', 'B_C_bis', 'C_D', 'D_E']))

    def test_replace_invalid(self):
        # Different ends
        with self.assertRaises(ValueError):
            self.path.replace(make_path('B', 'C', 'D'), make_path('B', 'X'))
        with self.assertRaises(ValueError):
            self.path.replace(make_path('B', 'C', 'D'), make_path('X', 'D'))
        # Old part not found
        with self.assertRaises(ValueError):
            self.path.replace(make_path('B', 'D'), make_path('B', 'X', 'D'))
        # Old part found several times
        with self.assertRaises(ValueError):
            make_path('A', 'B', 'A', 'B').replace(make_path('A', 'B'), make_path('A', 'X', 'B'))

    def test_replace_from(self):
        self.assertEqual(self.path.replace_from(2, make_path('C', 'X', 'Y')), make_path('A', 'B', 'C', 'X', 'Y'))
        self.assertEqual(self.path.replace_from(0, make_path('A', 'X')), make_path('A', 'X'))
        self.assertEqual(self.path.replace_from(4, make_path('E', 'X')), make_path('A', 'B', 'C', 'D', 'E', 'X'))
        self.assertEqual(self.path.replace_from(2, GraphPath(['C'], [])), make_path('A', 'B', 'C'))

    def test_replace_from_invalid(self):
        with self.assertRaises(ValueError):
            self.path.replace_from(2, make_path('B', 'X'))
        with self.assertRaises(IndexError):
            self.path.replace_from(5, make_path('E', 'X'))


class TestGraphPathWithGraph(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """
        roads = generate_line_road([0, 0], [0, 30], 4)
        self.graph = generate_layer_from_roads(roads, 'CAR').graph

    def tearDown(self):
        """Concludes and closes the test.
        """

    def test_from_hipop(self):
        hipop_path, _ = dijkstra(self.graph, 'CAR_0', 'CAR_3', 'length', {'CAR': 'CAR'}, {'CAR'})
        p = GraphPath.from_hipop(hipop_path)
        self.assertEqual(p.nodes, ('CAR_0', 'CAR_1', 'CAR_2', 'CAR_3'))
        self.assertEqual(p.links, ('CAR_0_1', 'CAR_1_2', 'CAR_2_3'))

    def test_from_hipop_single_node(self):
        hipop_path, _ = dijkstra(self.graph, 'CAR_1', 'CAR_1', 'length', {'CAR': 'CAR'}, {'CAR'})
        self.assertEqual(GraphPath.from_hipop(hipop_path), GraphPath(['CAR_1'], []))

    def test_check(self):
        GraphPath(['CAR_0', 'CAR_1', 'CAR_2'], ['CAR_0_1', 'CAR_1_2']).check(self.graph)
        GraphPath(['CAR_1'], []).check(self.graph)

    def test_check_invalid(self):
        # Unknown link
        with self.assertRaises(ValueError):
            GraphPath(['CAR_0', 'CAR_1'], ['CAR_0_9']).check(self.graph)
        # Link not connecting the nodes
        with self.assertRaises(ValueError):
            GraphPath(['CAR_0', 'CAR_2'], ['CAR_0_1']).check(self.graph)
        with self.assertRaises(ValueError):
            GraphPath(['CAR_1', 'CAR_0'], ['CAR_0_1']).check(self.graph)
        # Unknown node
        with self.assertRaises(ValueError):
            GraphPath(['CAR_9'], []).check(self.graph)
