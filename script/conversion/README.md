# Conversion scripts

This repository contains Python scripts for converting various network format to MnMS specific network format.

---

## Bison conversion

### Features

### Script structure

### Installation

### Usage example

### Notes

---

## GTFS conversion

This Python script converts GTFS (General Transit Feed Specification) public transport data into an MnMS-compatible JSON network file.

### Features

- Parses GTFS .zip archives as input.
- Uses an existing MnMS road network JSON file as the base.
- Generates an MnMS JSON network representation of the public transport network.

### Script structure

- `cleanString(input_string: str) -> str` – Cleans and normalizes input strings by removing problematic characters (e.g., spaces, special symbols).
This ensures stop names and line identifiers are safe for processing and storage.


- `secondsToMnMsTime(seconds: int) -> str` – Converts time expressed in seconds since midnight into MnMS time format (HH:MM:SS).
Used when adapting GTFS times to MnMS simulation requirements.


- `generate_nx_graph(roads: dict) -> networkx.Graph` – Builds a NetworkX graph representation of the road network from MnMS JSON data.
Each node corresponds to a road node, and each edge represents a road section.


- `closest_node(x: float, y: float, G: networkx.Graph) -> str` – Finds the closest graph node in G to the given coordinates (x, y).
Used for assigning GTFS stops to road network nodes.


- `closest_edge(x: float, y: float, G: networkx.Graph) -> str` – Finds the closest edge (road section) in G to the given coordinates (x, y).
Useful for mapping stops to sections when no node is nearby.


- `getLongestTripStops(trips: dict, stop_times: dict) -> list` – From the GTFS dataset, extracts the longest trip (in terms of number of stops) for each line.
This ensures that the main representative route is used when constructing MnMS lines.


- `gps_inside_box(x: float, y: float, bbox: list) -> bool` – Checks whether the coordinates (x, y) lie inside a given bounding box.
Used to filter out stops that fall outside the target network area.


- `filter_line(line: dict, bbox: list) -> dict` – Filters a GTFS line so that only stops inside the bounding box are kept.
This ensures only relevant transit data is processed.


- `extract_gtfs_stops(gtfs_zip: str) -> dict` – Reads a GTFS archive (.zip) and extracts all stops, mapping them to their coordinates.
Stops are later mapped to MnMS network nodes/sections.


- `generate_public_transportation_lines(gtfs_data: dict, roads: dict) -> dict` – Generates MnMS public transportation lines (routes and stops) from GTFS data.
This provides a first raw conversion into MnMS-compatible structures.


- `generate_map_matching_pt_lines(gtfs_data: dict, G: networkx.Graph, roads: dict) -> dict` – Improves the public transportation lines by performing map matching of stops to the road graph G.
Ensures that generated lines align properly with the MnMS road network.


- `register_pt_lines(roads: dict, pt_lines: dict) -> dict` – Registers the generated public transport lines into the MnMS network JSON.
Updates the ROADS section with PT-specific data.


- `register_map_match_pt_lines(roads: dict, matched_lines: dict) -> dict` – Registers the map-matched PT lines into the MnMS network JSON.
This overwrites/updates existing PT definitions with more accurate ones.


### Installation

### Usage example

````bash 
python conversion_gtfs.py lyon_gtfs.zip lyon_roads.json lyon_gtfs.json
````

- `gtfs_file` – Path to the MnMS network JSON file.
- `mnms_roads_file` – Path to the MnMS network JSON file.
- `mnms_output_file` – Path to the new MnMS network file (created by the script if it doesn’t exist yet)

### Notes

- The GTFS ZIP file must follow standard GTFS format (stops.txt, routes.txt, trips.txt, etc.).
- The script assumes the road network file is already in MnMS JSON format.


---

## NetworkX conversion

This script converts an MnMS network JSON file into a NetworkX MultiDiGraph JSON file.
It enables users and developers to leverage the NetworkX library for advanced graph analysis and visualization.

### Features

- Load MnMS graph using mnms.io.graph.load_graph.
- Extract nodes and sections.
- Convert to a NetworkX MultiDiGraph.
- Serialize to JSON node-link format.
- Save to an output file.

### Script structure

- `generate_nx_graph(nodes, sections) -> nx.MultiDiGraph` – Converts MnMS graph data (nodes and sections) into a NetworkX MultiDiGraph:
  - Adds nodes with positional attributes (x, y).
  - Adds directed edges representing road sections with id and length.

### Installation

Install missing dependencies with:

````bash
pip install networkx
````

### Usage example

````bash 
python conversion_nx.py mnms_network.json output/networkx_graph.json
````

- `network_file` – Path to the input MnMS network JSON file. Must exist.
- `networkx_output_file` – Path to the new NetworkX JSON file. Directory must exist, file can be new.

The script will produce as an output, a JSON file containing the NetworkX graph in node-link format.

Example NetworkX structure:

````json
{
  "directed": true,
  "multigraph": true,
  "nodes": [
    {"id": "N1", "position": [0.0, 0.0]},
    {"id": "N2", "position": [10.0, 5.0]}
  ],
  "links": [
    {"source": "N1", "target": "N2", "id": "S1", "length": 100.0}
  ]
}
````

### Notes

---

## OpenStreetMap conversion

### Features

### Script structure

### Installation

### Usage example

### Notes

---

## Symuflow conversion

### Features

### Script structure

### Installation

### Usage example

### Notes
