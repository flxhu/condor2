#!/usr/bin/env python3
import os, os.path, subprocess, shlex, sys, json, shutil
import argparse

##### CONFIGURATION - Adapt Me ######

OSGEO4W_ROOT = "C:\\Program Files\\QGIS 2.18\\"
NVDXT_PATH = "D:\\Condor 2 Own Landscape\\CondorLandscapeToolkit\\nvdxt.exe"
CONDOR_DIR = "C:\\Program Files\\Condor2\\Landscapes\\"
TARGET_KBS = 32633

#####################################

# Derived directories, don't touch
GDAL_BIN = os.path.join(OSGEO4W_ROOT, "bin")
GDAL_DATA = os.path.join(OSGEO4W_ROOT, "share", "gdal")
GDAL_BUILD_VRT = "'" + os.path.join(GDAL_BIN, "gdalbuildvrt") + "'" 

# Constants, changing them is untested
TERRAIN_TILE_SIZE_PIXELS = 8192
FOREST_TILE_SIZE_PIXELS = 2048
TILE_SIZE_UTM = 23040.0

THERMAL_MAP_TILE_SIZE = 256
TERRAIN_SAMPLING = "near"  # we want it crisp
WGS_84_KBS = "EPSG:4326"

def load_config(config_file_name):
    with open(config_file_name, "r") as myfile:
        config_json = myfile.read()
    return json.loads(config_json)

def initialize_directories(config):
    map_name = config['name']
    output_directory = os.path.join(CONDOR_DIR, f"{map_name}")

    tmp_directory = os.path.join(f"{map_name}/", "tmp/")

    textures_dds_directory = os.path.join(output_directory, "Textures/")
    trn_out_directory = os.path.join(output_directory, "HeightMaps/")
    editor_terrain_directory = os.path.join(output_directory, "Working/", "Terragen/", "Textures/")
    forest_directory = os.path.join(output_directory, "Working/", "Terragen/", "ForestMaps/")

    os.makedirs(output_directory, exist_ok=True)
    os.makedirs(tmp_directory, exist_ok=True)
    os.makedirs(textures_dds_directory, exist_ok=True)
    os.makedirs(editor_terrain_directory, exist_ok=True)
    os.makedirs(forest_directory, exist_ok=True)
    os.makedirs(trn_out_directory, exist_ok=True)

def get_files_from_directory(directory, extension):
  files = os.listdir(directory)
  all = []
  for fname in files:
      if extension in fname:
          all.append(os.path.join(directory, fname))
  return all

def render_osm(config):
    area_utm = tuple(config['area_utm'])
    area_wgs84 = tuple(config['area_outer_wgs84'])
    target_kbs = config['target_kbs']
    map_name = config['name']
    tmp_directory = os.path.join(f"{map_name}/", "tmp/")
    output_directory = os.path.join(CONDOR_DIR, f"{map_name}")
    working_directory = os.path.join(output_directory, "Working/")
    editor_terrain_directory = os.path.join(output_directory, "Working/", "Terragen/", "Textures/")
    forest_directory = os.path.join(output_directory, "Working/", "Terragen/", "ForestMaps/")
    osm_directory = config['osm_directory']
    regions = config['osm_regions']

    # Process OSM to .tif
    osm_process(area_utm, target_kbs, area_wgs84, osm_directory, regions)

    # Cut tiles
    cut_to_tiles("s", area_utm, f"{osm_directory}/forest-evergreen_esg4326.tif.ers",
                 tmp_directory, forest_directory, FOREST_TILE_SIZE_PIXELS)
    cut_to_tiles("b", area_utm, f"{osm_directory}/forest-other_esg4326.tif.ers",
                 tmp_directory, forest_directory, FOREST_TILE_SIZE_PIXELS)
    cut_to_tiles("a", area_utm, f"{osm_directory}/water_inverted_esg4326.tif.ers",
                  tmp_directory, editor_terrain_directory, TERRAIN_TILE_SIZE_PIXELS)

    shutil.copy(os.path.join(osm_directory, "ThermalMap.bmp"), working_directory)
    print("ThermalMap.bmp written to", working_directory, ". Export via File>Export Thermap Map")

