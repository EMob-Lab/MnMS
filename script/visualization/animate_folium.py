import os
import argparse
import json
import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
from pyproj import Transformer, CRS


# Init transformer (Lambert93 -> WGS84)
transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

# Function to convert Lambert 93 coordinates to WGS84 (lat, lon)
def convert_from_lambert(x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon

# CSV import
df = pd.read_csv("veh.csv", sep=";")

# Filter states
valid_states = ["STOP", "PICKUP", "SERVING"]
df = df[df['STATE'].isin(valid_states)]

# Split POSITION column (Lambert93 coordinates)
df[['X', 'Y']] = df['POSITION'].str.split(' ', expand=True)
df['X'] = pd.to_numeric(df['X'], errors='coerce')
df['Y'] = pd.to_numeric(df['Y'], errors='coerce')

# Split LINK column
df[['FROM', 'TO']] = df['LINK'].str.split(' ', expand=True)

# Drop rows with missing coords
df = df.dropna(subset=['X', 'Y'])

# Apply conversion (ignore NaN rows)
df[['lat', 'lon']] = df.dropna(subset=['X', 'Y']).apply(
    lambda r: convert_from_lambert(r['X'], r['Y']), axis=1, result_type="expand"
)

df['TIME'] = pd.to_datetime(df['TIME'], format="%H:%M:%S.%f")

# Sort by vehicle ID and time
df = df.sort_values(["ID", "TIME"])

# Identify segments where state changes
df['STATE_CHANGE'] = (df['STATE'] != df.groupby("ID")['STATE'].shift()).astype(int)
df['SEGMENT'] = df.groupby("ID")['STATE_CHANGE'].cumsum()

# Aggregate per segment (one row per vehicle-state interval)
segments = df.groupby(['ID', 'TYPE', 'FROM', 'TO', 'STATE', 'SEGMENT']).agg(
    START_TIME=('TIME', 'first'),
    END_TIME=('TIME', 'last'),
    LAT=('lat', 'first'),
    LON=('lon', 'first')
).reset_index()

# Extend END_TIME a bit so the point stays visible
segments['END_TIME'] = segments['END_TIME'] + pd.Timedelta(minutes=1)

# Format times
segments['START_TIME'] = segments['START_TIME'].dt.strftime("2023-01-01 %H:%M:%S")
segments['END_TIME']   = segments['END_TIME'].dt.strftime("2023-01-01 %H:%M:%S")

# Colors by TYPE
colors = {
    "Bus": "green",
    "Tram": "magenta",
    "Metro": "red"
}

# Radius by TYPE
radius = {
    "Bus": 2,
    "Tram": 4,
    "Metro": 6
}

# Build features for TimestampedGeoJson
features = []
for _, row in segments.iterrows():
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [row['LON'], row['LAT']],  # folium expects lon, lat
        },
        "properties": {
            "times": [row["START_TIME"], row["END_TIME"]],
            "popup": f"ID: {row['ID']}<br>Type: {row['TYPE']}<br>From: {row['FROM']}<br>To: {row['TO']}<br>State: {row['STATE']}",
            "icon": "circle",
            "iconstyle": {
                "fillColor": colors.get(row['TYPE'], "black"),
                "fillOpacity": 0.7,
                "stroke": "true",
                "radius": radius.get(row['TYPE'])
            }
        }
    }
    features.append(feature)

# Create Folium map (centered roughly on Lyon)
m = folium.Map(location=[45.75, 4.85], zoom_start=12)

# Add animated layer
TimestampedGeoJson(
    {"type": "FeatureCollection", "features": features},
    period="PT1M",       # time resolution (1 minute)
    add_last_point=False,
    auto_play=True,
    loop=False,
    max_speed=10,
).add_to(m)

# Save
m.save("animated_map.html")
print("Map saved as animated_map.html")