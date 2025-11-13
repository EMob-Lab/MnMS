#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: cecile.becarie, christophe.tettarassar
"""

import os
import argparse
import json
import matplotlib as mpl
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import numpy as np
import contextily as ctx
import pyproj
from shapely.geometry import LineString, Point
from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection
from datetime import datetime
from datetime import timedelta, time


def project_to_webmercator(x, y):
    """Convert Lambert 93 (EPSG:2154) to Web Mercator (EPSG:3857)"""
    transformer = pyproj.Transformer.from_crs(2154, 3857, always_xy=True)
    return transformer.transform(x, y)


def notify_PV(g):
    if g.iloc[0].STATE == 'SERVING':
        g.STATE = 'PV'
    return g


def timedelta_to_time(total_secondes):
    heures = int(total_secondes) // 3600 % 24
    minutes = (int(total_secondes) % 3600) // 60
    secondes = int(total_secondes) % 60
    return time(heures, minutes, secondes, 0)


def update(n):
    time_current = time_init + (flow_dt * n)
    time_step_mn = time_mn_init + int(flow_dt.total_seconds()) * n
    time_text.set_text(time_current.strftime(time_template))
    print(n, time_current.strftime(time_template))

    # Users
    if time_current.strftime("%H:%M:%S.00") in df_grouped_users.groups.keys():
        df_current_users = df_grouped_users.get_group(time_current.strftime("%H:%M:%S.00"))
        print('users ',len(df_current_users))
        arr_current_users = df_current_users[['X', 'Y']].copy().to_numpy()
        scat_users.set_offsets(arr_current_users)

        user_number_text.set_text('# users: ' + str(len(df_current_users['ID'].unique())))

    # Vehicles
    if time_current.strftime("%H:%M:%S.00") in df_grouped_vehs.groups.keys():
        df_current_veh = df_grouped_vehs.get_group(time_current.strftime("%H:%M:%S.00"))
        print('vehicles ',len(df_current_veh))
        arr_current_veh = df_current_veh[['X', 'Y']].copy().to_numpy()
        scat_vehs.set_offsets(arr_current_veh)

        cv = [color_vehs[t] for t in df_current_veh['STATE'].to_list()]
        scat_vehs.set_color(cv)

        veh_number_text.set_text('# vehicles: ' + str(len(cv)))

    return scat_vehs, scat_users,


# Custom argparse type to check if path is valid file
def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Demonstrator OpenStreetMap")
    parser.add_argument('network_file', type=_path_file_type, help='Path to the network JSON file')
    parser.add_argument('vehicles_file', type=_path_file_type, help='Path to the vehicles CSV file')
    parser.add_argument('users_file', type=_path_file_type, help='Path to the users CSV file')
    # parser.add_argument('--simulation_duration', type=int, default=None) # simulation duration (in seconds)

    args = parser.parse_args()

    # Settings
    network_file = args.network_file
    vehicles_file = args.vehicles_file
    users_file = args.users_file

    flow_dt = timedelta(seconds=1)
    simulation_duration = 3600
    time_init = datetime(2023, 12, 14, 6, 30, 0)

    # Plot setting
    color_vehs = {'STOP': 'green', 'PICKUP': 'orange', 'SERVING': 'blue', 'PV': 'red'}
    color_veh_type = {'Bus': 'green', 'Tram': 'magenta', 'Metro': 'red'}

    # Load the network json file
    with open(network_file, 'r') as f:
        data = json.load(f)

    # Road DB
    sections = data['ROADS']['SECTIONS']
    nodes = data['ROADS']['NODES']
    stops = data['ROADS']['STOPS']

    # Layers
    lines_car = []
    lines_PT = []
    stopsX = dict()
    stopsY = dict()

    for layer in data['LAYERS']:

        if layer['TYPE'] == 'mnms.graph.layers.CarLayer':
            layer_car_links = layer['MAP_ROADDB']['LINKS']
            for key, roaddb_element in layer_car_links.items():
                section = sections[roaddb_element[0]]
                ups = section['upstream']
                downs = section['downstream']
                lines_car.append([nodes[ups]['position'], nodes[downs]['position']])

        if layer['TYPE'] == 'mnms.graph.layers.PublicTransportLayer':

            s_veh_type = layer['VEH_TYPE'][layer['VEH_TYPE'].rfind('.')+1:]
            color_layer = color_veh_type[s_veh_type]

            stops_X = []
            stops_Y = []
            lines_tmp = []
            for line in layer['LINES']:
                line_pt = []
                for stop in line['STOPS']:
                    stop_db = stops[stop]
                    line_pt.append(stop_db['absolute_position'])

                    stops_X.append(stop_db['absolute_position'][0])
                    stops_Y.append(stop_db['absolute_position'][1])

                lines_tmp.append(line_pt)
            lines_PT.append({'id': layer['ID'], 'lines': lines_tmp, 'color':color_layer, 'label': s_veh_type + ' lane'})

            stopsX[layer['ID']] = stops_X
            stopsY[layer['ID']] = stops_Y

    # Build a GeoDataFrame for the road network
    gdf_roads = gpd.GeoDataFrame(
        geometry=[LineString(line) for line in lines_car],
        crs="EPSG:2154"  # Lambert 93
    ).to_crs(epsg=3857)  # Convert to Web Mercator

    # Vehicles
    df_vehs = pd.read_csv(vehicles_file, sep=';')
    df_vehs.drop(df_vehs[df_vehs['POSITION'].isna() == True].index, inplace=True)

    df_vehs['TIME_STEP'] = df_vehs.apply(lambda x: datetime.strptime(x['TIME'], "%H:%M:%S.%f").hour * 3600 + datetime.strptime(x['TIME'],
                                        "%H:%M:%S.%f").minute * 60 + datetime.strptime(
                                        x['TIME'], "%H:%M:%S.%f").second, axis=1)

    # Complete data for each missing time step
    df_vehs = df_vehs.groupby('ID', group_keys=False).apply(notify_PV)

    df_grouped_vehs_by_id = df_vehs.groupby('ID')

    new_rows = []
    for id, group in df_grouped_vehs_by_id:

        print('veh ', id)

        bUber = False
        #if len(group[group.STATE == 'STOP']) > 0:
        for index, row in group[group.STATE == 'STOP'].iterrows():
            #d1 = group[group.STATE == 'STOP'].iloc[0].TIME_STEP
            d1 = row.TIME_STEP
            red_group=group[group.TIME_STEP > d1]
            d2 = d1
            if d1 > 0:
                if len(red_group[red_group.STATE == 'PICKUP']) > 0:
                    bUber = True
                    d2 = red_group[red_group.STATE == 'PICKUP'].iloc[0].TIME_STEP
                else:
                    if bUber:
                        d2 = df_vehs.tail(1).TIME_STEP.values[0]

                if d2 - d1 > flow_dt.total_seconds():
                    for n in range(1, d2 - d1):
                        new_row = row.copy()
                        new_row.TIME_STEP = d1 + n * flow_dt.total_seconds()
                        new_row.TIME = timedelta_to_time(new_row.TIME_STEP).strftime("%H:%M:%S.00")
                        new_rows.append(new_row)

    df_new_rows = pd.DataFrame(new_rows)

    df_vehs = pd.concat([df_vehs, pd.DataFrame(df_new_rows)], ignore_index=True)

    df_vehs = df_vehs.sort_values(by=['TIME'])

    #df_vehs.to_csv("vehs_ext.csv", index=False, sep=';')

    time_mn_init = time_init.hour * 3600 + time_init.minute * 60

    df_vehs['sep'] = df_vehs['POSITION'].str.find(' ')
    df_vehs['X'] = df_vehs.apply(lambda x : float(x['POSITION'][:x['sep']]), axis=1)
    df_vehs['Y'] = df_vehs.apply(lambda x : float(x['POSITION'][x['sep']+1:]), axis=1)
    df_vehs['X'], df_vehs['Y'] = project_to_webmercator(df_vehs['X'], df_vehs['Y'])

    df_grouped_vehs = df_vehs.groupby('TIME')

    # Users
    df_users = pd.read_csv(users_file, sep=';')

    df_users = df_users.drop(df_users[df_users.STATE == 'DEADEND'].index)

    df_users['TIME_STEP'] = df_users.apply(lambda x: datetime.strptime(x['TIME'], "%H:%M:%S.%f").hour * 3600 + (
        datetime.strptime(x['TIME'], "%H:%M:%S.%f").minute) * 60 + datetime.strptime(x['TIME'], "%H:%M:%S.%f").second,
                                           axis=1)

    # Complete data for each missing time step
    df_grouped_users_by_id = df_users.groupby('ID')
    new_rows = []
    for id, group in df_grouped_users_by_id:

        print('user ', id)
        group.sort_values(by=['TIME'])

        if len(group[group.STATE == 'WAITING_ANSWER']) > 0:
            d1 = group[group.STATE == 'WAITING_ANSWER'].iloc[0].TIME_STEP
            d2 = d1
            if d1 > 0:
                if len(group[group.STATE == 'INSIDE_VEHICLE']) > 0:
                    d2 = group[group.STATE == 'INSIDE_VEHICLE'].iloc[0].TIME_STEP
                else:
                    if len(group[group.STATE == 'STOP']):
                        d2 = group[group.STATE == 'STOP'].iloc[0].TIME_STEP

                if d2 - d1 > flow_dt.total_seconds():
                    for n in range(1, d2 - d1):
                        new_row = group[group.STATE == 'WAITING_ANSWER'].iloc[0]
                        new_row.TIME_STEP = group[group.STATE == 'WAITING_ANSWER'].iloc[0].TIME_STEP+n*flow_dt.total_seconds()
                        new_row.TIME = timedelta_to_time(new_row.TIME_STEP).strftime("%H:%M:%S.00")
                        new_rows.append(new_row)

    df_new_rows = pd.DataFrame(new_rows)
    df_users = pd.concat([df_users, pd.DataFrame(df_new_rows)], ignore_index=True)

    df_users=df_users.sort_values(by=['TIME'])

    #df_users.to_csv("users_ext.csv", index=False, sep=';')

    df_users['sep'] = df_users['POSITION'].str.find(' ')
    df_users['X'] = df_users.apply(lambda x: float(x['POSITION'][:x['sep']]), axis=1)
    df_users['Y'] = df_users.apply(lambda x: float(x['POSITION'][x['sep'] + 1:]), axis=1)
    df_users['X'], df_users['Y'] = project_to_webmercator(df_users['X'], df_users['Y'])
    #df_users['TIME_STEP']=df_users.apply(lambda x : datetime.strptime(x['TIME'], "%H:%M:%S.%f").hour*60 + datetime.strptime(x['TIME'], "%H:%M:%S.%f").minute, axis=1)
    #
    df_users['TIME_STEP'] = df_users.apply(lambda x: datetime.strptime(x['TIME'], "%H:%M:%S.%f").hour * 3600 + (datetime.strptime(x['TIME'], "%H:%M:%S.%f").minute) * 60 + datetime.strptime(x['TIME'], "%H:%M:%S.%f").second, axis = 1)
    #
    df_grouped_users = df_users.groupby('TIME')

    # Plot
    figsize = (24, 9)
    colors = ['b', 'g', 'tomato', 'blue', 'magenta']
    fig = plt.figure(figsize=figsize)
    ax1 = fig.add_subplot(1, 1, 1)

    # Plot the road network first
    gdf_roads.plot(ax=ax1, color='grey', linewidth=1, label='road network')

    # Add the OpenStreetMap basemap
    ctx.add_basemap(ax1, crs=gdf_roads.crs, source=ctx.providers.OpenStreetMap.Mapnik)

    lc_car = LineCollection(lines_car, linewidths=1)
    lc_car.set_color('grey')
    lc_car.set_label('roads network')
    ax1.add_collection(lc_car)

    c = 0
    #colors = ['b','g','tomato','blue','magenta']
    #label= ['bus line','metro line','tram line']
    for l in lines_PT:
        lc_pt = LineCollection(l['lines'], linewidths=3, alpha=0.2)
        lc_pt.set_color(l['color'])
        lc_pt.set_label(l['label'])
        ax1.add_collection(lc_pt)
        ax1.scatter(stopsX[l['id']], stopsY[l['id']], s=20, color=l['color'], alpha=0.2)
        c = c+1

    #ax1.autoscale()
    ax1.set_aspect('equal')
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.set_frame_on(False)

    # Timer
    time_template = "%H:%M:%S"
    time_text = ax1.text(0.4, -0.05, time_init.strftime(time_template), transform=ax1.transAxes, fontsize=18)
    time_text.set_bbox(dict(facecolor='grey', alpha=0.5))
    time_text.set_text(time_init.strftime(time_template))

    # Vehicle and user number display
    veh_number_text = ax1.text(0.6, -0.05, '# vehicles: 0', transform=ax1.transAxes, fontsize=16)
    user_number_text = ax1.text(0.6, -0.12, '# users: 0', transform=ax1.transAxes, fontsize=16)

    # Vehicles
    scat_vehs = ax1.scatter([], [], c='black', s=30, marker='h',alpha=0.8)
    # Only for legend
    PV_legend = ax1.scatter([], [], c=color_vehs['PV'], s=50, marker='h',alpha=0.8, label='Personal vehicle')
    OnDemand_STOP_legend = ax1.scatter([], [], c=color_vehs['STOP'], s=50, marker='h', alpha=0.8, label='On demand vehicle waiting')
    OnDemand_PICKUP_legend = ax1.scatter([], [], c=color_vehs['PICKUP'], s=50, marker='h', alpha=0.8,
                                       label='On demand vehicle to pick up')
    OnDemand_SERVING_legend = ax1.scatter([], [], c=color_vehs['SERVING'], s=50, marker='h', alpha=0.8,
                                       label='On demand vehicle in service')


    # Users
    scat_users = ax1.scatter([], [], c='red', s=10, marker='x', label='User')

    plt.legend(handles=[scat_users, PV_legend, OnDemand_STOP_legend, OnDemand_PICKUP_legend, OnDemand_SERVING_legend], loc=(0.8, 0.8))

    animALL = FuncAnimation(fig, update, frames=simulation_duration+1, interval=100, repeat=False, blit=False)

    backup = True
    if backup:
        aniWriter = mpl.animation.writers['ffmpeg']
        aniWriter = aniWriter(fps=5)
        animALL.save('video.mp4', writer=aniWriter)

    plt.show()
