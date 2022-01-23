#!/usr/bin/env python3
import argparse
import json
import math
import os.path
import re
from ast import literal_eval

# pip install ...
import requests
import pyproj
import scipy.spatial

# Configuration
BOUNDING_BOX = (50.0, 11.6, 55.0, 17.0)
UTM_ZONE=33
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
        print(filename, "already exists, not querying")
        return

    r = requests.post(url=URL, data=query)

    with open(filename, "w", encoding='utf-8') as f:
        f.write(r.text)

def angle(v1, v2):
    d = (v2[0] - v1[0], v2[1] - v1[1])
    ang1 = math.atan2(0, 0)
    ang2 = math.atan2(d[1], d[0])
    return (ang1 - ang2) % (2.0 * math.pi)

def get_object_name(tags):
    if 'generator:source' in tags and tags['generator:source'] == 'wind':
        scale = 1.0
        if 'height:hub' in tags:
            height = int(re.findall(r'\d+', tags['height:hub'])[0])
            scale = height / 100.0
            # print ("scale", tags['height:hub'], scale)
        return WIND_GENERATOR_NAME, scale
    elif 'power' in tags and tags['power'] == 'tower':
        return POWER_TOWER_NAME, 1.0
    else:
        raise Exception("Unknown object type " + str(tags))

def convert(filename, utmzone, chain_orientation):
    result = []
    projection = pyproj.Proj(proj='utm', zone=utmzone, ellps='WGS84')
    with open(filename, "r", encoding='utf-8') as f:
        osm_data = json.loads(f.read())['elements']
        print("Found", len(osm_data), "nodes in", filename)

        points = []
        if chain_orientation:
            for node in osm_data:
                utm_coordinate = projection(node['lon'], node['lat'])
                points.append(utm_coordinate)
            print("Indexed", len(osm_data), "nodes in", filename)
            kdtree = scipy.spatial.KDTree(points)

        for node in osm_data:
            utm_coordinate = projection(node['lon'], node['lat'])

            orientation = 0.0
            if chain_orientation:
                distances, indices = kdtree.query(
                    utm_coordinate, 
                    k=[2, 3, 4, 5, 7, 8, 9, 10])
                while distances[0] < 100 and len(distances) > 2:
                    # Do not consider points too close, they might be from a
                    # parallel line
                    distances = distances[1:]
                    indices = indices[1:]
                orientation = angle(utm_coordinate, points[indices[0]])
                orientation2 = (
                   (angle(utm_coordinate, points[indices[1]]) + math.pi)
                      % (2.0 * math.pi))
                orientation = (orientation + orientation2) / 2
                
                # print("n", (easting, northing), distances, neighbor, orientation)

            object_name, scale = get_object_name(node['tags'])
            line = {"x" : utm_coordinate[0], 
                    "y" : utm_coordinate[1],
                    "z" : 0.0, 
                    "scale" : scale,
                    "orientation": orientation, 
                    "name" : object_name}
            result.append(line)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bbox",
        help="Bounding box",
        default=str(BOUNDING_BOX),
        action="store")
    parser.add_argument(
        "--utmzone",
        help="UTM zone",
        default=UTM_ZONE,
        action="store")
    parser.add_argument("--wind", action='store_true')
    parser.add_argument("--power", action='store_true')
    parser.add_argument(
        "-o", "--output", 
        help="JSON object data with absolute coordinates", 
        action="store")
    args = parser.parse_args()

    bounding_box = literal_eval(args.bbox)

    if args.wind:
      print(f"Querying overpass for wind with bbox: {bounding_box}")
      query_overpass(
          WIND_GENERATOR_TERM,
          bounding_box, 
          args.output + "_wind_osm.json")

    if args.power:
      print(f"Querying overpass for power with bbox: {bounding_box}")
      query_overpass(
          POWER_TOWER_TERM, 
          bounding_box, 
          args.output + "_power_osm.json")

    if args.wind:
        wobjects = convert(
            args.output + "_wind_osm.json", args.utmzone, False)
        with open(args.output + "_wind_objects.json", "w") as f:
            f.write(json.dumps(wobjects, sort_keys=True, indent=2))

    if args.power:
        pobjects = convert(
            args.output + "_power_osm.json", args.utmzone, True)
        with open(args.output + "_power_objects.json", "w") as f:
            f.write(json.dumps(pobjects, sort_keys=True, indent=2))
