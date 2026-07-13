from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.config import DEFAULT_SETTINGS

ManualScore = Literal[-1, 0, 1]


class Settings(BaseModel):
    env_buffer_radius_m: float = DEFAULT_SETTINGS["env_buffer_radius_m"]
    intersection_density_threshold_per_km2: float = DEFAULT_SETTINGS["intersection_density_threshold_per_km2"]
    population_density_threshold_per_km2: float = DEFAULT_SETTINGS["population_density_threshold_per_km2"]
    employment_density_threshold_per_km2: float = DEFAULT_SETTINGS["employment_density_threshold_per_km2"]
    active_edge_buffer_m: float = DEFAULT_SETTINGS["active_edge_buffer_m"]
    active_edge_builtup_pct_threshold: float = DEFAULT_SETTINGS["active_edge_builtup_pct_threshold"]
    crossing_spacing_threshold_m: float = DEFAULT_SETTINGS["crossing_spacing_threshold_m"]
    walking_path_length_gap_pct_threshold: float = DEFAULT_SETTINGS["walking_path_length_gap_pct_threshold"]


class ManualEnvironmentInputs(BaseModel):
    future_urban_development: ManualScore = 0


class ManualDesignInputs(BaseModel):
    grade_change_requires_climbing: ManualScore = 0
    transit_improvement: ManualScore = 0
    purpose_of_construction: ManualScore = 0
    road_width_mode_share: ManualScore = 0
    sense_of_place: ManualScore = 0
    visual_blockage: ManualScore = 0
    street_activity: ManualScore = 0
    safety: ManualScore = 0


class ScoreRequest(BaseModel):
    # GeoJSON geometry/feature-collection dicts, in WGS84 (lon/lat), as drawn on the Leaflet map
    project_polygon: dict[str, Any]
    crossings: dict[str, Any]  # FeatureCollection of crosswalk LineStrings across the road
    central_road: dict[str, Any]
    # Two comparison walking-path lines for the automatic walking_path_length_gap
    # indicator - optional because the indicator can't be computed without both.
    walking_path_with_project: dict[str, Any] | None = None
    walking_path_without_project: dict[str, Any] | None = None
    settings: Settings = Field(default_factory=Settings)
    manual_environment: ManualEnvironmentInputs = Field(default_factory=ManualEnvironmentInputs)
    manual_design: ManualDesignInputs = Field(default_factory=ManualDesignInputs)


class IndicatorResult(BaseModel):
    key: str
    label: str
    raw_value: float | str | None
    threshold: float | str | None
    result: ManualScore
    automatic: bool


class CategoryScore(BaseModel):
    indicators: list[IndicatorResult]
    total: int


class ScoreResponse(BaseModel):
    environment: CategoryScore
    design: CategoryScore
