import json
import folium
from pyproj import Transformer, CRS

# Define coordinate systems
lambert_93 = CRS("EPSG:2154")  # Lambert 93
wgs84 = CRS("EPSG:4326")       # WGS84

# Create transformer: FROM Lambert -> TO WGS84
transformer = Transformer.from_crs(lambert_93, wgs84, always_xy=True)

def convert_from_lambert(x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon


def extract_file(file):
    with open(file, "r") as json_file:
        return json.load(json_file)


mnms_network = extract_file("lyon_mnms_restricted_gtfs_bus_tram_metro.json")

roads = mnms_network.get("ROADS")
layers = mnms_network.get("LAYERS")
stops = roads.get("STOPS")
sections = roads.get("SECTIONS")

m = folium.Map(location=[45.75, 4.85], zoom_start=12, tiles='cartodbpositron')

radius_map = {
    "mnms.vehicles.veh_type.Metro": 5,
    "mnms.vehicles.veh_type.Tram": 3,
    "mnms.vehicles.veh_type.Bus": 1
}

color_map = {
    "mnms.vehicles.veh_type.Metro": "#ff0000",
    "mnms.vehicles.veh_type.Tram": "#a600ff",
    "mnms.vehicles.veh_type.Bus": "#10b400"
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

# To avoid duplicates stops
plotted_stops = set()

for layer in layers:

    veh_type = layer["VEH_TYPE"]
    radius = radius_map.get(veh_type)
    color = color_map.get(veh_type)
    weight = weight_map.get(veh_type)
    opacity = opacity_map.get(veh_type)

    mobility = veh_type.split('.')[-1]
    fg = folium.FeatureGroup(name=mobility, show=True).add_to(m)

    if color:
        lines = layer["LINES"]
        for line in lines:
            line_stops = line["STOPS"]

            # Render stops
            for stop_id in line_stops:
                stop = stops[stop_id]
                if stop_id not in plotted_stops:
                    y = float(stop["absolute_position"][1])
                    x = float(stop["absolute_position"][0])

                    lat, lon = convert_from_lambert(x, y)

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

            # Render sections/links
            for stop_id in line_stops:
                stop = stops[stop_id]
                sec_id = stop.get("section")
                if sec_id and sec_id in sections:
                    sec = sections[sec_id]
                    up_id = sec["upstream"]
                    down_id = sec["downstream"]

                    if up_id in stops and down_id in stops:
                        up = stops[up_id]["absolute_position"]
                        down = stops[down_id]["absolute_position"]
                        up_0, up_1 = convert_from_lambert(up[0], up[1])
                        down_0, down_1 = convert_from_lambert(down[0], down[1])

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

folium.LayerControl().add_to(m)
m.save("folium_test.html")
