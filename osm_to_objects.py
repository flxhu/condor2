#!/usr/bin/env python3
import argparse
import json
import math
import os.path

# pip install ...
import requests
import pyproj

# Configuration
BOUNDING_BOX = (50.1, 11.6, 54.8,  15.25)
UTM_ZONE = 33
WIND_GENERATOR_NAME = "Eolienne2.c3d" 
POWER_TOWER_NAME = "Powertower.c3d"

# Constants
URL = "https://overpass-api.de/api/interpreter"
WIND_GENERATOR_TERM = "\"generator:source\"=\"wind\""
POWER_TOWER_TERM = "\"power\"=\"tower\""

def get_query(bbox, term):
    return f"""
[out:json][timeout:120];
(
node[{term}]{bbox};
);
out body;
>;
out skel qt;
"""

def query_overpass(term, bbox, filename):
    query = get_query(bbox, term)
    print(query)
    if os.path.exists(filename):
        print(filename, "already exists")
        return

    r = requests.post(url=URL, data=query)

    with open(filename, "w", encoding='utf-8') as f:
        f.write(r.text)

def find_nearest(osm_data, node):
    nearest = None
    dist = 999999999999
    for other in osm_data:
        if other == None or other == node:
            continue
        lon_dist = node['lon'] - other['lon']
        lat_dist = node['lat'] - other['lat']
        d = lon_dist * lon_dist + lat_dist * lat_dist
        if d < dist and d > 0.0001:
            dist = d
            nearest = other
    return nearest

def angle(v1, v2):
    d = (v2[0] - v1[0], v2[1] - v1[1])
    ang1 = math.atan2(0, 0)
    ang2 = math.atan2(d[1], d[0])
    return (ang1 - ang2) % (2.0 * math.pi)

def convert(filename, object_name, chain_orientation):
    result = []
    projection = pyproj.Proj(proj='utm', zone=UTM_ZONE, ellps='WGS84')
    with open(filename, "r") as f:
        osm_data = json.loads(f.read())['elements']
        print("Found", len(osm_data), "nodes")
        for node in osm_data:
            easting, northing = projection(node['lon'], node['lat'])

            orientation = 0.0
            if chain_orientation:
                nearest_node = find_nearest(osm_data, node)
                en, nn = projection(nearest_node['lon'], nearest_node['lat'])
                orientation = angle((easting, northing), (en, nn))

            line = {"x" : easting, "y" : northing, "z" : 0.0, 
                    "scale" : 1.0, "orientation": orientation, 
                    "name" : object_name}
            result.append(line)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--condor-dir", 
        help="Condor 2 base directory", 
        default="C:/Program Files/Condor2/")
    parser.add_argument(
        "--bbox",
        help="Bounding box",
        default="(50.1, 11.6, 54.8,  15.25)",
        action="store")
    parser.add_argument(
        "--utm_zone", 
        help="UTM zone",
        default="33",
        action="store")
    parser.add_argument(
        "-j", "--json", 
        help="JSON object data with absolute coordinates", 
        action="store")
    args = parser.parse_args()

    query_overpass(WIND_GENERATOR_TERM, BOUNDING_BOX, "wind_osm.json")
    query_overpass(POWER_TOWER_TERM, BOUNDING_BOX, "power_osm.json")

    wobjects = convert("wind_osm.json", WIND_GENERATOR_NAME, False)
    with open("wind_objects.json", "w") as f:
        f.write(json.dumps(wobjects, sort_keys=True, indent=2))

    pobjects = convert("power_osm.json", POWER_TOWER_NAME, True)
    with open("power_objects.json", "w") as f:
        f.write(json.dumps(pobjects, sort_keys=True, indent=2))

    with open("all_objects.json", "w") as f:
        f.write(json.dumps(wobjects + pobjects, sort_keys=True, indent=2))