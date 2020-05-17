#!/usr/bin/env python3

import argparse
import os.path
import struct
import json

def read_trn(trn_file):
    print("Parsing", trn_file)
    with open(trn_file, "rb") as f:
        width, height = struct.unpack('ii', f.read(8))
        struct.unpack('fff', f.read(12))  # 12, 3 * 90 Grad floats
        easting, northing = struct.unpack('ff', f.read(8))

        utm_zone, null = struct.unpack('HH', f.read(4))  # 33
        utm_zone_ns, null = struct.unpack('HH', f.read(4))  # 78 = 'N'

        easting_lu = easting - width / 256 * 23090
        northing_lu = northing + height / 256 * 23090

        assert f.tell() == 36

        # 256 x 256 shorts per tile
        # print(struct.unpack('H', f.read(2)))

        print("Bottom right (origin) northing", northing, "easting", easting, "zone", utm_zone)
        print("Upper left northing", northing_lu, "easting", easting_lu, "zone")
        print("Width:", width / 256, "tiles, Height:", height / 256, "tiles")

        return easting, northing, utm_zone, easting_lu, northing_lu

def read_obj(obj_file, easting, northing):
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
            line = {"x" : easting - posx, "y" : northing + posy, "z" : posz, 
                    "scale" : dim, "orientation": ori, 
                    "name" : name.decode("ascii")}
            print(line, posx, posy)
            result.append(line)
    return result

def write_obj(obj_file, easting, northing, objects):
    print("Writing", obj_file)
    with open(obj_file, "wb") as f:
        for o in objects:
            outdata = struct.pack(
                'fffffB',
                easting - o['x'],  o['y'] - northing, o['z'], o['scale'], o['orientation'], 
                len(o['name']))
            f.write(outdata)
            f.write(o['name'].encode("ascii"))
            f.write(b'\0' * (131 - len(o['name'])))

def clip(objects, e_rb, n_rb, e_lu, n_lu):
    result = []
    for object in objects:
        x = object['x']
        y = object['y']
        if x < e_rb and x > e_lu and y < n_lu and y > n_rb:
           result.append(object)
    return result

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
    parser.add_argument(
        "--noclip",
        help="Do not filter out objects outside of landscape bounds when importing", 
        action="store_true")
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
        
    easting, northing, utm_zone, easting_lu, northing_lu = read_trn(trn_file)
    if args.command == "export":
        objects = read_obj(obj_file, easting, northing)
        print("Read", len(objects), "objects")
        if args.json:
            print("Writing to", args.json)
            with open(args.json, "w") as f:
                f.write(json.dumps(objects, sort_keys=True, indent=2))

    elif args.command == "import":
       with open(args.json, "r") as f:
           objects = json.loads(f.read())
           print("Read", len(objects), "objects from", args.json)
           object_count = len(objects)
           if not args.noclip:
               objects = clip(objects, easting, northing, easting_lu, northing_lu)
               print("Clipping dropped", object_count - len(objects), "objects")
           write_obj(obj_out_file, easting, northing, objects)
