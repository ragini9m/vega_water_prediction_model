from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

import httpx

from app.schemas import WeatherInput


OPEN_METEO_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


class WeatherServiceError(RuntimeError):
    """Raised when live weather data cannot be retrieved."""


def _require_list(
    hourly: dict[str, Any],
    key: str,
) -> list:
    value = hourly.get(key)

    if not isinstance(value, list):
        raise WeatherServiceError(
            f"Open-Meteo response is missing hourly '{key}'."
        )

    return value


def _parse_open_meteo_time(
    value: str,
) -> datetime:
    """
    Open-Meteo returns local ISO timestamps without an explicit
    UTC offset when a location timezone is requested.

    For selecting a continuous 24-hour block, parsing them as
    naive datetimes is sufficient because all timestamps in the
    response use the same location timezone.
    """
    return datetime.fromisoformat(value)


def _sum_numeric(
    values: list[float | int | None],
) -> float:
    return sum(
        float(value)
        for value in values
        if value is not None
    )


def _mean_numeric(
    values: list[float | int | None],
    variable_name: str,
) -> float:
    valid_values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not valid_values:
        raise WeatherServiceError(
            f"No valid values found for {variable_name}."
        )

    return mean(valid_values)


def _select_next_24_hours(
    hourly: dict[str, Any],
) -> dict[str, list]:
    times = _require_list(hourly, "time")

    if not times:
        raise WeatherServiceError(
            "Open-Meteo returned no hourly timestamps."
        )

    parsed_times = [
        _parse_open_meteo_time(value)
        for value in times
    ]

    now_local = parsed_times[0]

    current_time_text = hourly.get(
        "_current_time",
    )

    if isinstance(current_time_text, str):
        current_time = _parse_open_meteo_time(
            current_time_text,
        )
    else:
        current_time = now_local

    start_index = 0

    for index, forecast_time in enumerate(parsed_times):
        if forecast_time >= current_time:
            start_index = index
            break

    end_index = min(
        start_index + 24,
        len(times),
    )

    if end_index - start_index < 20:
        raise WeatherServiceError(
            "Open-Meteo did not return enough hourly values "
            "for a 24-hour prediction."
        )

    selected: dict[str, list] = {}

    for key, values in hourly.items():
        if key.startswith("_"):
            continue

        if isinstance(values, list):
            selected[key] = values[
                start_index:end_index
            ]

    return selected


async def fetch_open_meteo_weather(
    latitude: float,
    longitude: float,
    timezone_name: str = "auto",
) -> WeatherInput:
    """
    Fetch and aggregate the next 24 hours of Open-Meteo data.
    """
    hourly_variables = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "surface_pressure",
        "precipitation",
        "shortwave_radiation",
        "et0_fao_evapotranspiration",
    ]

    parameters = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(hourly_variables),
        "current": "temperature_2m",
        "timezone": timezone_name,
        "forecast_days": 2,
        "wind_speed_unit": "ms",
    }

    timeout = httpx.Timeout(
        connect=5.0,
        read=15.0,
        write=5.0,
        pool=5.0,
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
        ) as client:
            response = await client.get(
                OPEN_METEO_FORECAST_URL,
                params=parameters,
            )

            response.raise_for_status()
            payload = response.json()

    except httpx.TimeoutException as exc:
        raise WeatherServiceError(
            "Open-Meteo request timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise WeatherServiceError(
            "Open-Meteo returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:
        raise WeatherServiceError(
            f"Could not connect to Open-Meteo: {exc}"
        ) from exc

    except ValueError as exc:
        raise WeatherServiceError(
            "Open-Meteo returned invalid JSON."
        ) from exc

    hourly = payload.get("hourly")

    if not isinstance(hourly, dict):
        raise WeatherServiceError(
            "Open-Meteo response does not contain hourly data."
        )

    current = payload.get("current", {})

    if isinstance(current, dict):
        hourly["_current_time"] = current.get("time")

    selected = _select_next_24_hours(hourly)

    temperatures = _require_list(
        selected,
        "temperature_2m",
    )

    humidities = _require_list(
        selected,
        "relative_humidity_2m",
    )

    wind_speeds = _require_list(
        selected,
        "wind_speed_10m",
    )

    pressures = _require_list(
        selected,
        "surface_pressure",
    )

    precipitation = _require_list(
        selected,
        "precipitation",
    )

    shortwave_radiation = _require_list(
        selected,
        "shortwave_radiation",
    )

    hourly_eto = _require_list(
        selected,
        "et0_fao_evapotranspiration",
    )

    selected_times = _require_list(
        selected,
        "time",
    )

    # Hourly shortwave radiation is W/m².
    # Each hourly value represents energy over one hour:
    # W/m² × 3600 seconds ÷ 1,000,000 = MJ/m².
    shortwave_radiation_mj_m2 = (
        _sum_numeric(shortwave_radiation)
        * 3600.0
        / 1_000_000.0
    )

    weather_timestamp = datetime.now(timezone.utc)

    if selected_times:
        try:
            parsed = datetime.fromisoformat(
                selected_times[0],
            )

            if parsed.tzinfo is not None:
                weather_timestamp = parsed.astimezone(
                    timezone.utc,
                )
        except ValueError:
            pass

    return WeatherInput(
        timestamp=weather_timestamp,

        mean_temperature_c=_mean_numeric(
            temperatures,
            "temperature_2m",
        ),

        relative_humidity_percent=_mean_numeric(
            humidities,
            "relative_humidity_2m",
        ),

        wind_speed_m_s=_mean_numeric(
            wind_speeds,
            "wind_speed_10m",
        ),

        # Open-Meteo supplies shortwave radiation, not
        # complete net radiation. Do not mislabel it.
        net_radiation_mj_m2_day=0.0,

        shortwave_radiation_mj_m2_day=(
            shortwave_radiation_mj_m2
        ),

        soil_heat_flux_mj_m2_day=0.0,

        atmospheric_pressure_kpa=(
            _mean_numeric(
                pressures,
                "surface_pressure",
            )
            / 10.0
        ),

        rainfall_previous_24h_mm=0.0,

        rainfall_forecast_24h_mm=(
            _sum_numeric(precipitation)
        ),

        eto_forecast_24h_mm=(
            _sum_numeric(hourly_eto)
        ),

        weather_source="open-meteo",
    )