def osm_process(area_utm, target_kbs, area_wgs84, osm_directory, sources):
    width_m = area_utm[2] - area_utm[0]
    width_pixels = width_m * TERRAIN_TILE_SIZE_PIXELS / TILE_SIZE_UTM
    height_m = area_utm[1] - area_utm[3]
    height_pixels = height_m * TERRAIN_TILE_SIZE_PIXELS / TILE_SIZE_UTM

    no_tiles_x, no_tiles_y = get_tile_count(area_utm)
    forest_factor = float(FOREST_TILE_SIZE_PIXELS) / float(TERRAIN_TILE_SIZE_PIXELS)
    thermal_factor = forest_factor
    print(sources)
    features = [("forest-evergreen", "landuse=forest and leaf_type=needleleaved", 64, False, forest_factor),
                ("forest-other", "landuse=forest and leaf_type!=needleleaved", 100, False, forest_factor),
                ("water","natural=water or waterway=riverbank or natural=bay or place=bay or natural=strait or natural=coastline", 10, True, 1.0),
                ("farmland", "landuse=farmland or landuse=meadow", 178, False, thermal_factor),
                ("cities", "landuse=residential or landuse=industrial or landuse=commercial", 150, False, thermal_factor)]
    for source in sources:
        print("Converting and filtering region", source)
        prefix = os.path.join(osm_directory, source)
        if not os.path.exists(f"{prefix}-latest.osm"):
          os.system(f'osmconvert64 {prefix}-latest.osm.pbf -o={prefix}-latest.osm')

        for feature, query, burn, inverted, factor_unused in features:
            print(".. filtering", feature)
            if not os.path.exists(f"{prefix}-{feature}.osm"):
              os.system(f'osmfilter {prefix}-latest.osm --keep="{query}" -o={prefix}-{feature}.osm')

    for feature, query, burn, inverted, factor in features:      
      print("Merging and rendering", feature, "with resolution factor", factor)
      if not os.path.exists(f"{osm_directory}/all-{feature}.osm.bpf"):
        os.system(f'osmconvert64 {osm_directory}/*-{feature}.osm -o={osm_directory}/all-{feature}.osm.bpf')

      run(f"{osm_directory}/{feature}.tif",
          "gdal_rasterize",
          f' -l multipolygons -ot Byte -burn {burn} -burn {burn} -burn {burn} -of gtiff' +
          f' -te {area_wgs84[0]} {area_wgs84[1]} {area_wgs84[2]} {area_wgs84[3]} ' + 
          f' -ts {factor * width_pixels} {factor * height_pixels} {osm_directory}/all-{feature}.osm.bpf {osm_directory}/{feature}.tif')
      
      gdal_reproject(f"{osm_directory}/{feature}_esg4326.tif", f"{osm_directory}/{feature}.tif", WGS_84_KBS, target_kbs, "")

      if inverted:
        run(f"{osm_directory}/{feature}_inverted.tif",
            "gdal_translate",
            f'  -ot Byte -b 1 -scale 0 {burn} 255 0 -of gtiff {osm_directory}/{feature}.tif {osm_directory}/{feature}_inverted.tif')
        gdal_reproject(f"{osm_directory}/{feature}_inverted_esg4326.tif", f"{osm_directory}/{feature}_inverted.tif", WGS_84_KBS, target_kbs, "")

    print("Rendering thermal map")
    run(os.path.join(osm_directory, "thermal.tif"),
        "gdalwarp",
        " -srcnodata 0 -multi " + 
        " ".join([f"{osm_directory}/{feature}_esg4326.tif.ers" 
                  for feature, query, burn, inverted, factor in features if not inverted]) +
        f" {osm_directory}/thermal.tif")
    run(os.path.join(osm_directory, "ThermalMap.bmp"),
        "gdal_translate",
        f" -epo -projwin {area_utm[0]} {area_utm[1]} {area_utm[2]} {area_utm[3]} -outsize {no_tiles_x*THERMAL_MAP_TILE_SIZE} {no_tiles_y*THERMAL_MAP_TILE_SIZE} -of BMP {osm_directory}/thermal.tif '{osm_directory}/ThermalMap.bmp'")

def get_tile_count(area_utm):
    width_m = area_utm[2] - area_utm[0]
    height_m = area_utm[1] - area_utm[3]
    return int(width_m / TILE_SIZE_UTM), int(height_m / TILE_SIZE_UTM)

def check_area(area_utm):
    print("UTM coordinates:", area_utm)
    width_m = area_utm[2] - area_utm[0]
    height_m = area_utm[1] - area_utm[3]
    if height_m < 0 or width_m < 0:
        print("Swap coordinates")
    print("Size (km): ", width_m / 1000, "x", height_m / 1000)
    print("Size (tiles)", width_m / TILE_SIZE_UTM, "x", height_m / TILE_SIZE_UTM,
          "ok?", width_m % TILE_SIZE_UTM == 0, height_m % TILE_SIZE_UTM == 0)
    no_tiles_x, no_tiles_y = get_tile_count(area_utm)
    print()
    print("Terrain texture suggested resolution:",
          no_tiles_x * TERRAIN_TILE_SIZE_PIXELS, "x", no_tiles_y * TERRAIN_TILE_SIZE_PIXELS)
    print()
    print("Forest texture suggested resolution:",
          no_tiles_x * FOREST_TILE_SIZE_PIXELS, "x", no_tiles_y * FOREST_TILE_SIZE_PIXELS)
    print()
    return no_tiles_x, no_tiles_y

