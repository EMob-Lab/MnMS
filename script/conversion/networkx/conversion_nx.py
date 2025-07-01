import networkx as nx
import json
import os
import argparse

from networkx.readwrite import json_graph
from mnms.io.graph import load_graph


nx_dump_file = "lyon_mnms_nx.json"


def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


def generate_nx_graph(nodes, sections):

    # Create a directed graph
    nxgraph = nx.MultiDiGraph()

    # Add nodes to the graph
    for id, node in nodes.items():
        node_id = node.id
        x = float(node.position[0])
        y = float(node.position[1])
        nxgraph.add_node(node_id, position=(x, y))

    # Add edges to the graph
    for id, section in sections.items():
        edge_id = section.id
        upnode = section.upstream
        downnode = section.downstream
        length = section.length
        nxgraph.add_edge(upnode, downnode, id=edge_id, length=length)

    return nxgraph


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSON MnMS network file to JSON NetworkX file")
    parser.add_argument('network_file', type=_path_file_type, help='Path to the network JSON file')

    args = parser.parse_args()

    mnms_graph = load_graph(args.network_file)
    roads = mnms_graph.roads

    roads_nodes = mnms_graph.graph.nodes
    roads_sections = roads.sections

    # nx graph
    nxgraph = generate_nx_graph(roads_nodes, roads_sections)
    nxdata = json_graph.node_link_data(nxgraph)

    with open(nx_dump_file, "w") as f:
        json.dump(nxdata, f, indent=2)
