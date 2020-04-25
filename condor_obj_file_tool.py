#!/usr/bin/env python3

import argparse
import os.path
import struct
import json

def read_trn(trn_file):
    with open(trn_file, "rb") as f:
        f.seek(20)
        lon, lat = struct.unpack('ff', f.read(8))
        print(trn_file, "Lon:", lon, "Lat:", lat)
        return lon, lat

def read_obj(obj_file, lon, lat):
    result = []
    with open(obj_file, "rb") as f:
        while True:
            buffer = f.read(4*5)
            if not buffer:
                break
            posx, posy, posz, dim, ori = struct.unpack('fffff', buffer)
            lnam = ord(struct.unpack('c', f.read(1))[0])

            buff = f.read(131)
            name = buff[0:lnam]
            line = {"x" : lon - posx, "y" : lat + posy, "z" : posz, 
                           "scale" : dim, "orientation": ori, 
                           "name" : name.decode("ascii")}
            print(line, posx, posy)
            result.append(line)
    return result

def write_obj(obj_file, lon, lat, objects):
    print("Writing", obj_file)
    with open(obj_file, "wb") as f:
        for o in objects:
            print(lon - o['x'],  o['y'] - lat)
            outdata = struct.pack(
                'fffffB',
                lon - o['x'],  o['y'] - lat, o['z'], o['scale'], o['orientation'], 
                len(o['name']))
            f.write(outdata)
            f.write(o['name'].encode("ascii"))
            f.write(b'\0' * (131 - len(o['name'])))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", 
        choices=["export", "import", "view"])
    parser.add_argument(
        "--condor-dir", 
        help="Condor 2 base directory", 
        default="C:/Program Files/Condor2/")
    parser.add_argument(
        "--name", 
        help="Landscape name", 
        action="store")
    parser.add_argument(
        "-j", "--json", 
        help="JSON object data with absolute coordinates", 
        action="store")
    args = parser.parse_args()

    if not os.path.exists(args.condor_dir):
        print("Condor directory not found at", args.condor_dir,
              ", please specify with --condor-dir")

    landscape_dir = os.path.join(
        args.condor_dir, "Landscapes/", args.name + "/")
    trn_file = os.path.join(landscape_dir, args.name + ".trn")
    obj_file = os.path.join(landscape_dir, args.name + ".obj")
    obj_out_file = os.path.join(landscape_dir, args.name + ".obj")

    print("Landscape directory", landscape_dir,
          ". Make sure it is writable by your user, otherwise data may end up in the VirtualStore.")
        
    lon, lat = read_trn(trn_file)
    if args.command == "export":
        objects = read_obj(obj_file, lon, lat)
        print("Read", len(objects), "objects")
        if args.json:
            print("writing to", args.json)
            with open(args.json, "w") as f:
                f.write(json.dumps(objects, sort_keys=True, indent=2))
    elif args.command == "import":
       with open(args.output, "r") as f:
           objects = json.loads(f.read())
           print("Read", len(objects), "objects from", args.json)
           write_obj(obj_out_file, lon, lat, objects)
