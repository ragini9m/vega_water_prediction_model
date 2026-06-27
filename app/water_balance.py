from __future__ import annotations


def vwc_to_storage_mm(
    volumetric_water_content: float,
    root_depth_m: float,
) -> float:
    """
    Convert volumetric water content to equivalent
    water depth in the root zone.

    Example:
        0.20 VWC × 0.30 m × 1000 = 60 mm
    """
    return (
        volumetric_water_content
        * root_depth_m
        * 1000.0
    )


def storage_mm_to_vwc(
    storage_mm: float,
    root_depth_m: float,
) -> float:
    if root_depth_m <= 0:
        raise ValueError(
            "Root depth must be greater than zero."
        )

    return storage_mm / (
        root_depth_m * 1000.0
    )


def calculate_refill_threshold(
    field_capacity_vwc: float,
    wilting_point_vwc: float,
    allowable_depletion: float,
) -> float:
    """
    Refill threshold based on allowable depletion.
    """
    return field_capacity_vwc - (
        allowable_depletion
        * (
            field_capacity_vwc
            - wilting_point_vwc
        )
    )


def calculate_tree_et(
    eto_mm_day: float,
    tree_coefficient: float,
) -> float:
    return max(
        0.0,
        eto_mm_day * tree_coefficient,
    )


def litres_to_mm(
    litres: float,
    area_m2: float,
) -> float:
    """
    One litre over one square metre equals one millimetre.
    """
    if area_m2 <= 0:
        raise ValueError(
            "Area must be greater than zero."
        )

    return litres / area_m2


def update_storage(
    current_storage_mm: float,
    tree_et_mm: float,
    rainfall_mm: float,
    irrigation_mm: float,
    rainfall_efficiency: float,
    irrigation_efficiency: float,
) -> float:
    effective_rain = (
        max(0.0, rainfall_mm)
        * rainfall_efficiency
    )

    effective_irrigation = (
        max(0.0, irrigation_mm)
        * irrigation_efficiency
    )

    updated = (
        current_storage_mm
        - tree_et_mm
        + effective_rain
        + effective_irrigation
    )

    return max(0.0, updated)


def fuse_sensor_and_model(
    sensor_storage_mm: float,
    model_storage_mm: float,
    sensor_quality: float,
) -> float:
    """
    Use up to 80% sensor weight for a high-quality sensor.
    """
    quality = min(
        1.0,
        max(0.0, sensor_quality),
    )

    sensor_weight = 0.8 * quality
    model_weight = 1.0 - sensor_weight

    return (
        sensor_weight * sensor_storage_mm
        + model_weight * model_storage_mm
    )


def calculate_required_litres(
    current_vwc: float,
    target_vwc: float,
    root_depth_m: float,
    irrigated_area_m2: float,
    irrigation_efficiency: float,
    minimum_litres: float,
    maximum_litres: float,
) -> float:
    if current_vwc >= target_vwc:
        return 0.0

    net_litres = (
        (target_vwc - current_vwc)
        * root_depth_m
        * irrigated_area_m2
        * 1000.0
    )

    gross_litres = (
        net_litres / irrigation_efficiency
    )

    bounded_litres = min(
        maximum_litres,
        max(minimum_litres, gross_litres),
    )

    return round(bounded_litres, 1)