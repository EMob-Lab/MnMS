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
    parser.add_argument('CRS_src', type=str, help='Coordinate Reference System of the network')
    parser.add_argument('folium_html_file', type=_output_file_type, help='Path to the folium HTML visualization file', nargs='?', default='')

    args = parser.parse_args()

    output_folium_file = args.folium_html_file
    if not output_folium_file:
        output_folium_file = os.path.splitext(args.network_file)[0]+'.html'

    CRS_src = args.CRS_src


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
    m = folium.Map(tiles='cartodbpositron')

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
        "mnms.vehicles.veh_type.Metro": 4,
        "mnms.vehicles.veh_type.Tram": 3,
        "mnms.vehicles.veh_type.Bus": 2
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
    wgs84 = CRS("EPSG:4326")  # WGS84 (global latitude/longitude)

    # Create a transformer to convert Lambert 93 → WGS84
    transformer = Transformer.from_crs(CRS_src, wgs84, always_xy=True)

    # -----------------------------------
    # Drawing Sections
    # -----------------------------------
    sections=roads['SECTIONS']
    nodes = roads['NODES']

    min_lat = 90
    max_lat = -90
    min_lon = 180
    max_lon = -180

    for key, val_node in nodes.items():
        x = float(val_node["position"][0])
        y = float(val_node["position"][1])
        val_node['lat'], val_node['lon'] = convert_from_lambert(transformer, x, y)
        min_lat = min(min_lat, val_node['lat'])
        max_lat = max(max_lat, val_node['lat'])
        min_lon = min(min_lon, val_node['lon'])
        max_lon = max(max_lon, val_node['lon'])

    fg = folium.FeatureGroup(name='sections', show=True).add_to(m)
    for key, val_section in sections.items():

        up_0 = nodes[val_section['upstream']]['lat']
        up_1 = nodes[val_section['upstream']]['lon']

        down_0 = nodes[val_section['downstream']]['lat']
        down_1 = nodes[val_section['downstream']]['lon']

        # Draw the section

        folium.PolyLine(
            locations=[
                [up_0, up_1],
                [down_0, down_1]
            ],
            color='black',
            weight=2,
            tooltip=f"{'section'}: {key}",
            fill=True,
            opacity=0.3
        ).add_to(fg)

    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

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

        if color:
            # Create a separate layer for this vehicle type
            fg = folium.FeatureGroup(name=mobility, show=True).add_to(m)

            lines = layer["LINES"]

            # Loop through each line within this vehicle type
            for line in lines:
                line_stops = line["STOPS"]
                prev_stop = None

                # ---- Render Stops ----
                for stop_id in line_stops:
                    stop = stops[stop_id]
                    if stop_id not in plotted_stops:
                        y = float(stop["absolute_position"][1])
                        x = float(stop["absolute_position"][0])

                        # Convert from Lambert 93 to WGS84
                        lat, lon = convert_from_lambert(transformer, x, y)

                        stop['lat']=lat
                        stop['lon'] = lon

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

                    if prev_stop:
                        # Draw the section
                        folium.PolyLine(
                            locations=[
                                [prev_stop['lat'], prev_stop['lon']],
                                [lat, lon]
                            ],
                            color=color,
                            weight=weight,
                            tooltip=f"{mobility}: {line['ID']}",
                            fill=True,
                            opacity=opacity
                        ).add_to(fg)

                    prev_stop = stop




    # Add layer control so user can toggle Metro/Bus/Tram layers
    folium.LayerControl().add_to(m)

    # Save map to HTML
    m.save(output_folium_file)
