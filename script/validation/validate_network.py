import os
import argparse
import json

import pandas as pd
import mpl_scatter_density
import numpy as np

from statistics import mean, median
from matplotlib import pyplot as plt
from matplotlib import colormaps

pd.set_option('future.no_silent_downcasting', True)

# Check that all required sub-tags exist in the ROADS tag
def validate_roads_tag(roads):
    valid = True

    # Extract sub-tags from ROADS
    nodes = roads.get("NODES")
    stops = roads.get("STOPS")
    sections = roads.get("SECTIONS")
    zones = roads.get("ZONES")

    # Validate presence of required tags
    if nodes is None:
        print(f"No tag NODES found in tag ROADS")
        valid = False

    if stops is None:
        print(f"No tag STOPS found in tag ROADS")
        valid = False

    if sections is None:
        print(f"No tag SECTIONS found in tag ROADS")
        valid = False

    if zones is None:
        print(f"No tag ZONES found in tag ROADS")
        valid = False

    return valid


# Placeholder function for validating LAYERS tag, currently does nothing
def validate_layers_tag(layers):
    valid = True


# Validate the ROADS tag and print result
def validate_roads(roads):
    roads_valid = True
    network_valid = validate_roads_tag(roads)

    print(f"Network (ROADS) valid : {network_valid}")

    return network_valid


# Validate the LAYERS tag and print result
def validate_layers(layers):
    layers_valid = True
    network_valid = validate_layers_tag(layers)

    print(f"Network (LAYERS) valid : {network_valid}")

    return network_valid


# Build adjacency matrix from SECTIONS for network connectivity analysis
def build_adjacency_matrix(network):
    # Create DataFrame of sections
    df_links = pd.DataFrame(network['ROADS']['SECTIONS'].values())

    # Get all unique nodes from upstream and downstream columns
    all_nodes = np.union1d(df_links.upstream.unique(), df_links.downstream.unique())
    df_adj = pd.DataFrame(index=all_nodes, columns=all_nodes)

    # Mark adjacency where sections connect nodes
    for _, row in df_links.iterrows():
        df_adj.loc[row.upstream, row.downstream] = 1

    # Fill missing values with 0 (no connection)
    df_adj.fillna(0, inplace=True)

    return df_adj


# Identify dead-end nodes with no outgoing edges
def identify_deadends(df_adj):
    df_adj_de = df_adj.copy()
    # Find nodes with no outgoing edges
    s_deadEnds = (df_adj_de == 0).all(axis=1)
    ls_deadEnds = s_deadEnds[s_deadEnds].index

    while True:
        # Remove columns corresponding to identified dead ends
        df_adj_de.loc[:, ls_deadEnds] = 0
        s_deadEnds = (df_adj_de == 0).all(axis=1)
        new_deadEnds = s_deadEnds[s_deadEnds].index

        # Stop when no new dead ends found
        if new_deadEnds.equals(ls_deadEnds):
            break
        else:
            ls_deadEnds = new_deadEnds

    ls_deadEnds = new_deadEnds

    return ls_deadEnds


# Identify spring nodes with no incoming edges
def identify_springs(df_adj):
    df_adj_sp = df_adj.copy()
    # Find nodes with no incoming edges
    s_springs = (df_adj_sp == 0).all(axis=0)
    ls_springs = s_springs[s_springs].index

    while True:
        # Remove rows corresponding to identified springs
        df_adj_sp.loc[s_springs, :] = 0
        s_springs = (df_adj_sp == 0).all(axis=0)
        new_springs = s_springs[s_springs].index

        # Stop when no new springs found
        if new_springs.equals(ls_springs):
            break
        else:
            ls_springs = new_springs

    ls_springs = new_springs

    return ls_springs


# Find final sections ending in dead-end nodes
def identify_final_sections(deadends):
    final_sections = []
    sections = roads.get("SECTIONS")

    # Iterate over deadends and find sections ending there
    for deadend in deadends:
        for id, section in sections.items():
            downnode = section["downstream"]
            if deadend == downnode:
                final_sections.append(section["id"])

    return final_sections


# Identify duplicate sections based on upstream/downstream node pairs
def identify_duplicate_sections(sections):
    duplicates = []
    seen_pairs = {}

    for id, section in sections.items():
        id_section = section["id"]
        upnode = section["upstream"]
        downnode = section["downstream"]
        pair = (upnode, downnode)

        # Mark as duplicate if pair already seen
        if pair in seen_pairs:
            duplicates.append(id_section)
        else:
            seen_pairs[pair] = id_section

    return duplicates


