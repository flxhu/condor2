#!/usr/bin/env python3

import os, os.path, re

CONDOR_DIR = "C:\\Program Files\\Condor2\\Landscapes\\"
SOURCE_LANDSCAPE = "EastGermany"
TARGET_LANDSCAPE = "EastGermanyExt"

PATHS=[
   # ("HeightMaps", 56, 0),
    ("ForestMaps", 16, 0),
   # ("Textures", 16, 0)
      ]

def getMaxXY(dir):
    files = os.listdir(dir)
    files.sort(reverse=True)
    name = files[0]
    match = re.match(r"([a-z]?)(\d{2})(\d{2})([.a-z0-9]*)", files[0])
    return int(match[2]), int(match[3]), match[1], match[4]

for p, shift_x, shift_y in PATHS:
    source_data_dir = os.path.join(CONDOR_DIR, SOURCE_LANDSCAPE, p)
    max_x, max_y, prefix, ext = getMaxXY(source_data_dir)
    print(p, max_y, max_x, prefix, ext)

    for y in range(max_y + 1):
        for x in range(max_x + 1):
            source_file = os.path.join(source_data_dir)

            target_x = x + shift_x
            target_y = y + shift_y
            
            source_file = f"{prefix}{x:02}{y:02}{ext}"
            target_file = f"{prefix}{target_x:02}{target_y:02}{ext}"
            source_path = os.path.join(CONDOR_DIR, SOURCE_LANDSCAPE, p, source_file)
            target_path = os.path.join(CONDOR_DIR, TARGET_LANDSCAPE, p, target_file)
            assert os.path.exists(source_path), source_path
            assert not os.path.exists(target_path), target_path
            print(f"From {source_path} to {target_path}")
            os.link(source_path, target_path)