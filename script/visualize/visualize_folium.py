import os
import argparse
import json
import folium
from pyproj import Transformer, CRS


# Function to convert Lambert 93 coordinates to WGS84 (lat, lon)
def convert_from_lambert(transformer, x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon

# -----------------------------------
# Data Loading
# -----------------------------------

# Load JSON file containing transportation network data
def extract_file(file):
    with open(file, "r") as json_file:
        return json.load(json_file)

# Validates that the argument path is a valid file
def _path_file_type(path):
    """
    Validates that the given path is a valid file.
    """
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


# Helper function for output path (no need to exist)
def _output_file_type(path):
    """
    Validates only the directory part of the path exists,
    but allows the file itself to not exist yet.
    """
    directory = os.path.dirname(path) or "."
    if os.path.isdir(directory):
        return path
    else:
        raise argparse.ArgumentTypeError(f"Directory {directory} does not exist")


# --------------------------- Entry Point ---------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize an MnMS network file with folium")
    parser.add_argument('network_file', type=_path_file_type, help='Path to the network JSON file')
    parser.add_argument('folium_html_file', type=_output_file_type, help='Path to the folium HTML visualization file')

    args = parser.parse_args()

    # Load the mobility network (GTFS-like format)
    mnms_network = extract_file(args.network_file)

    # Extract relevant sections of the data
    roads = mnms_network.get("ROADS")
    layers = mnms_network.get("LAYERS")
    stops = roads.get("STOPS")
    sections = roads.get("SECTIONS")

    # -----------------------------------
    # Map Setup with Folium
    # -----------------------------------

    # Initialize Folium map centered on Lyon, France
    m = folium.Map(location=[45.75, 4.85], zoom_start=12, tiles='cartodbpositron')

    # Appearance configuration for different vehicle types
    radius_map = {
        "mnms.vehicles.veh_type.Metro": 5,
        "mnms.vehicles.veh_type.Tram": 3,
        "mnms.vehicles.veh_type.Bus": 1
    }

    color_map = {
        "mnms.vehicles.veh_type.Metro": "#ff0000",  # Red
        "mnms.vehicles.veh_type.Tram": "#a600ff",  # Purple
        "mnms.vehicles.veh_type.Bus": "#10b400"  # Green
    }

    weight_map = {
        "mnms.vehicles.veh_type.Metro": 5,
        "mnms.vehicles.veh_type.Tram": 3,
        "mnms.vehicles.veh_type.Bus": 1
    }

    opacity_map = {
        "mnms.vehicles.veh_type.Metro": 0.8,
        "mnms.vehicles.veh_type.Tram": 0.5,
        "mnms.vehicles.veh_type.Bus": 0.3
    }

    # Track which stops have already been drawn to avoid duplicates
    plotted_stops = set()

    # -----------------------------------
    # Coordinate System Setup
    # -----------------------------------

    # Define source and target coordinate systems using EPSG codes
    lambert_93 = CRS("EPSG:2154")  # Lambert 93 (used in France)
    wgs84 = CRS("EPSG:4326")  # WGS84 (global latitude/longitude)

    # Create a transformer to convert Lambert 93 → WGS84
    transformer = Transformer.from_crs(lambert_93, wgs84, always_xy=True)

    # -----------------------------------
    # Drawing Layers: Stops & Routes
    # -----------------------------------

    # Loop through each transport mode layer (e.g. Metro, Bus, Tram)
    for layer in layers:
        veh_type = layer["VEH_TYPE"]  # Full string like "mnms.vehicles.veh_type.Metro"

        # Visual styling for the current transport type
        radius = radius_map.get(veh_type)
        color = color_map.get(veh_type)
        weight = weight_map.get(veh_type)
        opacity = opacity_map.get(veh_type)

        mobility = veh_type.split('.')[-1]  # Extract "Metro", "Bus", or "Tram"

        # Create a separate layer for this vehicle type
        fg = folium.FeatureGroup(name=mobility, show=True).add_to(m)

        if color:
            lines = layer["LINES"]

            # Loop through each line within this vehicle type
            for line in lines:
                line_stops = line["STOPS"]

                # ---- Render Stops ----
                for stop_id in line_stops:
                    stop = stops[stop_id]
                    if stop_id not in plotted_stops:
                        y = float(stop["absolute_position"][1])
                        x = float(stop["absolute_position"][0])

                        # Convert from Lambert 93 to WGS84
                        lat, lon = convert_from_lambert(transformer, x, y)

                        # Draw stop as a CircleMarker
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=radius,
                            tooltip=f"{mobility}: {stop_id}",
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.9
                        ).add_to(fg)

                        plotted_stops.add(stop_id)

                # ---- Render Sections (Links between Stops) ----
                for stop_id in line_stops:
                    stop = stops[stop_id]
                    sec_id = stop.get("section")  # Get associated section if available

                    if sec_id and sec_id in sections:
                        sec = sections[sec_id]
                        up_id = sec["upstream"]
                        down_id = sec["downstream"]

                        # Make sure both ends of the section exist
                        if up_id in stops and down_id in stops:
                            up = stops[up_id]["absolute_position"]
                            down = stops[down_id]["absolute_position"]

                            # Convert endpoints from Lambert to WGS84
                            up_0, up_1 = convert_from_lambert(transformer, up[0], up[1])
                            down_0, down_1 = convert_from_lambert(transformer, down[0], down[1])

                            # Draw the section as a line
                            folium.PolyLine(
                                locations=[
                                    [float(up_0), float(up_1)],
                                    [float(down_0), float(down_1)]
                                ],
                                color=color,
                                weight=weight,
                                fill=True,
                                opacity=opacity
                            ).add_to(fg)

    # -----------------------------------
    # Final Map Rendering
    # -----------------------------------

    # Add layer control so user can toggle Metro/Bus/Tram layers
    folium.LayerControl().add_to(m)

    # Save map to HTML
    m.save(args.folium_html_file)
