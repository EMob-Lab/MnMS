import unittest

from mnms.graph.graph_path import GraphPath
from mnms.graph.layers import BusLayer, CarLayer
from mnms.graph.road import RoadDescriptor
from mnms.graph.zone import construct_zone_from_sections
from mnms.mobility_service.personal_vehicle import PersonalMobilityService
from mnms.mobility_service.public_transport import PublicTransportMobilityService
from mnms.time import Dt, TimeTable


class TestLayers(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """

        self.roads = RoadDescriptor()
        self.roads.register_node("0", [0, 0])
        self.roads.register_node("1", [1, 0])
        self.roads.register_node("2", [2, 0])

        self.roads.register_section("0_1", "0", "1", 1)
        self.roads.register_section("1_2", "1", "2", 1)

        self.roads.register_stop("S0", "0_1", 0.4)
        self.roads.register_stop("S1", "1_2", 0.9)
        self.roads.register_stop("S2", "1_2", 0.95)

        self.roads.add_zone(construct_zone_from_sections(self.roads, "Z0", ["0_1"]))
        self.roads.add_zone(construct_zone_from_sections(self.roads, "Z1", ["1_2"]))

    def tearDown(self):
        """Concludes and closes the test.
        """

    def test_car_layer(self):
        car_layer = CarLayer(self.roads,
                             services=[PersonalMobilityService()])

        self.assertEqual(car_layer.id, "CAR")
        self.assertEqual(car_layer.default_speed, 13.8)

        car_layer.create_node("C0", "0")
        car_layer.create_node("C1", "1", {"0": {"2"}})
        car_layer.create_node("C2", "2")
        costs = {"PersonalVehicle": {"test": 34.3}}
        car_layer.create_link("C0_C1", "C0", "C1", costs, ["0_1"])

        gnodes = car_layer.graph.nodes

        self.assertIn("C0", gnodes)
        self.assertIn("C1", gnodes)
        self.assertIn("C2", gnodes)

        self.assertEqual(gnodes["C0"].position, [0, 0])
        self.assertEqual(gnodes["C1"].position, [1, 0])
        self.assertEqual(gnodes["C2"].position, [2, 0])

        glinks = car_layer.graph.links

        self.assertIn("C0_C1", glinks)

        self.assertDictEqual(costs, glinks["C0_C1"].costs)

    def test_public_transport_layer(self):
        bus_layer = BusLayer(self.roads,
                             services=[PublicTransportMobilityService("BUS")])

        bus_layer.create_line("L0",
                              ["S0", "S1"],
                              [["0_1", "1_2"]],
                              TimeTable.create_table_freq("08:00:00", "18:00:00", Dt(minutes=10)))
        bus_layer.create_line("L1",
                              ["S0", "S1", "S2"],
                              [["0_1", "1_2"], ["1_2"]],
                              TimeTable.create_table_freq("08:00:00", "18:00:00", Dt(minutes=10)),
                              True)

        gnodes = bus_layer.graph.nodes
        glinks = bus_layer.graph.links

        # Asserts for line L0
        # -------------------

        self.assertIn("L0_S0", gnodes)
        self.assertIn("L0_S1", gnodes)
        self.assertNotIn("L0_S2", gnodes)

        self.assertAlmostEqual(0.4, gnodes['L0_S0'].position[0])
        self.assertAlmostEqual(1.9, gnodes['L0_S1'].position[0])

        self.assertIn("L0_S0_S1", glinks)
        self.assertNotIn("L0_S1_S0", glinks)
        self.assertNotIn("L0_S1_S2", glinks)
        self.assertNotIn("L0_S2_S1", glinks)

        self.assertListEqual(["0_1", "1_2"], bus_layer.map_reference_links["L0_S0_S1"])

        line0 = bus_layer.lines["L0"]
        self.assertEqual(GraphPath(["L0_S0", "L0_S1"], ["L0_S0_S1"]), line0["path"])
        self.assertNotIn("backward_path", line0)
        line0["path"].check_consistency(bus_layer.graph)

        # Asserts for line L1
        # -------------------

        self.assertIn("L1_S0", gnodes)
        self.assertIn("L1_S1", gnodes)
        self.assertIn("L1_S2", gnodes)

        self.assertAlmostEqual(0.4, gnodes['L1_S0'].position[0])
        self.assertAlmostEqual(1.9, gnodes['L1_S1'].position[0])
        self.assertAlmostEqual(1.95, gnodes['L1_S2'].position[0])

        self.assertIn("L1_S0_S1", glinks)
        self.assertIn("L1_S1_S0", glinks)
        self.assertIn("L1_S1_S2", glinks)
        self.assertIn("L1_S2_S1", glinks)

        self.assertListEqual(["0_1", "1_2"], bus_layer.map_reference_links["L1_S0_S1"])
        self.assertListEqual(["1_2", "0_1"], bus_layer.map_reference_links["L1_S1_S0"])
        self.assertListEqual(["1_2"], bus_layer.map_reference_links["L1_S1_S2"])
        self.assertListEqual(["1_2"], bus_layer.map_reference_links["L1_S2_S1"])

        line1 = bus_layer.lines["L1"]
        self.assertEqual(GraphPath(["L1_S0", "L1_S1", "L1_S2"], ["L1_S0_S1", "L1_S1_S2"]), line1["path"])
        self.assertEqual(GraphPath(["L1_S2", "L1_S1", "L1_S0"], ["L1_S2_S1", "L1_S1_S0"]), line1["backward_path"])
        line1["path"].check_consistency(bus_layer.graph)
        line1["backward_path"].check_consistency(bus_layer.graph)


class TestSerializationLayers(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """
        self.roads = RoadDescriptor()
        self.roads.register_node("0", [0, 0])
        self.roads.register_node("1", [1, 0])
        self.roads.register_node("2", [2, 0])

        self.roads.register_section("0_1", "0", "1", 1)
        self.roads.register_section("1_2", "1", "2", 1)

        self.roads.register_stop("S0", "0_1", 0.4)
        self.roads.register_stop("S1", "1_2", 0.9)

        self.roads.add_zone(construct_zone_from_sections(self.roads, "Z0", ["0_1"]))
        self.roads.add_zone(construct_zone_from_sections(self.roads, "Z1", ["1_2"]))

    def tearDown(self):
        """Concludes and closes the test.
        """

    def test_serialization_car(self):
        car_layer = CarLayer(self.roads,
                             services=[PersonalMobilityService()])

        car_layer.create_node("C0", "0")
        car_layer.create_node("C1", "1", {"0": {"2"}})
        car_layer.create_node("C2", "2")
        car_layer.create_link("C0_C1", "C0", "C1", {"PersonalVehicle": {"test": 34.3}}, ["0_1"])

        data_dict = car_layer.__dump__()

        new_car_layer = CarLayer.__load__(data_dict, self.roads)

        self.assertDictEqual(new_car_layer.map_reference_links, car_layer.map_reference_links)
        self.assertDictEqual(new_car_layer.map_reference_nodes, car_layer.map_reference_nodes)
        self.assertSetEqual(set(new_car_layer.graph.nodes.keys()), set(car_layer.graph.nodes.keys()))
        self.assertSetEqual(set(new_car_layer.graph.links.keys()), set(car_layer.graph.links.keys()))

    def test_serialization_public_transport(self):
        bus_layer = BusLayer(self.roads)

        bus_layer.create_line("L0",
                              ["S0", "S1"],
                              [["0_1", "1_2"]],
                              TimeTable.create_table_freq("08:00:00", "18:00:00", Dt(minutes=10)),
                              True)

        data_dict = bus_layer.__dump__()

        new_bus_layer = BusLayer.__load__(data_dict, self.roads)

        self.assertDictEqual(new_bus_layer.map_reference_links, bus_layer.map_reference_links)
        self.assertDictEqual(new_bus_layer.map_reference_nodes, bus_layer.map_reference_nodes)
        self.assertSetEqual(set(new_bus_layer.graph.nodes.keys()), set(bus_layer.graph.nodes.keys()))
        self.assertSetEqual(set(new_bus_layer.graph.links.keys()), set(bus_layer.graph.links.keys()))
