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
    forecast_rain_mm: float = 0,
) -> IrrigationRequest:
    return IrrigationRequest(
        tree=TreeConfig(
            tree_id="TREE-TEST",
            species="test",
            age_category="young",
            root_depth_m=0.3,
            irrigated_area_m2=2.0,
            field_capacity_vwc=0.30,
            wilting_point_vwc=0.12,
            target_vwc=0.26,
            critical_vwc=0.15,
            allowable_depletion=0.4,
            tree_coefficient=0.65,
        ),
        weather=WeatherInput(
            timestamp=datetime.now(timezone.utc),
            mean_temperature_c=28,
            relative_humidity_percent=45,
            wind_speed_m_s=2.8,
            net_radiation_mj_m2_day=15.5,
            rainfall_forecast_24h_mm=forecast_rain_mm,
        ),
        sensor=SensorInput(
            timestamp=datetime.now(timezone.utc),
            soil_vwc=soil_vwc,
            sensor_quality=0.9,
            sensor_status="OK",
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


def test_wait_when_rain_is_expected() -> None:
    result = run_irrigation_model(
        build_request(
            soil_vwc=0.20,
            forecast_rain_mm=10,
        )
    )

    assert result.decision == "WAIT_FOR_RAIN"
    assert result.recommended_litres == 0