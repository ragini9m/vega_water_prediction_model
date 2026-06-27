'''
calculate ET₀ -> calculate tree ET -> calculate thresholds -> convert sensor VWC to water storage
    -> predict future storage -> predict VWC after 24 hours -> calculate required litres -> choose the watering decision
'''
    
from __future__ import annotations

from app.decision import (
    calculate_priority_score,
    choose_decision,
)
from app.eto import calculate_eto
from app.schemas import (
    IrrigationRequest,
    IrrigationResponse,
)
from app.water_balance import (
    calculate_refill_threshold,
    calculate_required_litres,
    calculate_tree_et,
    fuse_sensor_and_model,
    litres_to_mm,
    storage_mm_to_vwc,
    update_storage,
    vwc_to_storage_mm,
)


def age_vulnerability(age_category: str) -> float:
    return {
        "new": 1.0,
        "young": 0.7,
        "mature": 0.4,
    }.get(age_category, 0.5)


def calculate_heat_factor(
    temperature_c: float,
    eto_mm_day: float,
) -> float:
    temperature_component = max(
        0.0,
        min(
            1.0,
            (temperature_c - 20.0) / 15.0,
        ),
    )

    eto_component = max(
        0.0,
        min(
            1.0,
            eto_mm_day / 7.0,
        ),
    )

    return (
        0.5 * temperature_component
        + 0.5 * eto_component
    )


def calculate_confidence(
    sensor_quality: float,
    sensor_status: str,
    tree_config_complete: bool = True,
) -> float:
    status_factor = {
        "OK": 1.0,
        "NOISY": 0.65,
        "UNCALIBRATED": 0.40,
        "FAILED": 0.10,
    }[sensor_status]

    config_factor = (
        1.0 if tree_config_complete else 0.6
    )

    confidence = (
        0.65 * sensor_quality
        + 0.25 * status_factor
        + 0.10 * config_factor
    )

    return round(
        max(0.0, min(1.0, confidence)),
        2,
    )


def run_irrigation_model(
    request: IrrigationRequest,
) -> IrrigationResponse:
    tree = request.tree
    weather = request.weather
    sensor = request.sensor

    eto = calculate_eto(weather)

    tree_et = calculate_tree_et(
        eto_mm_day=eto,
        tree_coefficient=tree.tree_coefficient,
    )

    refill_threshold = calculate_refill_threshold(
        field_capacity_vwc=tree.field_capacity_vwc,
        wilting_point_vwc=tree.wilting_point_vwc,
        allowable_depletion=tree.allowable_depletion,
    )

    sensor_storage = vwc_to_storage_mm(
        volumetric_water_content=sensor.soil_vwc,
        root_depth_m=tree.root_depth_m,
    )

    previous_irrigation_mm = litres_to_mm(
        litres=request.irrigation_previous_24h_litres,
        area_m2=tree.irrigated_area_m2,
    )

    model_storage_now = update_storage(
        current_storage_mm=sensor_storage,
        tree_et_mm=tree_et,
        rainfall_mm=weather.rainfall_previous_24h_mm,
        irrigation_mm=previous_irrigation_mm,
        rainfall_efficiency=tree.rainfall_efficiency,
        irrigation_efficiency=tree.irrigation_efficiency,
    )

    fused_storage = fuse_sensor_and_model(
        sensor_storage_mm=sensor_storage,
        model_storage_mm=model_storage_now,
        sensor_quality=sensor.sensor_quality,
    )

    predicted_storage = update_storage(
        current_storage_mm=fused_storage,
        tree_et_mm=tree_et,
        rainfall_mm=weather.rainfall_forecast_24h_mm,
        irrigation_mm=0.0,
        rainfall_efficiency=tree.rainfall_efficiency,
        irrigation_efficiency=tree.irrigation_efficiency,
    )

    maximum_storage = vwc_to_storage_mm(
        tree.field_capacity_vwc,
        tree.root_depth_m,
    )

    predicted_storage = min(
        maximum_storage,
        predicted_storage,
    )

    predicted_vwc = storage_mm_to_vwc(
        predicted_storage,
        tree.root_depth_m,
    )

    predicted_vwc = max(
        tree.wilting_point_vwc,
        min(tree.field_capacity_vwc, predicted_vwc),
    )

    recommended_litres = calculate_required_litres(
        current_vwc=sensor.soil_vwc,
        target_vwc=tree.target_vwc,
        root_depth_m=tree.root_depth_m,
        irrigated_area_m2=tree.irrigated_area_m2,
        irrigation_efficiency=tree.irrigation_efficiency,
        minimum_litres=tree.minimum_litres,
        maximum_litres=tree.maximum_litres,
    )

    effective_forecast_rain = (
        weather.rainfall_forecast_24h_mm
        * tree.rainfall_efficiency
    )

    decision, litres, explanation = choose_decision(
        current_vwc=sensor.soil_vwc,
        predicted_vwc_24h=predicted_vwc,
        target_vwc=tree.target_vwc,
        refill_threshold_vwc=refill_threshold,
        critical_vwc=tree.critical_vwc,
        effective_forecast_rain_mm=effective_forecast_rain,
        sensor_status=sensor.sensor_status,
        recommended_litres=recommended_litres,
    )

    heat_factor = calculate_heat_factor(
        temperature_c=weather.mean_temperature_c,
        eto_mm_day=eto,
    )

    vulnerability = age_vulnerability(
        tree.age_category
    )

    priority = calculate_priority_score(
        current_vwc=sensor.soil_vwc,
        predicted_vwc_24h=predicted_vwc,
        refill_threshold_vwc=refill_threshold,
        critical_vwc=tree.critical_vwc,
        heat_factor=heat_factor,
        vulnerability_factor=vulnerability,
    )

    if decision == "NO_WATER_NEEDED":
        priority = min(priority, 20)
    elif decision == "WAIT_FOR_RAIN":
        priority = min(priority, 40)
    elif decision == "WATER_NOW":
        priority = max(priority, 90)

    confidence = calculate_confidence(
        sensor_quality=sensor.sensor_quality,
        sensor_status=sensor.sensor_status,
    )

    return IrrigationResponse(
        tree_id=tree.tree_id,
        timestamp=sensor.timestamp,
        eto_mm_day=round(eto, 3),
        tree_et_mm_day=round(tree_et, 3),
        current_vwc=round(sensor.soil_vwc, 4),
        predicted_vwc_24h=round(predicted_vwc, 4),
        refill_threshold_vwc=round(
            refill_threshold,
            4,
        ),
        target_vwc=tree.target_vwc,
        critical_vwc=tree.critical_vwc,
        decision=decision,
        recommended_litres=litres,
        priority_score=priority,
        confidence=confidence,
        explanation=explanation,
    )