# Compute centrality as number of connected sections per node
def compute_centralities(roads):
    nodes = roads.get("NODES")
    sections = roads.get("SECTIONS")
    centralities = {}

    # Count connections per node
    for id, node in nodes.items():
        id_node = node["id"]
        for id, section in sections.items():
            upnode = section["upstream"]
            downnode = section["downstream"]
            if id_node == upnode:
                centralities[id_node] = centralities.get(id_node, 0) + 1
            if id_node == downnode:
                centralities[id_node] = centralities.get(id_node, 0) + 1

    return centralities


# Perform various analyses on the ROADS data and print results
def analyze_roads(roads):
    nodes = roads.get("NODES")
    stops = roads.get("STOPS")
    sections = roads.get("SECTIONS")
    zones = roads.get("ZONES")

    sections_length = {}

    # Collect lengths of all sections
    for id, section in sections.items():
        sections_length[id] = section["length"]

    # Print summary statistics about network
    print(f"Number of nodes : {len(nodes)}")
    print(f"Number of stops : {len(stops)}")
    print(f"Number of sections : {len(sections)}")
    print(f"Number of zones: {len(zones)} | Zone IDs: {', '.join(zone['id'] for zone in zones.values())}")
    print(f"Number of sections per zone : {len(sections) / len(zones)}")

    min_length = min(sections_length.values())
    print(f"Min length of section : {min_length} for sections : {[k for k, v in sections_length.items() if v == min_length]}")
    max_length = max(sections_length.values())
    print(f"Max length of section : {max_length} for sections : {[k for k, v in sections_length.items() if v == max_length]}")

    print(f"Mean length of section : {mean(sections_length.values())}")
    print(f"Median length of section : {median(sections_length.values())}")

    print(f"Connectivity index : {len(sections) / len(nodes)}")

    df_adj = build_adjacency_matrix(network)

    deadends = identify_deadends(df_adj)
    springs = identify_springs(df_adj)
    # Isolates are nodes that are both deadends and springs
    isolates = [value for value in deadends if value in springs]
    final_sections = identify_final_sections(list(deadends))
    duplicate_sections = identify_duplicate_sections(sections)

    print(f"Number of Dead-ends: {len(deadends)}")
    #print(list(deadends))

    print(f"Number of Springs: {len(springs)}")
    #print(list(springs))

    print(f"Number of Isolate nodes: {len(isolates)}")
    #print(list(isolates))

    print((f"Number of Final sections: {len(final_sections)}"))
    #print(final_sections)

    print((f"Number of Duplicate sections: {len(duplicate_sections)}"))
    print(duplicate_sections)


# Analyze bus-specific data in the LAYERS tag if present
def analyze_bus(layers):
    for layer in layers:

        if layer["ID"] == "BUSLayer":
            lines = layer["LINES"]
            bus_line_count = len(lines)
            mapmatched_bus_list = []
            mapmatch_bus_line_count = 0
            mapmatching_rate = 0.0
            sum_mapmatching_rate = 0.0

            print(f"Number of Bus lines: {bus_line_count}")

            # Iterate over all bus lines
            for line in lines:
                id_bus_line = line["ID"]
                lsections = line["SECTIONS"]
                lsections_count = len(lsections)
                mapmatch_lsections_count = 0

                print(f"Number of sections lists for line {id_bus_line}: {lsections_count}")

                isfullymapmatch = True
                # Check if each section list is mapmatched
                for lsection in lsections:
                    ismapmatch = True
                    for section in lsection:
                        if str(section).startswith("BUS"):
                            ismapmatch = False
                            isfullymapmatch = False
                    if ismapmatch:
                        mapmatch_lsections_count = mapmatch_lsections_count + 1

                mapmatching_rate = mapmatch_lsections_count / lsections_count
                print(f"Bus line {id_bus_line} mapmatching rate: {mapmatching_rate}")
                sum_mapmatching_rate = sum_mapmatching_rate + mapmatching_rate

                if isfullymapmatch:
                    mapmatch_bus_line_count = mapmatch_bus_line_count + 1

                # TODO: value of minimum mapmatching rate to be defined
                if mapmatching_rate > 0.5:
                    mapmatched_bus_list.append(id_bus_line)

            print(f"Number of Bus lines fully map matched: {mapmatch_bus_line_count}")
            print(f"List of mapmatched bus lines (at least 50%): {mapmatched_bus_list}")
            print(f"Number of Bus lines map matched: {len(mapmatched_bus_list)}")
            print(f"Average Bus mapmatching rate: {sum_mapmatching_rate / bus_line_count}")


# Visualize nodes on a scatter plot
def visualize_nodes(roads):
    nodes = roads.get("NODES")

    fig_nodes = plt.figure("Nodes", figsize=(20, 12))
    fig_nodes.suptitle("Nodes")
    for id, node in nodes.items():
        x = float(node["position"][0])
        y = float(node["position"][1])
        plt.scatter(x, y, color="blue", s=1)


