import networkx as nx
import json
import os
import argparse

from networkx.readwrite import json_graph
from mnms.io.graph import load_graph


# Output filename for the converted NetworkX graph
nx_dump_file = "lyon_mnms_nx.json"


# Helper function to check if a file path is valid
def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


# Function to convert MnMS graph data into a NetworkX MultiDiGraph
def generate_nx_graph(nodes, sections):
    # Create a directed multigraph (allows multiple edges between nodes)
    nxgraph = nx.MultiDiGraph()

    # Add nodes to the graph with positions as attributes
    for id, node in nodes.items():
        node_id = node.id
        x = float(node.position[0])
        y = float(node.position[1])
        nxgraph.add_node(node_id, position=(x, y))

    # Add directed edges (sections) with attributes
    for id, section in sections.items():
        edge_id = section.id
        upnode = section.upstream      # Node where the section starts
        downnode = section.downstream  # Node where the section ends
        length = section.length        # Length of the road section
        nxgraph.add_edge(upnode, downnode, id=edge_id, length=length)

    return nxgraph


# Entry point for the script
if __name__ == "__main__":
    # Set up argument parser for command-line execution
    parser = argparse.ArgumentParser(description="Convert JSON MnMS network file to JSON NetworkX file")
    parser.add_argument('network_file', type=_path_file_type, help='Path to the network JSON file')

    args = parser.parse_args()

    # Load the MnMS graph from the given JSON file
    mnms_graph = load_graph(args.network_file)
    roads = mnms_graph.roads

    # Extract nodes and sections (edges) from the graph
    roads_nodes = mnms_graph.graph.nodes
    roads_sections = roads.sections

    # Generate the NetworkX graph
    nxgraph = generate_nx_graph(roads_nodes, roads_sections)

    # Convert the NetworkX graph to a JSON-serializable format
    nxdata = json_graph.node_link_data(nxgraph)

    # Write the JSON data to a file
    with open(nx_dump_file, "w") as f:
        json.dump(nxdata, f, indent=2)