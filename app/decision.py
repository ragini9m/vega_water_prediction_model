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


def choose_decision(
    current_vwc: float,
    predicted_vwc_24h: float,
    target_vwc: float,
    refill_threshold_vwc: float,
    critical_vwc: float,
    sensor_status: str,
    recommended_litres: float,
    water_deficit_litres: float,
    expected_rain_litres: float,
    rain_replacement_fraction: float = 0.70,
) -> tuple[str, float, int, list[str]]:
    reasons: list[str] = []

    if sensor_status == "FAILED":
        return (
            "SENSOR_INSPECTION_REQUIRED",
            0.0,
            20,
            [
                "The soil-moisture sensor is marked as failed.",
                "A watering decision was not issued.",
            ],
        )

    if sensor_status == "UNCALIBRATED":
        return (
            "SENSOR_INSPECTION_REQUIRED",
            0.0,
            25,
            [
                "The soil-moisture sensor is not calibrated.",
                "Calibrated VWC is required before using the result.",
            ],
        )

    if current_vwc >= target_vwc:
        return (
            "NO_WATER_NEEDED",
            0.0,
            10,
            [
                "Current moisture is at or above the target value."
            ],
        )

    rain_can_replace_deficit = (
        water_deficit_litres > 0
        and expected_rain_litres
        >= (
            rain_replacement_fraction
            * water_deficit_litres
        )
    )

    if (
        rain_can_replace_deficit
        and current_vwc > critical_vwc
    ):
        replacement_percent = (
            expected_rain_litres
            / water_deficit_litres
            * 100.0
        )

        return (
            "WAIT_FOR_RAIN",
            0.0,
            35,
            [
                "Forecast rainfall may replace a meaningful "
                "part of the calculated soil-water deficit.",
                (
                    "Expected useful rainfall is approximately "
                    f"{replacement_percent:.0f}% of the deficit."
                ),
            ],
        )

    if current_vwc <= critical_vwc:
        return (
            "WATER_NOW",
            recommended_litres,
            95,
            [
                "Current moisture is at or below the "
                "critical threshold.",
                "Immediate watering is recommended.",
            ],
        )

    if predicted_vwc_24h <= refill_threshold_vwc:
        deficit_range = max(
            refill_threshold_vwc - critical_vwc,
            0.001,
        )

        forecast_severity = (
            refill_threshold_vwc
            - predicted_vwc_24h
        ) / deficit_range

        forecast_severity = max(
            0.0,
            min(1.0, forecast_severity),
        )

        priority = round(
            70 + 20 * forecast_severity
        )

        return (
            "WATER_WITHIN_24H",
            recommended_litres,
            priority,
            [
                "Predicted moisture is expected to fall below "
                "the refill threshold within 24 hours.",
                "Preventive watering is recommended.",
            ],
        )

    return (
        "MONITOR",
        0.0,
        40,
        [
            "Moisture is below the target but is not expected "
            "to reach the refill threshold within 24 hours."
        ],
    )