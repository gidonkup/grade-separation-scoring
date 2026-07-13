"""One-off script that writes small synthetic reference layers to backend/data/
so the app is runnable before the real Jerusalem GIS layers arrive.

Run: python backend/scripts/generate_placeholder_data.py
"""

import geopandas as gpd
from shapely.geometry import Point, Polygon
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.config import (
    DATA_DIR,
    INTERSECTIONS_PATH,
    TRAFFIC_ZONES_PATH,
    BUILT_UP_AREA_PATH,
    POPULATION_FIELD,
    EMPLOYMENT_FIELD,
    WGS84_CRS,
)

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Rough center point: Jerusalem, near Jaffa Road / city center.
CENTER_LON, CENTER_LAT = 35.2137, 31.7800

# ~1 degree longitude at this latitude is ~95km, ~1 degree latitude ~111km.
# Use small offsets in degrees to scatter points within roughly 1.5km of center.
M_TO_DEG_LAT = 1 / 111_000
M_TO_DEG_LON = 1 / (111_000 * 0.85)  # cos(latitude) correction


def offset(lon, lat, dx_m, dy_m):
    return lon + dx_m * M_TO_DEG_LON, lat + dy_m * M_TO_DEG_LAT


# --- Intersections: a scattered grid of points, some dense, some sparse ---
intersection_offsets_m = [
    (-800, -800), (-600, -700), (-400, -600), (-200, -500), (0, -400),
    (-700, -300), (-500, -200), (-300, -100), (-100, 0), (100, 100),
    (300, 200), (500, 300), (700, 400), (-200, 300), (0, 500),
    (200, 700), (400, 800), (-900, 200), (900, -200), (600, -600),
]
intersection_points = [Point(*offset(CENTER_LON, CENTER_LAT, dx, dy)) for dx, dy in intersection_offsets_m]
gdf_intersections = gpd.GeoDataFrame({"id": range(len(intersection_points))}, geometry=intersection_points, crs=WGS84_CRS)
gdf_intersections.to_file(INTERSECTIONS_PATH, driver="GeoJSON")

# --- Traffic analysis zones: 4 adjacent squares (~1km each side) with population/employment ---
zone_defs = [
    # (center_dx_m, center_dy_m, half_side_m, population, employment)
    (-500, -500, 600, 5200, 1800),
    (500, -500, 600, 3100, 3600),
    (-500, 500, 600, 6800, 900),
    (500, 500, 600, 2400, 2100),
]
zone_rows = []
for dx, dy, half, pop, emp in zone_defs:
    corners_m = [(-half, -half), (half, -half), (half, half), (-half, half)]
    ring = [offset(CENTER_LON, CENTER_LAT, dx + cx, dy + cy) for cx, cy in corners_m]
    zone_rows.append({POPULATION_FIELD: pop, EMPLOYMENT_FIELD: emp, "geometry": Polygon(ring)})
gdf_zones = gpd.GeoDataFrame(zone_rows, crs=WGS84_CRS)
gdf_zones.to_file(TRAFFIC_ZONES_PATH, driver="GeoJSON")

# --- Built-up area: irregular blobs covering part of the zones (not everything) ---
builtup_defs = [
    (-700, -600, 250), (-450, -450, 220), (-250, -250, 200),
    (400, -450, 260), (650, -650, 230),
    (-650, 450, 240), (-400, 650, 210),
    (450, 400, 200),
]
builtup_rows = []
for dx, dy, r in builtup_defs:
    ring_m = [(dx + r * __import__("math").cos(a), dy + r * __import__("math").sin(a))
              for a in [i * 2 * 3.14159265 / 8 for i in range(8)]]
    ring = [offset(CENTER_LON, CENTER_LAT, cx, cy) for cx, cy in ring_m]
    builtup_rows.append({"geometry": Polygon(ring)})
gdf_builtup = gpd.GeoDataFrame(builtup_rows, crs=WGS84_CRS)
gdf_builtup.to_file(BUILT_UP_AREA_PATH, driver="GeoJSON")

print(f"Wrote {len(gdf_intersections)} intersections -> {INTERSECTIONS_PATH}")
print(f"Wrote {len(gdf_zones)} traffic zones -> {TRAFFIC_ZONES_PATH}")
print(f"Wrote {len(gdf_builtup)} built-up polygons -> {BUILT_UP_AREA_PATH}")
