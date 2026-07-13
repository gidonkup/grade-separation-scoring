"""Builds backend/data/*.geojson from the real source files in data_sources/raw/
(see data_sources/README.md for what each one is):

  - data_sources/raw/traffic_zones/traffic_zones.shp     traffic-analysis-zone geometries
  - data_sources/raw/population_employment_forecast_2020_2050.xlsx   forecast by Taz_num
  - data_sources/raw/built_up_area/built_up_area.shp     countrywide built-up area (one multipolygon)
  - data_sources/raw/junctions_layer/junctions.shp       countrywide road-network junctions

Output field names are renamed from the source's cryptic originals for
readability: Taz_num -> zone_id, Taz_name -> zone_name,
pop_without_dorms_yeshiva -> population_2020, total_emp -> employment_2020.

Run: python backend/scripts/build_reference_data.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.config import (
    DATA_DIR,
    TRAFFIC_ZONES_PATH,
    BUILT_UP_AREA_PATH,
    INTERSECTIONS_PATH,
    POPULATION_FIELD,
    EMPLOYMENT_FIELD,
    WGS84_CRS,
    PROJECTED_CRS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data_sources" / "raw"
TAZ_SHP = RAW_DIR / "traffic_zones" / "traffic_zones.shp"
FORECAST_XLSX = RAW_DIR / "population_employment_forecast_2020_2050.xlsx"
BUILT_UP_SHP = RAW_DIR / "built_up_area" / "built_up_area.shp"
JUNCTIONS_SHP = RAW_DIR / "junctions_layer" / "junctions.shp"

# How far past the TAZ layer's extent to keep built-up geometry - project
# buffers (default 1-2km) need built-up area a bit outside the TAZ boundary too.
CLIP_MARGIN_M = 3000

DATA_DIR.mkdir(parents=True, exist_ok=True)


def build_traffic_zones():
    taz = gpd.read_file(TAZ_SHP)
    forecast = pd.read_excel(FORECAST_XLSX)

    # Taz_num is float64 in the shapefile, int64 in the Excel - align before merging.
    taz["Taz_num"] = taz["Taz_num"].astype("int64")

    merged = taz.merge(
        forecast[["Taz_num", "pop_without_dorms_yeshiva", "total_emp"]],
        on="Taz_num",
        how="left",
    )
    merged = merged.rename(
        columns={
            "Taz_num": "zone_id",
            "Taz_name": "zone_name",
            "pop_without_dorms_yeshiva": POPULATION_FIELD,
            "total_emp": EMPLOYMENT_FIELD,
        }
    )
    unmatched = merged[POPULATION_FIELD].isna().sum()
    if unmatched:
        print(f"WARNING: {unmatched} TAZ zones had no matching forecast row (left as NaN).")

    out = merged[["zone_id", "zone_name", POPULATION_FIELD, EMPLOYMENT_FIELD, "geometry"]]
    out = out.to_crs(WGS84_CRS)
    out.to_file(TRAFFIC_ZONES_PATH, driver="GeoJSON")
    print(f"Wrote {len(out)} traffic zones -> {TRAFFIC_ZONES_PATH}")
    return taz.to_crs(WGS84_CRS).total_bounds, merged


def build_built_up_area(taz_bounds_wgs84):
    bld = gpd.read_file(BUILT_UP_SHP)

    # This source file is one single (huge, invalid) countrywide MultiPolygon.
    # Fixing validity on the whole thing before narrowing to Jerusalem is what
    # makes this slow (10+ minutes) - explode to single parts first (cheap,
    # no geometry repair needed for that), bbox-filter down to the relevant
    # area (also cheap, uses the parts' precomputed bounds), and only then
    # run make_valid on the much smaller remaining subset.
    exploded = bld.explode(index_parts=False).reset_index(drop=True)

    taz_bounds_proj_box = (
        gpd.GeoSeries([box(*taz_bounds_wgs84)], crs=WGS84_CRS).to_crs(bld.crs).iloc[0]
    )
    minx, miny, maxx, maxy = taz_bounds_proj_box.bounds
    clip_box = box(minx - CLIP_MARGIN_M, miny - CLIP_MARGIN_M, maxx + CLIP_MARGIN_M, maxy + CLIP_MARGIN_M)

    filtered = exploded[exploded.geometry.intersects(clip_box)].reset_index(drop=True)
    filtered["geometry"] = filtered.geometry.apply(make_valid)

    out = filtered[["geometry"]].to_crs(WGS84_CRS)
    out.to_file(BUILT_UP_AREA_PATH, driver="GeoJSON")
    print(f"Wrote {len(out)} built-up polygons -> {BUILT_UP_AREA_PATH}")


def build_intersections(taz_bounds_wgs84):
    # Countrywide, already WGS84, all rows have degree >= 3 (i.e. already
    # real junctions, not just arbitrary points along a road).
    junctions = gpd.read_file(JUNCTIONS_SHP).to_crs(PROJECTED_CRS)

    taz_bounds_proj_box = gpd.GeoSeries([box(*taz_bounds_wgs84)], crs=WGS84_CRS).to_crs(PROJECTED_CRS).iloc[0]
    minx, miny, maxx, maxy = taz_bounds_proj_box.bounds
    clip_box = box(minx - CLIP_MARGIN_M, miny - CLIP_MARGIN_M, maxx + CLIP_MARGIN_M, maxy + CLIP_MARGIN_M)

    filtered = junctions[junctions.geometry.intersects(clip_box)].reset_index(drop=True)
    out = filtered[["degree", "fclasses", "names", "geometry"]].to_crs(WGS84_CRS)
    out.to_file(INTERSECTIONS_PATH, driver="GeoJSON")
    print(f"Wrote {len(out)} intersections -> {INTERSECTIONS_PATH}")


if __name__ == "__main__":
    taz_bounds_wgs84, _ = build_traffic_zones()
    build_built_up_area(taz_bounds_wgs84)
    build_intersections(taz_bounds_wgs84)
