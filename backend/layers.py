"""Loads the fixed citywide reference layers once at server startup."""

from functools import lru_cache

import geopandas as gpd
import shapely

from backend.config import (
    INTERSECTIONS_PATH,
    TRAFFIC_ZONES_PATH,
    BUILT_UP_AREA_PATH,
    POPULATION_FIELD,
    EMPLOYMENT_FIELD,
    PROJECTED_CRS,
    WGS84_CRS,
)

# The real built-up-area layer has ~90k individual footprints - fine for the
# backend's own intersection math (spatial-indexed, see geo.built_up_pct),
# but far too many vector features for Leaflet to render in a browser tab.
# The map only ever shows this layer as background context, so a display copy
# is filtered down to the visually-significant footprints and simplified.
DISPLAY_MIN_AREA_M2 = 10_000
DISPLAY_SIMPLIFY_TOLERANCE_M = 3

# The real intersections layer has ~140k points in the Jerusalem area - same
# problem for map display. `degree` = how many road segments meet there, so
# limiting to >=4 keeps genuine crossroads/junctions and drops plain 3-way forks.
DISPLAY_MIN_DEGREE = 4


@lru_cache
def get_reference_layers():
    intersections = gpd.read_file(INTERSECTIONS_PATH).to_crs(PROJECTED_CRS)
    traffic_zones = gpd.read_file(TRAFFIC_ZONES_PATH).to_crs(PROJECTED_CRS)
    built_up_area = gpd.read_file(BUILT_UP_AREA_PATH).to_crs(PROJECTED_CRS)

    for field in (POPULATION_FIELD, EMPLOYMENT_FIELD):
        if field not in traffic_zones.columns:
            raise ValueError(
                f"Traffic zones layer is missing expected column '{field}'. "
                "Update POPULATION_FIELD/EMPLOYMENT_FIELD in backend/config.py "
                "to match the real file's column names."
            )

    return {
        "intersections": intersections,
        "traffic_zones": traffic_zones,
        "built_up_area": built_up_area,
    }


@lru_cache
def get_display_built_up_area() -> gpd.GeoDataFrame:
    """Filtered/simplified/precision-snapped WGS84 copy of the built-up layer,
    computed once and cached - for map display only. Scoring always uses the
    full-resolution layer from get_reference_layers()."""
    full = get_reference_layers()["built_up_area"]
    significant = full[full.geometry.area >= DISPLAY_MIN_AREA_M2].copy()
    significant["geometry"] = significant.geometry.simplify(
        DISPLAY_SIMPLIFY_TOLERANCE_M, preserve_topology=True
    )
    wgs = significant.to_crs(WGS84_CRS)
    # Untrimmed float precision roughly doubles the JSON payload for no
    # visual benefit on an already-simplified display layer.
    wgs["geometry"] = wgs.geometry.apply(lambda g: shapely.set_precision(g, 1e-6))
    return wgs


@lru_cache
def get_display_intersections() -> gpd.GeoDataFrame:
    """Filtered/precision-snapped WGS84 copy of the intersections layer, for
    map display only - scoring always uses the full layer from get_reference_layers()."""
    full = get_reference_layers()["intersections"]
    significant = full[full["degree"] >= DISPLAY_MIN_DEGREE][["degree", "geometry"]].copy()
    wgs = significant.to_crs(WGS84_CRS)
    wgs["geometry"] = wgs.geometry.apply(lambda g: shapely.set_precision(g, 1e-6))
    return wgs
