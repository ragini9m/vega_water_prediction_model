from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WeatherInput(BaseModel):
    timestamp: datetime

    mean_temperature_c: float = Field(ge=-40, le=60)
    relative_humidity_percent: float = Field(ge=0, le=100)
    wind_speed_m_s: float = Field(ge=0, le=50)

    net_radiation_mj_m2_day: float = Field(
        default=0.0,
        ge=0,
    )

    shortwave_radiation_mj_m2_day: float = Field(
        default=0.0,
        ge=0,
    )

    soil_heat_flux_mj_m2_day: float = 0.0

    atmospheric_pressure_kpa: float = Field(
        default=101.3,
        gt=0,
    )

    rainfall_previous_24h_mm: float = Field(
        default=0.0,
        ge=0,
    )

    rainfall_forecast_24h_mm: float = Field(
        default=0.0,
        ge=0,
    )

    eto_forecast_24h_mm: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Reference ET supplied by the weather provider. "
            "When available, this is used instead of calculating "
            "ET0 from incomplete weather variables."
        ),
    )

    weather_source: str = "manual"

class TreeConfig(BaseModel):
    tree_id: str
    species: str = "unknown"
    age_category: Literal[
        "new",
        "young",
        "mature",
    ] = "young"

    effective_depth_m: float = Field(
        gt=0,
        le=3,
        description=(
            "Effective soil depth represented by the sensor "
            "and watering model."
        ),
    )

    irrigated_area_m2: float = Field(
        gt=0,
        le=100,
    )

    field_capacity_vwc: float = Field(
        gt=0,
        lt=1,
    )

    wilting_point_vwc: float = Field(
        gt=0,
        lt=1,
    )

    target_vwc: float = Field(
        gt=0,
        lt=1,
    )

    critical_vwc: float = Field(
        gt=0,
        lt=1,
    )

    allowable_depletion: float = Field(
        default=0.4,
        ge=0,
        le=1,
    )

    site_adjusted_tree_coefficient: float = Field(
        default=0.65,
        ge=0,
        le=2,
    )

    rainfall_capture_efficiency: float = Field(
        default=0.7,
        ge=0,
        le=1,
    )

    irrigation_efficiency: float = Field(
        default=0.8,
        gt=0,
        le=1,
    )

    rain_replacement_fraction: float = Field(
        default=0.7,
        ge=0,
        le=1,
    )

    minimum_litres: float = Field(
        default=5.0,
        ge=0,
    )

    maximum_litres: float = Field(
        default=50.0,
        gt=0,
    )

    @model_validator(mode="after")
    def validate_thresholds(
        self,
    ) -> "TreeConfig":
        if (
            self.wilting_point_vwc
            >= self.field_capacity_vwc
        ):
            raise ValueError(
                "Wilting point must be below field capacity."
            )

        if not (
            self.wilting_point_vwc
            <= self.critical_vwc
            <= self.target_vwc
            <= self.field_capacity_vwc
        ):
            raise ValueError(
                "Required order: wilting point <= critical "
                "<= target <= field capacity."
            )

        if self.minimum_litres > self.maximum_litres:
            raise ValueError(
                "Minimum litres cannot exceed maximum litres."
            )

        return self

class SensorInput(BaseModel):
    timestamp: datetime

    soil_vwc: float = Field(
        ge=0,
        le=1,
        description=(
            "Calibrated volumetric water content, not raw ADC."
        ),
    )

    soil_temperature_c: float | None = Field(
        default=None,
        ge=-20,
        le=70,
    )

    sensor_status: Literal[
        "OK",
        "NOISY",
        "FAILED",
        "UNCALIBRATED",
        "STALE",
    ] = "OK"


class IrrigationRequest(BaseModel):
    tree: TreeConfig
    weather: WeatherInput
    sensor: SensorInput

class LivePredictionRequest(BaseModel):
    tree: TreeConfig
    sensor: SensorInput

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    timezone: str = Field(
        default="auto",
        description=(
            "Open-Meteo timezone. Use 'auto' to determine it "
            "from latitude and longitude."
        ),
    )


class WeatherPreviewRequest(BaseModel):
    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    timezone: str = "auto"

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

    effective_rain_forecast_mm: float
    expected_rain_litres: float

    water_deficit_litres: float
    calculated_gross_litres: float
    recommended_litres: float
    recommendation_capped: bool

    predicted_drainage_mm: float

    decision: Literal[
        "NO_WATER_NEEDED",
        "MONITOR",
        "WAIT_FOR_RAIN",
        "WATER_WITHIN_24H",
        "WATER_NOW",
        "SENSOR_INSPECTION_REQUIRED",
    ]

    priority_score: int

    data_quality: Literal[
        "HIGH",
        "MEDIUM",
        "LOW",
        "INVALID",
    ]

    explanation: list[str]