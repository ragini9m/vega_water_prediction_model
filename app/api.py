from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.model import run_irrigation_model
from app.open_meteo import (
    WeatherServiceError,
    fetch_open_meteo_weather,
)
from app.schemas import (
    IrrigationRequest,
    IrrigationResponse,
    LivePredictionRequest,
    WeatherInput,
    WeatherPreviewRequest,
)


app = FastAPI(
    title="VEGA Urban Tree Water Model",
    version="0.1.0",
    description=(
        "FAO-56 and FDR-based urban-tree "
        "watering recommendation API."
    ),
)

DATA_PATH = Path("data/predictions.csv")


def save_prediction(
    result: IrrigationResponse,
) -> None:
    DATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = DATA_PATH.exists()

    with DATA_PATH.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "tree_id",
                "timestamp",
                "eto_mm_day",
                "tree_et_mm_day",
                "current_vwc",
                "predicted_vwc_24h",
                "refill_threshold_vwc",
                "target_vwc",
                "critical_vwc",
                "effective_rain_forecast_mm",
                "expected_rain_litres",
                "water_deficit_litres",
                "calculated_gross_litres",
                "recommended_litres",
                "recommendation_capped",
                "predicted_drainage_mm",
                "decision",
                "priority_score",
                "data_quality",
            ],
        )

        if not file_exists:
            writer.writeheader()

        row = result.model_dump()
        row.pop("explanation", None)
        writer.writerow(row)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/predict",
    response_model=IrrigationResponse,
)
def predict(
    request: IrrigationRequest,
) -> IrrigationResponse:
    result = run_irrigation_model(request)
    save_prediction(result)
    return result

@app.post(
    "/predict-live",
    response_model=IrrigationResponse,
)
async def predict_live(
    request: LivePredictionRequest,
) -> IrrigationResponse:
    try:
        weather = await fetch_open_meteo_weather(
            latitude=request.latitude,
            longitude=request.longitude,
            timezone_name=request.timezone,
        )

    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    model_request = IrrigationRequest(
        tree=request.tree,
        sensor=request.sensor,
        weather=weather,
    )

    prediction = run_irrigation_model(
        model_request,
    )

    # Keep your existing persistence call here, when present.
    # save_prediction(prediction)

    return prediction

@app.post(
    "/weather-preview",
    response_model=WeatherInput,
)
async def weather_preview(
    request: WeatherPreviewRequest,
) -> WeatherInput:
    try:
        return await fetch_open_meteo_weather(
            latitude=request.latitude,
            longitude=request.longitude,
            timezone_name=request.timezone,
        )

    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc