from backend import geo
from backend.models import IndicatorResult, ManualDesignInputs, Settings

# Labels for the manual placeholder indicators - precise auto-calculation
# logic for these is still being worked out with the domain expert.
MANUAL_INDICATOR_LABELS = {
    "grade_change_requires_climbing": "שינוי מפלסי המצריך עלייה/ירידה של הולכי רגל",
    "transit_improvement": "שיפור בתחבורה הציבורית",
    "purpose_of_construction": "סיבת ההקמה (שיפור לרכב מול שיפור להליכתיות)",
    "road_width_mode_share": "רוחב דרך עירונית / נתח נסועה לרכב פרטי",
    "sense_of_place": "תחושת מקום / הזמנה לשהייה",
    "visual_blockage": "חסימה חזותית",
    "street_activity": "רמת פעילות ברחוב",
    "safety": "בטיחות",
}

CROSSING_SPACING_LABEL = "מרווח בין מעברי חצייה"
WALKING_PATH_GAP_LABEL = "פער אורך מסלול הליכה (עם התוכנית מול בלעדיה)"


def score_design(
    crossings_proj,
    central_road_proj,
    walking_path_with_project_proj,
    walking_path_without_project_proj,
    settings: Settings,
    manual: ManualDesignInputs,
) -> list[IndicatorResult]:
    indicators = []

    # 1. Crossing spacing (automatic) - one reference point per drawn crosswalk line
    crossing_points = geo.crossing_reference_points(crossings_proj, central_road_proj)
    max_gap = geo.max_gap_along_line(crossing_points, central_road_proj)
    indicators.append(
        IndicatorResult(
            key="crossing_spacing",
            label=CROSSING_SPACING_LABEL,
            raw_value=round(max_gap, 1),
            threshold=settings.crossing_spacing_threshold_m,
            result=1 if max_gap <= settings.crossing_spacing_threshold_m else -1,
            automatic=True,
        )
    )

    # 2. Walking path length gap (automatic) - needs both comparison lines drawn
    if walking_path_with_project_proj is not None and walking_path_without_project_proj is not None:
        gap_pct = geo.length_gap_pct(walking_path_with_project_proj, walking_path_without_project_proj)
        result = -1 if gap_pct > settings.walking_path_length_gap_pct_threshold else 1
        raw_value = round(gap_pct, 1)
    else:
        gap_pct, result, raw_value = None, 0, None

    indicators.append(
        IndicatorResult(
            key="walking_path_length_gap",
            label=WALKING_PATH_GAP_LABEL,
            raw_value=raw_value,
            threshold=settings.walking_path_length_gap_pct_threshold if raw_value is not None else None,
            result=result,
            automatic=True,
        )
    )

    # 3. Remaining sub-indicators - manual -1/0/1 placeholders for now
    for key, label in MANUAL_INDICATOR_LABELS.items():
        indicators.append(
            IndicatorResult(
                key=key,
                label=label,
                raw_value=None,
                threshold=None,
                result=getattr(manual, key),
                automatic=False,
            )
        )

    return indicators
