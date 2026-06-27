'''
FAO-56 Penman–Monteith equation.
result represents the environmental drying demand in:mm of water per day
'''

from __future__ import annotations

from math import exp

from app.schemas import WeatherInput


def saturation_vapour_pressure(temp_c: float) -> float:
    """
    Saturation vapour pressure in kPa.
    """
    return 0.6108 * exp(
        (17.27 * temp_c) / (temp_c + 237.3)
    )


def vapour_pressure_curve_slope(temp_c: float) -> float:
    """
    Slope of saturation vapour pressure curve,
    expressed in kPa/°C.
    """
    es = saturation_vapour_pressure(temp_c)

    return (
        4098.0 * es
        / ((temp_c + 237.3) ** 2)
    )


def psychrometric_constant(
    atmospheric_pressure_kpa: float,
) -> float:
    """
    Psychrometric constant in kPa/°C.
    """
    return 0.000665 * atmospheric_pressure_kpa

def calculate_eto(
    weather: WeatherInput,
) -> float:
    if weather.eto_forecast_24h_mm is not None:
        return weather.eto_forecast_24h_mm
    """
    Simplified daily FAO-56 Penman-Monteith calculation.

    Returns:
        Reference evapotranspiration in mm/day.

    Note:
        This MVP uses mean temperature and mean relative humidity.
        A later version should use Tmin, Tmax, RHmin and RHmax.
    """
    temperature = weather.mean_temperature_c
    humidity = weather.relative_humidity_percent
    wind = weather.wind_speed_m_s

    es = saturation_vapour_pressure(temperature)
    ea = es * humidity / 100.0

    delta = vapour_pressure_curve_slope(temperature)
    gamma = psychrometric_constant(
        weather.atmospheric_pressure_kpa
    )

    radiation_component = (
        0.408
        * delta
        * (
            weather.net_radiation_mj_m2_day
            - weather.soil_heat_flux_mj_m2_day
        )
    )

    aerodynamic_component = (
        gamma
        * (900.0 / (temperature + 273.0))
        * wind
        * (es - ea)
    )

    denominator = (
        delta
        + gamma * (1.0 + 0.34 * wind)
    )

    if denominator <= 0:
        raise ValueError(
            "Invalid FAO-56 calculation denominator."
        )

    eto = (
        radiation_component
        + aerodynamic_component
    ) / denominator

    return max(0.0, eto)