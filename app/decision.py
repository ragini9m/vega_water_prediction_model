'''
converts the calculated numbers into a useful action and creates the priority score.
NO_WATER_NEEDED
MONITOR
WAIT_FOR_RAIN
WATER_WITHIN_24H
WATER_NOW
SENSOR_INSPECTION_REQUIRED 
''' 

from __future__ import annotations


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def calculate_priority_score(
    current_vwc: float,
    predicted_vwc_24h: float,
    refill_threshold_vwc: float,
    critical_vwc: float,
    heat_factor: float,
    vulnerability_factor: float,
) -> int:
    denominator = max(
        refill_threshold_vwc - critical_vwc,
        0.001,
    )

    current_deficit = clamp(
        (
            refill_threshold_vwc
            - current_vwc
        ) / denominator
    )

    forecast_deficit = clamp(
        (
            refill_threshold_vwc
            - predicted_vwc_24h
        ) / denominator
    )

    score = 100.0 * (
        0.45 * current_deficit
        + 0.30 * forecast_deficit
        + 0.15 * clamp(vulnerability_factor)
        + 0.10 * clamp(heat_factor)
    )

    return round(clamp(score / 100.0) * 100)


def choose_decision(
    current_vwc: float,
    predicted_vwc_24h: float,
    target_vwc: float,
    refill_threshold_vwc: float,
    critical_vwc: float,
    effective_forecast_rain_mm: float,
    sensor_status: str,
    recommended_litres: float,
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []

    if sensor_status == "FAILED":
        return (
            "SENSOR_INSPECTION_REQUIRED",
            0.0,
            [
                "The moisture sensor is marked as failed.",
                "The model should not issue a high-confidence "
                "watering instruction without a valid sensor.",
            ],
        )

    if current_vwc >= target_vwc:
        reasons.append(
            "Current root-zone moisture is at or above target."
        )
        return "NO_WATER_NEEDED", 0.0, reasons

    if (
        effective_forecast_rain_mm >= 5.0
        and current_vwc > critical_vwc
    ):
        reasons.extend(
            [
                "Useful rainfall is forecast.",
                "Current moisture is not yet critical.",
            ]
        )
        return "WAIT_FOR_RAIN", 0.0, reasons

    if current_vwc <= critical_vwc:
        reasons.extend(
            [
                "Current moisture is at or below "
                "the critical threshold.",
                "Immediate watering is recommended.",
            ]
        )
        return (
            "WATER_NOW",
            recommended_litres,
            reasons,
        )

    if predicted_vwc_24h <= refill_threshold_vwc:
        reasons.extend(
            [
                "Predicted moisture will be below "
                "the refill threshold within 24 hours.",
                "Preventive watering is recommended.",
            ]
        )
        return (
            "WATER_WITHIN_24H",
            recommended_litres,
            reasons,
        )

    reasons.append(
        "Moisture is below target but is not expected "
        "to reach the refill threshold within 24 hours."
    )

    return "MONITOR", 0.0, reasons