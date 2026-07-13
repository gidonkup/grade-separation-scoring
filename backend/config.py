"""Default settings and reference-layer field mapping.

Every threshold here is meant to be overridden at request time via the
Settings payload sent from the frontend - these are just the defaults.
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

INTERSECTIONS_PATH = DATA_DIR / "intersections.geojson"
TRAFFIC_ZONES_PATH = DATA_DIR / "traffic_zones.geojson"
BUILT_UP_AREA_PATH = DATA_DIR / "built_up_area.geojson"

# Column names in the traffic-zones layer, as written by build_reference_data.py
# (renamed from the source JTMT TAZ forecast's 2020 base-year columns -
# pop_without_dorms_yeshiva / total_emp - for readability; the source Excel
# also has _2025/_2030/.../_2050 suffixed variants for later years, not wired up yet).
POPULATION_FIELD = "population_2020"
EMPLOYMENT_FIELD = "employment_2020"

DEFAULT_SETTINGS = {
    "env_buffer_radius_m": 1000,
    "intersection_density_threshold_per_km2": 8,
    "population_density_threshold_per_km2": 1500,
    "employment_density_threshold_per_km2": 700,
    "active_edge_buffer_m": 1000,
    "active_edge_builtup_pct_threshold": 30,
    "crossing_spacing_threshold_m": 150,
    "walking_path_length_gap_pct_threshold": 20,
}

# Layers are authored in WGS84 (lon/lat) by the frontend; all area/length
# math is done in this projected CRS (Israel TM Grid, meters).
PROJECTED_CRS = "EPSG:2039"
WGS84_CRS = "EPSG:4326"
