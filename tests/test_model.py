from datetime import datetime, timezone

from app.model import run_irrigation_model
from app.schemas import (
    IrrigationRequest,
    SensorInput,
    TreeConfig,
    WeatherInput,
)


def build_request(
    soil_vwc: float,
    forecast_rain_mm: float = 0.0,
    sensor_status: str = "OK",
) -> IrrigationRequest:
    return IrrigationRequest(
        tree=TreeConfig(
            tree_id="TREE-TEST",
            species="test",
            age_category="young",
            effective_depth_m=0.3,
            irrigated_area_m2=2.0,
            field_capacity_vwc=0.30,
            wilting_point_vwc=0.12,
            target_vwc=0.26,
            critical_vwc=0.15,
            allowable_depletion=0.4,
            site_adjusted_tree_coefficient=0.65,
            rainfall_capture_efficiency=0.7,
            irrigation_efficiency=0.8,
            rain_replacement_fraction=0.7,
            minimum_litres=5.0,
            maximum_litres=50.0,
        ),
        weather=WeatherInput(
            timestamp=datetime.now(timezone.utc),
            mean_temperature_c=28.0,
            relative_humidity_percent=45.0,
            wind_speed_m_s=2.8,
            net_radiation_mj_m2_day=15.5,
            soil_heat_flux_mj_m2_day=0.0,
            atmospheric_pressure_kpa=101.3,
            rainfall_previous_24h_mm=0.0,
            rainfall_forecast_24h_mm=forecast_rain_mm,
        ),
        sensor=SensorInput(
            timestamp=datetime.now(timezone.utc),
            soil_vwc=soil_vwc,
            soil_temperature_c=23.4,
            sensor_status=sensor_status,
        ),
    )


def test_no_water_when_soil_is_wet() -> None:
    result = run_irrigation_model(
        build_request(soil_vwc=0.28)
    )

    assert result.decision == "NO_WATER_NEEDED"
    assert result.recommended_litres == 0


def test_water_now_when_critical() -> None:
    result = run_irrigation_model(
        build_request(soil_vwc=0.14)
    )

    assert result.decision == "WATER_NOW"
    assert result.priority_score >= 90
    assert result.recommended_litres > 0


def test_wait_when_rain_can_replace_deficit() -> None:
    result = run_irrigation_model(
        build_request(
            soil_vwc=0.20,
            forecast_rain_mm=30.0,
        )
    )

    assert result.decision == "WAIT_FOR_RAIN"
    assert result.recommended_litres == 0


def test_failed_sensor_requires_inspection() -> None:
    result = run_irrigation_model(
        build_request(
            soil_vwc=0.20,
            sensor_status="FAILED",
        )
    )

    assert result.decision == "SENSOR_INSPECTION_REQUIRED"
    assert result.data_quality == "INVALID"
    assert result.recommended_litres == 0