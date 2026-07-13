import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend import geo
from backend.config import DEFAULT_SETTINGS, WGS84_CRS
from backend.export import build_excel
from backend.layers import get_display_built_up_area, get_display_intersections, get_reference_layers
from backend.models import CategoryScore, ScoreRequest, ScoreResponse
from backend.scoring_design import MANUAL_INDICATOR_LABELS as DESIGN_MANUAL_LABELS
from backend.scoring_design import score_design
from backend.scoring_env import MANUAL_INDICATOR_LABELS as ENV_MANUAL_LABELS
from backend.scoring_env import score_environment

app = FastAPI(title="Grade-separation project scoring tool")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/api/settings/defaults")
def settings_defaults():
    return DEFAULT_SETTINGS


@app.get("/api/manual-indicator-labels")
def manual_indicator_labels():
    return {"environment": ENV_MANUAL_LABELS, "design": DESIGN_MANUAL_LABELS}


@app.get("/api/reference-layers")
def reference_layers():
    """Fixed background layers, reprojected back to WGS84 for the map.

    built_up_area and intersections are swapped for filtered/simplified
    display copies - the real ~90k-footprint / ~140k-point layers are only
    used server-side for scoring (see backend/layers.get_display_*).
    """
    return {
        # Already reprojected to WGS84 and precision-snapped, and cached.
        "intersections": json.loads(get_display_intersections().to_json()),
        "traffic_zones": json.loads(get_reference_layers()["traffic_zones"].to_crs(WGS84_CRS).to_json()),
        "built_up_area": json.loads(get_display_built_up_area().to_json()),
    }


def _compute_scores(request: ScoreRequest) -> ScoreResponse:
    reference = get_reference_layers()

    project_polygon_proj = geo.geometry_from_geojson(request.project_polygon)
    crossings_proj = geo.features_from_geojson(request.crossings)
    central_road_proj = geo.geometry_from_geojson(request.central_road)
    walking_with = (
        geo.geometry_from_geojson(request.walking_path_with_project)
        if request.walking_path_with_project
        else None
    )
    walking_without = (
        geo.geometry_from_geojson(request.walking_path_without_project)
        if request.walking_path_without_project
        else None
    )

    env_indicators = score_environment(
        project_polygon_proj, reference, request.settings, request.manual_environment
    )
    design_indicators = score_design(
        crossings_proj, central_road_proj, walking_with, walking_without, request.settings, request.manual_design
    )

    return ScoreResponse(
        environment=CategoryScore(indicators=env_indicators, total=sum(i.result for i in env_indicators)),
        design=CategoryScore(indicators=design_indicators, total=sum(i.result for i in design_indicators)),
    )


@app.post("/api/score", response_model=ScoreResponse)
def compute_score(request: ScoreRequest):
    return _compute_scores(request)


@app.post("/api/export")
def export_score(request: ScoreRequest):
    response = _compute_scores(request)
    excel_buffer = build_excel(response)
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=grade_separation_score.xlsx"},
    )


# Serve the frontend last so it doesn't shadow the /api routes above.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
