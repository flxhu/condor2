# Condor 2 Landscape Creation Tools
Tools for building landscapes for the Condor 2 flight simulator

## create_landscape.py
 
Condor 2 landscapes consist of several artefacts and can be very time-intensive
to build manually. 
 
'create_landscape.py` automates some of the process and is able to generate:
1. the terrain (height map) from USGS EarthExplorer .bil files
2. texture tiles and the overview map from a GeoTIFF
3. forests, water and the thermal map 

What you're left to do is placing airports and objects, maybe fixing up some
tiles.

Prerequisites:
* Windows (Linux et al. likely work to, but untested)
* A QGIS installation (https://www.qgis.org/de/site/forusers/download.html)
* Python 3
* At least a couple of 100G of SSD space
* Patience: some of the rendering steps can take days for large areas

First adapt `create_landscape.py` to your installation (QGIS directory etc).

The rough workflow with the tool (please refer to the Landscape Guide for 
details):
1. decide on an approximate area of coverage (in WGS-84 coordinates, 
   should a bit larger than the final landscape) and exact UTM coordinates
   (UTMTools.exe) and put them into the `config.json`. I've included the
   `config.json` of the EastGermany map as an example.
2. Terrain 
  - download DEM data from USGS EarthExplorer
  - convert terrain data with `create_landscape.py -c config.json heightmap`
  - create the initial landscape from the data
3. Textures
  - download textures and stitch them to a large GeoTIFF. In some countries 
    you can get DOPs (resolution 1m or better) from the local administration,
    or you can rip data from mapping services with sasplanet (z17, EPSG 3785). 
    Add path and kbs to `config.json`.
  - generate textures tiles with `create_landscape.py -c config.json textures`
4. Forests, Water, Thermal
  - download OpenStreetMap data for your coverage (.osm files), for example
    from https://download.geofabrik.de/, add to `config.json`.
  - generate forests and water tiles and the thermal map with
    `create_landscape.py -c config.json osm`

Import forests with the Landscape Editor. Run WaterAlpha on the generated 
texture and water tiles.

## condor_obj_file_tool.py for processing Condor 2 .obj files
condor_obj_file_tool.py converts Condor's .obj files, which contains the
coordinates, dimension and orientation of objects in the landscape. 

It can also help translate objects from one landscape's coordinate system to 
an other's. While Condor's .obj files contain relatives coordinates, the tool
writes absolute coordinates to the JSON file.

The JSON output can be used to diff and patch updates from concurrent edits.

Typical workflow

`condor_obj_file_tool.py export --name <landscapefrom> --json objects.json`

`condor_obj_file_tool.py import --name <landscapeto> --json objects.json`
 
Based on the work of Bre901, see http://www.condorsoaring.com/forums/viewtopic.php?f=38&t=18521&p=165412

## osm_to_objects.py for generating landscape objects from OSM data
osm_to_objects.py queries OSM for power tower and wind generator data and
creates a .json file with their positions, which can be imported into a 
landscape's .obj with condor_obj_file_tool.py