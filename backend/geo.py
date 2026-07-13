"""Generic GIS helpers shared by the environment and design scoring modules.

All functions here expect/return geometries in the projected CRS (meters) -
callers are responsible for reprojecting from WGS84 first.
"""

import geopandas as gpd
from shapely.geometry import LineString, shape
from shapely.ops import split

from backend.config import WGS84_CRS, PROJECTED_CRS


def geometry_from_geojson(geojson_dict: dict, target_crs: str = PROJECTED_CRS):
    """Single GeoJSON Geometry or Feature -> shapely geometry in `target_crs`."""
    geom_dict = geojson_dict["geometry"] if geojson_dict.get("type") == "Feature" else geojson_dict
    gseries = gpd.GeoSeries([shape(geom_dict)], crs=WGS84_CRS).to_crs(target_crs)
    return gseries.iloc[0]


def features_from_geojson(geojson_dict: dict, target_crs: str = PROJECTED_CRS) -> gpd.GeoDataFrame:
    """GeoJSON FeatureCollection (or single Feature/Geometry), any geometry type -> GeoDataFrame in `target_crs`."""
    if geojson_dict.get("type") == "FeatureCollection":
        features = geojson_dict["features"]
        if not features:
            return gpd.GeoDataFrame(geometry=[], crs=WGS84_CRS).to_crs(target_crs)
        gdf = gpd.GeoDataFrame.from_features(features, crs=WGS84_CRS)
    else:
        gdf = gpd.GeoDataFrame(geometry=[geometry_from_geojson(geojson_dict, WGS84_CRS)], crs=WGS84_CRS)
    return gdf.to_crs(target_crs)


def buffer_polygon(geom, radius_m):
    return geom.buffer(radius_m)


def count_points_in_polygon(points_gdf: gpd.GeoDataFrame, polygon) -> int:
    if points_gdf.empty:
        return 0
    return int(points_gdf.intersects(polygon).sum())


def area_weighted_density(zones_gdf: gpd.GeoDataFrame, polygon, value_field: str) -> float:
    """Weighted density (value per m^2) of `value_field` within `polygon`,
    aggregating over every zone that overlaps it, weighted by overlap area.
    """
    if zones_gdf.empty or polygon.area == 0:
        return 0.0

    total_value = 0.0
    for _, zone in zones_gdf.iterrows():
        overlap = zone.geometry.intersection(polygon)
        if overlap.is_empty or zone.geometry.area == 0:
            continue
        overlap_share = overlap.area / zone.geometry.area
        total_value += overlap_share * zone[value_field]

    return total_value / polygon.area


def density_per_km2(total_value: float, area_m2: float) -> float:
    if area_m2 == 0:
        return 0.0
    return total_value / (area_m2 / 1_000_000)


def side_strips(center_line: LineString, strip_width_m: float):
    """Split a buffer strip around `center_line` into a 'side A' / 'side B'
    polygon pair, one on each side of the line.
    """
    buffer_poly = center_line.buffer(strip_width_m, cap_style="flat")
    try:
        parts = list(split(buffer_poly, center_line).geoms)
    except Exception:
        parts = [buffer_poly]

    if len(parts) < 2:
        return buffer_poly, None
    parts = sorted(parts, key=lambda g: g.area, reverse=True)[:2]
    return parts[0], parts[1]


def built_up_pct(strip_polygon, built_up_gdf: gpd.GeoDataFrame) -> float:
    """% of `strip_polygon`'s area covered by `built_up_gdf`.

    The real built-up layer has ~90k individual polygons even after
    restricting to the Jerusalem area, so candidates are pre-filtered via the
    GeoDataFrame's spatial index before computing any exact intersection.
    """
    if strip_polygon is None or strip_polygon.area == 0 or built_up_gdf.empty:
        return 0.0
    candidate_idx = built_up_gdf.sindex.query(strip_polygon, predicate="intersects")
    if len(candidate_idx) == 0:
        return 0.0
    overlap_area = sum(
        strip_polygon.intersection(geom).area for geom in built_up_gdf.geometry.iloc[candidate_idx]
    )
    return 100.0 * overlap_area / strip_polygon.area


def crossing_reference_points(crossings_gdf: gpd.GeoDataFrame, road_line: LineString) -> gpd.GeoDataFrame:
    """One reference point per drawn crosswalk line: where it crosses the
    central road line if it actually intersects it, otherwise its centroid.
    """
    if crossings_gdf.empty:
        return crossings_gdf
    points = []
    for geom in crossings_gdf.geometry:
        inter = geom.intersection(road_line)
        if not inter.is_empty:
            points.append(inter.centroid if inter.geom_type != "Point" else inter)
        else:
            points.append(geom.centroid)
    return gpd.GeoDataFrame(geometry=points, crs=crossings_gdf.crs)


def order_points_along_line(points_gdf: gpd.GeoDataFrame, line: LineString):
    """Return points sorted by their projected distance along `line`."""
    if points_gdf.empty:
        return []
    projected = [(line.project(pt), pt) for pt in points_gdf.geometry]
    projected.sort(key=lambda t: t[0])
    return projected


def max_gap_along_line(points_gdf: gpd.GeoDataFrame, line: LineString) -> float:
    """Largest gap (meters) between consecutive crossing points projected
    onto the central road line, including the gaps to the line's endpoints.
    """
    ordered = order_points_along_line(points_gdf, line)
    positions = [0.0] + [pos for pos, _ in ordered] + [line.length]
    positions = sorted(set(positions))
    if len(positions) < 2:
        return line.length
    return max(b - a for a, b in zip(positions, positions[1:]))


def length_gap_pct(with_project_line: LineString, without_project_line: LineString) -> float:
    """% change in walking-path length caused by the project (positive = longer detour)."""
    if without_project_line.length == 0:
        return 0.0
    return 100.0 * (with_project_line.length - without_project_line.length) / without_project_line.length
