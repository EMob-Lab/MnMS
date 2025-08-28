# Validation scripts

This repository contains Python scripts for visualizing MnMS network files.

---

## Folium visualization

This Python script loads an MnMS network file and visualizes it using Folium (installation command further below).  
It converts coordinates from Lambert 93 to WGS84 and renders Metro, Tram, and Bus stops and sections on an interactive map.

### Features

- **Coordinate conversion**
  - Converts network data from Lambert 93 (EPSG:2154) → WGS84 (EPSG:4326).

  
- **Visualization with Folium**
  - Plots stops as colored markers depending on transport type.
  - Draws sections (links) between stops as colored polylines.
  - Supports Metro, Tram, and Bus layers.

  
- **Interactivity**
  - Layer control allows toggling of different transport modes.
  - Tooltips on stops show the stop ID and transport type.
 
 
- **Output**
  - Saves an interactive HTML map (`folium_map.html`).

### Script structure

- `convert_from_lambert(x, y)` – Converts coordinates from Lambert 93 to WGS84 (latitude, longitude).

### Installation

Install missing dependencies with:

````bash
pip install folium
````

````bash
pip install pyproj
````

### Usage example

````bash 
python validate_network.py mnms_network.json --visualize True
````

- `network_file` – Path to the MnMS network JSON file.

The script will produce as an output:

- `folium_map.html` – Interactive HTML map viewable in any browser.
- Example of color map visualization:
  - Red markers & lines, 5 weight value → Metro
  - Purple markers & lines, 3 weight value → Tram
  - Green markers & lines, 1 weight value → Bus
- Each layer can be toggled on/off in the interactive map.
  
### Notes

Coordinates format used in this script is Lambert 93, other coordinate system can be used.
Color map can be customized as well

---

## Notebook visualization

README description in progress