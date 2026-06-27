from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WeatherInput(BaseModel):
    timestamp: datetime

    mean_temperature_c: float = Field(ge=-40, le=60)
    relative_humidity_percent: float = Field(ge=0, le=100)
    wind_speed_m_s: float = Field(ge=0, le=50)

    net_radiation_mj_m2_day: float = Field(ge=0)
    soil_heat_flux_mj_m2_day: float = 0.0
    atmospheric_pressure_kpa: float = Field(default=101.3, gt=0)

    rainfall_previous_24h_mm: float = Field(default=0.0, ge=0)
    rainfall_forecast_24h_mm: float = Field(default=0.0, ge=0)


class TreeConfig(BaseModel):
    tree_id: str
    species: str = "unknown"
    age_category: Literal["new", "young", "mature"] = "young"

    root_depth_m: float = Field(gt=0, le=3)
    irrigated_area_m2: float = Field(gt=0, le=100)

    field_capacity_vwc: float = Field(gt=0, lt=1)
    wilting_point_vwc: float = Field(gt=0, lt=1)
    target_vwc: float = Field(gt=0, lt=1)
    critical_vwc: float = Field(gt=0, lt=1)

    allowable_depletion: float = Field(default=0.4, ge=0, le=1)
    tree_coefficient: float = Field(default=0.65, ge=0, le=2)

    rainfall_efficiency: float = Field(default=0.7, ge=0, le=1)
    irrigation_efficiency: float = Field(default=0.8, gt=0, le=1)

    minimum_litres: float = Field(default=5, ge=0)
    maximum_litres: float = Field(default=50, gt=0)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "TreeConfig":
        if self.wilting_point_vwc >= self.field_capacity_vwc:
            raise ValueError(
                "Wilting point must be lower than field capacity."
            )

        if self.critical_vwc >= self.target_vwc:
            raise ValueError(
                "Critical VWC must be lower than target VWC."
            )

        if not (
            self.wilting_point_vwc
            <= self.critical_vwc
            <= self.field_capacity_vwc
        ):
            raise ValueError(
                "Critical VWC must lie between wilting point "
                "and field capacity."
            )

        if not (
            self.wilting_point_vwc
            <= self.target_vwc
            <= self.field_capacity_vwc
        ):
            raise ValueError(
                "Target VWC must lie between wilting point "
                "and field capacity."
            )

        if self.minimum_litres > self.maximum_litres:
            raise ValueError(
                "Minimum litres cannot exceed maximum litres."
            )

        return self


class SensorInput(BaseModel):
    timestamp: datetime
    soil_vwc: float = Field(ge=0, le=1)
    soil_temperature_c: float | None = Field(default=None, ge=-20, le=70)

    sensor_quality: float = Field(default=1.0, ge=0, le=1)
    sensor_status: Literal[
        "OK",
        "NOISY",
        "FAILED",
        "UNCALIBRATED",
    ] = "OK"


class IrrigationRequest(BaseModel):
    tree: TreeConfig
    weather: WeatherInput
    sensor: SensorInput

    irrigation_previous_24h_litres: float = Field(default=0, ge=0)


class IrrigationResponse(BaseModel):
    tree_id: str
    timestamp: datetime

    eto_mm_day: float
    tree_et_mm_day: float

    current_vwc: float
    predicted_vwc_24h: float

    refill_threshold_vwc: float
    target_vwc: float
    critical_vwc: float

    decision: Literal[
        "NO_WATER_NEEDED",
        "MONITOR",
        "WAIT_FOR_RAIN",
        "WATER_WITHIN_24H",
        "WATER_NOW",
        "SENSOR_INSPECTION_REQUIRED",
    ]

    recommended_litres: float
    priority_score: int
    confidence: float
    explanation: list[str]