def get_geotiff_metadata(filename):
    if subprocess.call([os.path.join(GDAL_BIN, 'gdalinfo'), filename], env = {'GDAL_DATA' : GDAL_DATA}) != 0:
        print("<<< Failed, exit")
        sys.exit(10)

def run(output, command, args):
  return run_binary(os.path.join(GDAL_BIN, command), output, args, ".")

def nvdxt(output, cwd, args):
  return run_binary(NVDXT_PATH, output, args, cwd)

def run_binary(binary, output, args, workingdir):
  if not os.path.exists(output):
    line = [binary] + shlex.split(args)
    print(f">>> Generating {output} with {line}")
    if subprocess.call(line, env = {'GDAL_DATA' : GDAL_DATA, 'OSGEO4W_ROOT' : OSGEO4W_ROOT, 'SystemRoot': 'C:\\Windows'}, cwd=workingdir) != 0:
        print("<<< Failed, exit")
        sys.exit(10)
    print(f"<<< Done {output}")
  else:
    print(f"  skipping as {output} already exists")

def gdal_reproject(destination, source, source_kbs, target_kbs, resampling):
    run(destination,
        "gdalwarp",
        f"-s_srs {source_kbs} -t_srs {target_kbs} {resampling} -multi -of ERS {source} {destination}")

# Create projected and clipped geotiff
def terrain_reproject_and_clip(
      what, area_utm, geotiff_input, output_prefix, 
      tmp_dir, terrain_source_kbs, terrain_target_kbs,
      terrain_sampling, tile_size_pixels):
    tmp_prefix = os.path.join(tmp_dir, what)

    run(f"{tmp_prefix}_raster.vrt",
        "gdalbuildvrt",
        f"{tmp_prefix}_raster.vrt {geotiff_input}")

    gdal_reproject(
        f"{tmp_prefix}_raster_reproject_{terrain_sampling}.vrt",
        f"{tmp_prefix}_raster.vrt", terrain_source_kbs, terrain_target_kbs,
        f"-r {terrain_sampling}")

# Sasplanet: cache area. Stitch 4326 (WGS-84)
# LGB Geobroker: 25833 (UTMxy)
def render_textures(config):
    area_utm = tuple(config['area_utm'])
    map_name = config['name']
    terrain_geotiff_input = config['terrain_raw']

    output_directory = os.path.join(CONDOR_DIR, f"{map_name}")
    tmp_directory = os.path.join(f"{map_name}/", "tmp/")
    prefix = map_name
    output_prefix = os.path.join(output_directory, prefix)
    editor_terrain_directory = os.path.join(output_directory, "Working/", "Terragen/", "Textures/")

    get_geotiff_metadata(config['terrain_raw'])

    print("Converting", terrain_geotiff_input, 
          "into tiles in", editor_terrain_directory)

    terrain_reproject_and_clip(
        "terrain", area_utm, terrain_geotiff_input,
        output_prefix, tmp_directory,
        config['terrain_kbs'], config['target_kbs'],
        TERRAIN_SAMPLING, TERRAIN_TILE_SIZE_PIXELS)
    cut_to_tiles(
        "", area_utm, os.path.join(tmp_directory, 
        f"terrain_raster_reproject_{TERRAIN_SAMPLING}.vrt.ers"),
         tmp_directory, editor_terrain_directory, 
         TERRAIN_TILE_SIZE_PIXELS)

    print("Conversion done. Now run WaterAlpha (after the osm step) and run nvdxt on the result. Copy to Terrain directory.")

def cut_to_tiles(
      tile_prefix, area_utm, input_file, tmp_directory, 
      editor_terrain_directory, tile_size_pixels):
    tile_tmp = os.path.join(tmp_directory, "tiles")
    os.makedirs(tile_tmp, exist_ok=True)
    width_tiles, height_tiles = get_tile_count(area_utm)

    utm_height = area_utm[1] - area_utm[3]
    utm_width = area_utm[2] - area_utm[0]
    print("Width (utm):", utm_width, "Height:", utm_height)

    utm_tile_height = utm_height / height_tiles
    utm_tile_width = utm_width / width_tiles
    print("Tile Width (utm):", utm_tile_width, "Height:", utm_tile_height)
    assert TILE_SIZE_UTM == utm_tile_height
    assert TILE_SIZE_UTM == utm_tile_width

    for x in range(width_tiles):
        for y in range(height_tiles):
            start_x = (width_tiles - x - 1) * tile_size_pixels
            start_y = (height_tiles - y - 1) * tile_size_pixels
            tile_name = "{:02d}{:02d}".format(x, y)

            ulx = (width_tiles - x - 1) * utm_tile_width + area_utm[0]
            uly = area_utm[1] - (height_tiles - y - 1) * utm_tile_height 
            lrx = ulx + utm_tile_width
            lry = uly - utm_tile_height

            print(f"Generating tile {tile_prefix}{tile_name}.bmp at ({start_x}, {start_y}) size {tile_size_pixels}x{tile_size_pixels}")

            run(f'{editor_terrain_directory}/{tile_prefix}{tile_name}.bmp',
                "gdal_translate",
                f" -epo -projwin {ulx} {uly} {lrx} {lry} -outsize {tile_size_pixels} {tile_size_pixels} -of BMP {input_file} '{editor_terrain_directory}/{tile_prefix}{tile_name}.bmp'")


