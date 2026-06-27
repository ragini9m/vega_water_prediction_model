from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI

from app.model import run_irrigation_model
from app.schemas import (
    IrrigationRequest,
    IrrigationResponse,
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