# Visualize stops on a scatter plot
def visualize_stops(roads):
    stops = roads.get("STOPS")

    fig_stops = plt.figure("Stops", figsize=(20, 12))
    fig_stops.suptitle("Stops")
    for id, stop in stops.items():
        x = float(stop["absolute_position"][0])
        y = float(stop["absolute_position"][1])
        plt.scatter(x, y, color="red", s=10)


# Visualize sections as lines connecting nodes
def visualize_sections(roads):
    nodes = roads.get("NODES")
    sections = roads.get("SECTIONS")

    fig_sections = plt.figure("Sections", figsize=(20, 12))
    fig_sections.suptitle("Sections")
    for id, section in sections.items():
        upnode = section["upstream"]
        downnode = section["downstream"]

        # Find coordinates for upstream and downstream nodes
        for id, node in nodes.items():
            if node["id"] == upnode:
                ux = float(node["position"][0])
                uy = float(node["position"][1])
            if node["id"] == downnode:
                dx = float(node["position"][0])
                dy = float(node["position"][1])

        # Draw a line between the nodes
        plt.plot([ux, dx], [uy, dy])


# Visualize zones by plotting their contours
def visualize_zones(roads):
    zones = roads.get("ZONES")
    fig_centralities = plt.figure("Zones", figsize=(20, 12))
    fig_centralities.suptitle("Zones")
    for id, res in zones.items():
        xvalues = []
        yvalues = []
        col = (np.random.random(), np.random.random(), np.random.random())
        contour = res["contour"]
        for point in contour:
            xvalues.append(float(point[0]))
            yvalues.append(float(point[1]))
        # Close the polygon by connecting last point to first
        xvalues.append(xvalues[0])
        yvalues.append(yvalues[0])
        plt.plot(xvalues, yvalues, color=col)


# Visualize node centralities with color intensity
def visualize_centralities(roads, centralities, max_degree):
    nodes = roads.get("NODES")
    xvalues = []
    yvalues = []
    dvalues = []

    # Collect node positions and degree values
    for id, degree in centralities.items():
        node = nodes[id]
        xvalues.append(float(node["position"][0]))
        yvalues.append(float(node["position"][1]))
        dvalues.append(float(degree))

    fig_centralities = plt.figure("Centralities", figsize=(20, 12))
    fig_centralities.suptitle("Centralities")
    plt.scatter(x=xvalues, y=yvalues, c=dvalues, cmap="YlOrRd", vmin=0, vmax=max_degree, s=1)


# Visualize public transport lines by plotting stops and connecting them
def visualize_pt_lines(roads, layers):
    nodes = roads.get("NODES")
    stops = roads.get("STOPS")

    for layer in layers:
        if layer["TYPE"] == "mnms.graph.layers.PublicTransportLayer":
            veh_type = layer["VEH_TYPE"]
            fig_layer = plt.figure(veh_type, figsize=(20, 12))
            fig_layer.suptitle(veh_type)
            lines = layer["LINES"]
            for line in lines:
                lstops = line["STOPS"]
                xvalues = []
                yvalues = []
                col = (np.random.random(), np.random.random(), np.random.random())
                for lstop in lstops:
                    stop = stops[lstop]
                    x = float(stop["absolute_position"][0])
                    xvalues.append(x)
                    y = float(stop["absolute_position"][1])
                    yvalues.append(y)
                    plt.scatter(x, y, color=col, s=10)
                plt.plot(xvalues, yvalues, color=col)


# Load the JSON network file from disk
def extract_file(file):
    json_file = open(file)
    network = json.load(json_file)
    json_file.close()

    return network


# Custom argparse type to check if path is valid file
def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


# Main script execution starts here
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a JSON network file for MnMS")
    parser.add_argument('network_file', type=_path_file_type, help='Path to the network JSON file')
    parser.add_argument("--visualize", default=False, type=bool,
                        help="Visualize network, True or False")

    args = parser.parse_args()

    # Extract network data from file
    network = extract_file(args.network_file)

    roads = network.get("ROADS")
    layers = network.get("LAYERS")
    valid = True

    # Check if ROADS tag exists and validate it
    if roads is None:
        print(f"No tag ROADS found in JSON network file")
        valid = False
    else:
        valid = validate_roads(roads)

    # If valid, run analysis and optionally visualization
    if valid:
        analyze_roads(roads)
        # analyze_bus(layers)

        # centralities = compute_centralities(roads)
        # print(f"Node with maximum centrality degree : {max(centralities, key=centralities.get)} = {max(centralities.values())}")

        if args.visualize:
            visualize_nodes(roads)
            visualize_stops(roads)
            visualize_sections(roads)
            # visualize_centralities(roads, centralities, max(centralities.values()))
            visualize_zones(roads)
            visualize_pt_lines(roads, layers)
            plt.show()