def convert_tiles_to_dds(textures_directory):
    subprocess.call(
        ["nvDXT.exe"] +
            shlex.split("-quality_highest -nmips 5 -all -outdir dds -dxt1c -Triangle"), 
        cwd=textures_directory)

def process_heightmap(config):
    map_name = config['name']
    tmp_directory = os.path.join(f"{map_name}/", "tmp/")
    dem_create(config['name'], config['dem_directory'], 
    tmp_directory, config['area_utm'], config['target_kbs'])

# https://earthexplorer.usgs.gov/
# Load output in RAW TO TRN, 30m, flip vertical WIDTH = NCOLS, save to Brandenburg.trn target root folder
def dem_create(output_directory, dem_directory, tmp_dir, area_utm, target_kbs):
  print("Converting. bil files from https://earthexplorer.usgs.gov/ in",
        dem_directory, "to a .raw file for RawToTrn.exe")
  all_bils = get_files_from_directory(dem_directory, ".bil")
  if not all_bils:
      raise "No .bil files in " + dem_directory

  run(f"{tmp_dir}/dem_merged.bil",
      "gdal_merge.bat",
      f"-of EHdr -o {tmp_dir}dem_merged.bil " + " ".join(all_bils))
 
  run(f"{tmp_dir}/dem_merged_wgs84.bil",
      "gdalwarp",
      f" -overwrite -t_srs {target_kbs} -r cubicspline -of EHdr -tr 30 30 {tmp_dir}/dem_merged.bil {tmp_dir}/dem_merged_wgs84.bil")
  
  run(f"{tmp_dir}/dem_merged_wgs84_clipped.bil",
      "gdal_translate",
      f" -projwin {area_utm[0]} {area_utm[1]} {area_utm[2]} {area_utm[3]} -of EHdr -tr 30 30 {tmp_dir}/dem_merged_wgs84.bil {tmp_dir}/dem_merged_wgs84_clipped.bil")

  heightmap_raw = os.path.join(output_directory, "heightmap.raw")
  shutil.copy(f"{tmp_dir}dem_merged_wgs84_clipped.bil", heightmap_raw)
  heightmap_txt = os.path.join(output_directory, "heightmap.txt")
  shutil.copy(f"{tmp_dir}dem_merged_wgs84_clipped.hdr", heightmap_txt)
  print("Output written to ", heightmap_raw, "and", heightmap_raw)
  condor_landscape_dir = os.path.join(CONDOR_DIR, output_directory)
  print(f"Now load the {heightmap_raw} file with RawToTrn.exe (30m, flip vertical, Width = NCOLS, Height = NROWS,  from {heightmap_txt} file).")
  print(f"Then Save the resulting .trn to {condor_landscape_dir}/mapename.trn and load your new landscape in the LandscapeEditor")
  print("Make sure that your user has full permissions on the {condor_landscape_dir}, otherwise files end up in the VirtualStore.")
  print("Manually edit heights, and run File>Export TRN to TR3 and File>Export Terrain Hash")

# Unused
def terrain_prepare_overlay(overlay_dir, tmp_dir, target_kbs):
  tmp_prefix = os.path.join(tmp_dir, "overlay")
  files = get_files_from_directory(overlay_dir, ".jpg")
  run(f"{tmp_prefix}_raster.vrt",
      "gdalbuildvrt",
      f"{tmp_prefix}_raster.vrt {files}")

  gdal_reproject(
      f"{tmp_prefix}_raster_reproject.vrt", f"{tmp_prefix}_raster.vrt",
      "EPSG:25833", "-r cubicspline", target_kbs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", 
        choices=["check", "textures", "osm", "heightmap"])
    parser.add_argument(
        "-c", "--config", 
        help="Landscape configuration file (JSON)", 
        action="store")
    args = parser.parse_args()

    print("Using landscape configuration", args.config)
    config = load_config(args.config)
    print(config)

    check_area(tuple(config['area_utm']))

    print("Initializing directories")
    initialize_directories(config)

    if args.command == 'textures':
        render_textures(config)
    elif args.command == 'osm':
        render_osm(config)
    elif args.command == 'heightmap':
        process_heightmap(config)