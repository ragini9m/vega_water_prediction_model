'''
calculate ET₀ -> calculate tree ET -> calculate thresholds -> convert sensor VWC to water storage
    -> predict future storage -> predict VWC after 24 hours -> calculate required litres -> choose the watering decision
'''
from __future__ import annotations

from app.decision import choose_decision
from app.eto import calculate_eto
from app.schemas import (
    IrrigationRequest,
    IrrigationResponse,
)
from app.water_balance import (
    calculate_expected_rain_litres,
    calculate_refill_threshold,
    calculate_required_litres,
    calculate_tree_et,
    forecast_root_zone_storage,
)


def determine_data_quality(
    sensor_status: str,
) -> str:
    return {
        "OK": "HIGH",
        "NOISY": "MEDIUM",
        "STALE": "LOW",
        "UNCALIBRATED": "INVALID",
        "FAILED": "INVALID",
    }[sensor_status]


def run_irrigation_model(
    request: IrrigationRequest,
) -> IrrigationResponse:
    tree = request.tree
    weather = request.weather
    sensor = request.sensor

    eto_mm_day = calculate_eto(weather)

    tree_et_mm_day = calculate_tree_et(
        eto_mm_day=eto_mm_day,
        site_adjusted_tree_coefficient=(
            tree.site_adjusted_tree_coefficient
        ),
    )

    refill_threshold_vwc = calculate_refill_threshold(
        field_capacity_vwc=tree.field_capacity_vwc,
        wilting_point_vwc=tree.wilting_point_vwc,
        allowable_depletion=tree.allowable_depletion,
    )

    forecast = forecast_root_zone_storage(
        current_vwc=sensor.soil_vwc,
        effective_depth_m=tree.effective_depth_m,
        field_capacity_vwc=tree.field_capacity_vwc,
        tree_et_forecast_mm=tree_et_mm_day,
        rainfall_forecast_mm=(
            weather.rainfall_forecast_24h_mm
        ),
        rainfall_capture_efficiency=(
            tree.rainfall_capture_efficiency
        ),
    )

    predicted_vwc_24h = max(
        tree.wilting_point_vwc,
        min(
            tree.field_capacity_vwc,
            forecast["future_vwc"],
        ),
    )

    water_amounts = calculate_required_litres(
        current_vwc=sensor.soil_vwc,
        target_vwc=tree.target_vwc,
        effective_depth_m=tree.effective_depth_m,
        irrigated_area_m2=tree.irrigated_area_m2,
        irrigation_efficiency=tree.irrigation_efficiency,
        minimum_litres=tree.minimum_litres,
        maximum_litres=tree.maximum_litres,
    )

    expected_rain_litres = calculate_expected_rain_litres(
        rainfall_forecast_mm=(
            weather.rainfall_forecast_24h_mm
        ),
        irrigated_area_m2=tree.irrigated_area_m2,
        rainfall_capture_efficiency=(
            tree.rainfall_capture_efficiency
        ),
    )

    (
        decision,
        recommended_litres,
        priority_score,
        explanation,
    ) = choose_decision(
        current_vwc=sensor.soil_vwc,
        predicted_vwc_24h=predicted_vwc_24h,
        target_vwc=tree.target_vwc,
        refill_threshold_vwc=refill_threshold_vwc,
        critical_vwc=tree.critical_vwc,
        sensor_status=sensor.sensor_status,
        recommended_litres=(
            water_amounts["recommended_litres"]
        ),
        water_deficit_litres=(
            water_amounts["net_litres"]
        ),
        expected_rain_litres=expected_rain_litres,
        rain_replacement_fraction=(
            tree.rain_replacement_fraction
        ),
    )

    return IrrigationResponse(
        tree_id=tree.tree_id,
        timestamp=sensor.timestamp,
        eto_mm_day=round(eto_mm_day, 3),
        tree_et_mm_day=round(tree_et_mm_day, 3),
        current_vwc=round(sensor.soil_vwc, 4),
        predicted_vwc_24h=round(
            predicted_vwc_24h,
            4,
        ),
        refill_threshold_vwc=round(
            refill_threshold_vwc,
            4,
        ),
        target_vwc=tree.target_vwc,
        critical_vwc=tree.critical_vwc,
        effective_rain_forecast_mm=round(
            forecast["effective_rain_mm"],
            2,
        ),
        expected_rain_litres=round(
            expected_rain_litres,
            1,
        ),
        water_deficit_litres=(
            water_amounts["net_litres"]
        ),
        calculated_gross_litres=(
            water_amounts["gross_litres"]
        ),
        recommended_litres=recommended_litres,
        recommendation_capped=(
            water_amounts["recommendation_capped"]
        ),
        predicted_drainage_mm=round(
            forecast["drainage_mm"],
            2,
        ),
        decision=decision,
        priority_score=priority_score,
        data_quality=determine_data_quality(
            sensor.sensor_status
        ),
        explanation=explanation,
    )