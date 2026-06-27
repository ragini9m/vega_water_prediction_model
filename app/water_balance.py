''' 
This performs water calculations:
Converting soil VWC into stored root-zone water
Calculating the refill threshold
Calculating tree evapotranspiration
Adding effective rain
Adding previous irrigation
Predicting future root-zone water
Calculating the required litres
'''
from __future__ import annotations


def vwc_to_storage_mm(
    volumetric_water_content: float,
    effective_depth_m: float,
) -> float:
    if effective_depth_m <= 0:
        raise ValueError(
            "Effective depth must be greater than zero."
        )

    return (
        volumetric_water_content
        * effective_depth_m
        * 1000.0
    )


def storage_mm_to_vwc(
    storage_mm: float,
    effective_depth_m: float,
) -> float:
    if effective_depth_m <= 0:
        raise ValueError(
            "Effective depth must be greater than zero."
        )

    return storage_mm / (
        effective_depth_m * 1000.0
    )


def calculate_refill_threshold(
    field_capacity_vwc: float,
    wilting_point_vwc: float,
    allowable_depletion: float,
) -> float:
    return field_capacity_vwc - (
        allowable_depletion
        * (
            field_capacity_vwc
            - wilting_point_vwc
        )
    )


def calculate_tree_et(
    eto_mm_day: float,
    site_adjusted_tree_coefficient: float,
) -> float:
    return max(
        0.0,
        eto_mm_day
        * site_adjusted_tree_coefficient,
    )


def forecast_root_zone_storage(
    current_vwc: float,
    effective_depth_m: float,
    field_capacity_vwc: float,
    tree_et_forecast_mm: float,
    rainfall_forecast_mm: float,
    rainfall_capture_efficiency: float,
) -> dict:
    current_storage_mm = vwc_to_storage_mm(
        current_vwc,
        effective_depth_m,
    )

    effective_rain_mm = (
        max(0.0, rainfall_forecast_mm)
        * rainfall_capture_efficiency
    )

    unbounded_future_storage_mm = (
        current_storage_mm
        - max(0.0, tree_et_forecast_mm)
        + effective_rain_mm
    )

    field_capacity_storage_mm = vwc_to_storage_mm(
        field_capacity_vwc,
        effective_depth_m,
    )

    drainage_mm = max(
        0.0,
        unbounded_future_storage_mm
        - field_capacity_storage_mm,
    )

    future_storage_mm = min(
        field_capacity_storage_mm,
        max(0.0, unbounded_future_storage_mm),
    )

    future_vwc = storage_mm_to_vwc(
        future_storage_mm,
        effective_depth_m,
    )

    return {
        "current_storage_mm": current_storage_mm,
        "effective_rain_mm": effective_rain_mm,
        "future_storage_mm": future_storage_mm,
        "future_vwc": future_vwc,
        "drainage_mm": drainage_mm,
    }


def calculate_water_deficit_litres(
    current_vwc: float,
    target_vwc: float,
    effective_depth_m: float,
    irrigated_area_m2: float,
) -> float:
    if current_vwc >= target_vwc:
        return 0.0

    return (
        (target_vwc - current_vwc)
        * effective_depth_m
        * irrigated_area_m2
        * 1000.0
    )


def calculate_expected_rain_litres(
    rainfall_forecast_mm: float,
    irrigated_area_m2: float,
    rainfall_capture_efficiency: float,
) -> float:
    return (
        max(0.0, rainfall_forecast_mm)
        * irrigated_area_m2
        * rainfall_capture_efficiency
    )


def calculate_required_litres(
    current_vwc: float,
    target_vwc: float,
    effective_depth_m: float,
    irrigated_area_m2: float,
    irrigation_efficiency: float,
    minimum_litres: float,
    maximum_litres: float,
) -> dict:
    net_litres = calculate_water_deficit_litres(
        current_vwc=current_vwc,
        target_vwc=target_vwc,
        effective_depth_m=effective_depth_m,
        irrigated_area_m2=irrigated_area_m2,
    )

    if net_litres <= 0:
        return {
            "net_litres": 0.0,
            "gross_litres": 0.0,
            "recommended_litres": 0.0,
            "recommendation_capped": False,
        }

    gross_litres = (
        net_litres
        / irrigation_efficiency
    )

    recommended_litres = min(
        maximum_litres,
        max(minimum_litres, gross_litres),
    )

    return {
        "net_litres": round(net_litres, 1),
        "gross_litres": round(gross_litres, 1),
        "recommended_litres": round(
            recommended_litres,
            1,
        ),
        "recommendation_capped": (
            recommended_litres
            != gross_litres
        ),
    }