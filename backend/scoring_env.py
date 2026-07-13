from backend import geo
from backend.config import POPULATION_FIELD, EMPLOYMENT_FIELD
from backend.models import IndicatorResult, ManualEnvironmentInputs, Settings

MANUAL_INDICATOR_LABELS = {
    "future_urban_development": "תוספת פיתוח עירוני עתידי משמעותי",
}


def score_environment(
    project_polygon_proj,
    reference_layers: dict,
    settings: Settings,
    manual: ManualEnvironmentInputs,
) -> list[IndicatorResult]:
    buffer_poly = geo.buffer_polygon(project_polygon_proj, settings.env_buffer_radius_m)
    buffer_area_m2 = buffer_poly.area

    indicators = []

    # 1. Intersection density
    intersection_count = geo.count_points_in_polygon(reference_layers["intersections"], buffer_poly)
    intersection_density = geo.density_per_km2(intersection_count, buffer_area_m2)
    indicators.append(
        IndicatorResult(
            key="intersection_density",
            label="צפיפות צמתים",
            raw_value=round(intersection_density, 2),
            threshold=settings.intersection_density_threshold_per_km2,
            result=1 if intersection_density >= settings.intersection_density_threshold_per_km2 else -1,
            automatic=True,
        )
    )

    # 2. Population density (area-weighted across overlapping traffic zones)
    pop_density_per_m2 = geo.area_weighted_density(reference_layers["traffic_zones"], buffer_poly, POPULATION_FIELD)
    pop_density = pop_density_per_m2 * 1_000_000
    indicators.append(
        IndicatorResult(
            key="population_density",
            label="צפיפות אוכלוסין",
            raw_value=round(pop_density, 2),
            threshold=settings.population_density_threshold_per_km2,
            result=1 if pop_density >= settings.population_density_threshold_per_km2 else -1,
            automatic=True,
        )
    )

    # 3. Employment density (area-weighted across overlapping traffic zones)
    emp_density_per_m2 = geo.area_weighted_density(reference_layers["traffic_zones"], buffer_poly, EMPLOYMENT_FIELD)
    emp_density = emp_density_per_m2 * 1_000_000
    indicators.append(
        IndicatorResult(
            key="employment_density",
            label="צפיפות מועסקים",
            raw_value=round(emp_density, 2),
            threshold=settings.employment_density_threshold_per_km2,
            result=1 if emp_density >= settings.employment_density_threshold_per_km2 else -1,
            automatic=True,
        )
    )

    # 4. Active edges: built-up % on both sides of the project footprint boundary
    boundary_line = project_polygon_proj.boundary
    side_a, side_b = geo.side_strips(boundary_line, settings.active_edge_buffer_m)
    pct_a = geo.built_up_pct(side_a, reference_layers["built_up_area"])
    pct_b = geo.built_up_pct(side_b, reference_layers["built_up_area"])
    both_sides_active = (
        pct_a >= settings.active_edge_builtup_pct_threshold
        and pct_b >= settings.active_edge_builtup_pct_threshold
    )
    indicators.append(
        IndicatorResult(
            key="active_edges",
            label="דפנות פעילות (אחוז שטח בנוי משני הצדדים)",
            raw_value=f"{round(pct_a, 1)}% / {round(pct_b, 1)}%",
            threshold=f">= {settings.active_edge_builtup_pct_threshold}% בשני הצדדים",
            result=1 if both_sides_active else -1,
            automatic=True,
        )
    )

    # 5. Future urban development (manual)
    indicators.append(
        IndicatorResult(
            key="future_urban_development",
            label=MANUAL_INDICATOR_LABELS["future_urban_development"],
            raw_value=None,
            threshold=None,
            result=manual.future_urban_development,
            automatic=False,
        )
    )

    return indicators
