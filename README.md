# VEGA Smart Watering Model

A Python and FastAPI-based decision-support system for urban-tree irrigation.

The model combines:

* Calibrated soil-moisture sensor readings
* Tree and soil configuration
* Real weather forecasts from Open-Meteo
* Reference evapotranspiration
* A root-zone water-balance calculation
* Rule-based irrigation decisions

The current implementation is a transparent physical water-balance model. It is not yet a trained machine-learning model.

## Project Overview

The application estimates whether an urban tree needs irrigation and, when required, recommends an approximate watering volume.

The live workflow is:

```text
Tree configuration
        +
Calibrated soil-moisture reading
        +
Tree latitude and longitude
        ↓
Open-Meteo forecast API
        ↓
Temperature, humidity, wind, pressure,
radiation, precipitation and FAO ET₀
        ↓
24-hour root-zone water-balance forecast
        ↓
Predicted soil moisture
        ↓
Irrigation decision and recommended litres
```

The current soil-moisture reading is treated as the present soil state. Historical rainfall and irrigation are not added to that reading again, which prevents double-counting.

## Main Features

* FastAPI prediction API
* Live weather retrieval from Open-Meteo
* Manual-weather prediction endpoint
* Calibrated volumetric water-content input
* Reference evapotranspiration support
* Tree/site evapotranspiration estimate
* Forecast rainfall adjustment
* Root-zone storage forecast
* Water-deficit calculation
* Irrigation-efficiency correction
* Minimum and maximum watering limits
* Sensor-health handling
* Automated tests with pytest
* CSV prediction logging

## Project Structure

```text
vega-water-model/
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── decision.py
│   ├── eto.py
│   ├── model.py
│   ├── open_meteo.py
│   ├── schemas.py
│   └── water_balance.py
├── data/
│   └── predictions.csv
├── tests/
│   └── test_model.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

* Python 3.9 or newer
* pip
* Internet access for live Open-Meteo forecasts
* A calibrated soil-moisture reading
* A virtual environment is recommended

## Installation

Clone the repository:

```bash
git clone https://github.com/ragini9m/vega_water_prediction_model.git
cd vega_water_prediction_model
```

Create a virtual environment.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

The main dependencies include:

```text
fastapi
uvicorn
pydantic
httpx
pytest
```

## Running the Tests

Run:

```bash
python -m pytest -v
```

A successful test run should show:

```text
4 passed
```

## Running the API

Start the FastAPI development server:

```bash
python -m uvicorn app.api:app --reload
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### `POST /predict`

Runs the irrigation model using manually supplied weather data.

This endpoint is useful for:

* Testing
* Offline operation
* Historical experiments
* Comparing external weather sources

### `POST /weather-preview`

Fetches and aggregates the upcoming Open-Meteo weather forecast without running the irrigation model.

Example request:

```json
{
  "latitude": 50.7374,
  "longitude": 7.0982,
  "timezone": "auto"
}
```

### `POST /predict-live`

Fetches real forecast data from Open-Meteo and runs the irrigation model automatically.

The caller supplies:

* Tree and soil configuration
* Current sensor reading
* Latitude
* Longitude

The caller does not need to manually supply temperature, humidity, wind, pressure, forecast rain or reference ET.

## Data That Must Be Prepared

The required data is divided into four categories:

1. Tree and site configuration
2. Soil configuration
3. Sensor data
4. Location data

Weather data is obtained automatically from Open-Meteo when `/predict-live` is used.

## 1. Tree and Site Configuration

These values are relatively stable and should normally be stored once for each tree.

| Field               | Meaning                                                  |             Unit or type | Typical source                       |
| ------------------- | -------------------------------------------------------- | -----------------------: | ------------------------------------ |
| `tree_id`           | Unique tree identifier                                   |                     text | Asset-management system              |
| `species`           | Tree species                                             |                     text | Tree survey                          |
| `age_category`      | Establishment category                                   | `new`, `young`, `mature` | Planting records or inspection       |
| `effective_depth_m` | Effective soil depth represented by the model and sensor |                        m | Site measurement or initial estimate |
| `irrigated_area_m2` | Soil area that receives irrigation                       |                       m² | Basin or wetted-area measurement     |
| `minimum_litres`    | Minimum practical watering event                         |                        L | Irrigation-system setting            |
| `maximum_litres`    | Maximum permitted watering event                         |                        L | Operational or safety setting        |

Example:

```json
{
  "tree_id": "TREE-001",
  "species": "Acer platanoides",
  "age_category": "young",
  "effective_depth_m": 0.3,
  "irrigated_area_m2": 2.0,
  "minimum_litres": 5.0,
  "maximum_litres": 50.0
}
```

## 2. Soil and Irrigation Configuration

These values must be measured, estimated or calibrated for the installation.

| Field                            | Meaning                                                                            | Range or unit | How to prepare                         |
| -------------------------------- | ---------------------------------------------------------------------------------- | ------------: | -------------------------------------- |
| `field_capacity_vwc`             | Soil moisture after saturation and drainage                                        |           0–1 | Field calibration                      |
| `wilting_point_vwc`              | Approximate lower plant-available-water limit                                      |           0–1 | Laboratory test, database or estimate  |
| `target_vwc`                     | Desired moisture after irrigation                                                  |           0–1 | Operational target                     |
| `critical_vwc`                   | Emergency irrigation threshold                                                     |           0–1 | Operational threshold                  |
| `allowable_depletion`            | Allowed depletion before refill                                                    |           0–1 | Initial setting and later calibration  |
| `site_adjusted_tree_coefficient` | Converts reference ET into tree/site ET                                            |    multiplier | Initial estimate and later calibration |
| `rainfall_capture_efficiency`    | Fraction of forecast rain entering the modelled root zone                          |           0–1 | Surface and runoff assessment          |
| `irrigation_efficiency`          | Fraction of applied irrigation reaching the modelled soil zone                     |           0–1 | Irrigation-system assessment           |
| `rain_replacement_fraction`      | Required fraction of the deficit that rain must replace before watering is delayed |           0–1 | Operational policy                     |

The required threshold order is:

```text
wilting_point_vwc
    <= critical_vwc
    <= target_vwc
    <= field_capacity_vwc
```

Example initial configuration:

```json
{
  "field_capacity_vwc": 0.30,
  "wilting_point_vwc": 0.12,
  "target_vwc": 0.26,
  "critical_vwc": 0.15,
  "allowable_depletion": 0.40,
  "site_adjusted_tree_coefficient": 0.65,
  "rainfall_capture_efficiency": 0.70,
  "irrigation_efficiency": 0.80,
  "rain_replacement_fraction": 0.70
}
```

These are example starting values only. They are not universal values for every tree or soil.

## 3. Sensor Data

The model expects calibrated volumetric water content, not a raw ADC, voltage, frequency or capacitance value.

| Field                | Meaning                             |         Unit or type | Required |
| -------------------- | ----------------------------------- | -------------------: | -------- |
| `timestamp`          | Time of the sensor measurement      |    ISO 8601 datetime | Yes      |
| `soil_vwc`           | Calibrated volumetric water content | fraction from 0 to 1 | Yes      |
| `soil_temperature_c` | Soil temperature                    |                   °C | Optional |
| `sensor_status`      | Sensor condition                    |          status text | Yes      |

Supported sensor statuses:

```text
OK
NOISY
STALE
FAILED
UNCALIBRATED
```

Example:

```json
{
  "timestamp": "2026-06-27T16:00:00Z",
  "soil_vwc": 0.19,
  "soil_temperature_c": 23.4,
  "sensor_status": "OK"
}
```

For a moisture value of 19%, send:

```json
{
  "soil_vwc": 0.19
}
```

Do not send:

```json
{
  "soil_vwc": 19
}
```

## Sensor Calibration Requirement

A capacitive soil-moisture sensor normally produces a raw signal such as:

```text
ADC count
voltage
frequency
capacitance
```

A calibration function must convert the raw value into VWC:

```text
Raw sensor value
        ↓
Soil-specific calibration equation
        ↓
Calibrated VWC from 0 to 1
```

The sensor should be calibrated in the target soil because soil texture, salinity, density, temperature and installation quality can affect the output.

## 4. Location Data

Open-Meteo requires the tree location.

| Field       | Meaning                     |            Unit |
| ----------- | --------------------------- | --------------: |
| `latitude`  | Tree latitude               | decimal degrees |
| `longitude` | Tree longitude              | decimal degrees |
| `timezone`  | Forecast timezone selection | normally `auto` |

Example for Bonn:

```json
{
  "latitude": 50.7374,
  "longitude": 7.0982,
  "timezone": "auto"
}
```

## Data Retrieved Automatically from Open-Meteo

When `/predict-live` is used, the application requests hourly forecast data and aggregates the upcoming forecast period.

| Application variable         | Open-Meteo variable          |
| ---------------------------- | ---------------------------- |
| Air temperature              | `temperature_2m`             |
| Relative humidity            | `relative_humidity_2m`       |
| Wind speed                   | `wind_speed_10m`             |
| Atmospheric pressure         | `surface_pressure`           |
| Forecast precipitation       | `precipitation`              |
| Shortwave radiation          | `shortwave_radiation`        |
| Reference evapotranspiration | `et0_fao_evapotranspiration` |

The application derives approximately 24-hour values for:

```text
mean_temperature_c
relative_humidity_percent
wind_speed_m_s
atmospheric_pressure_kpa
rainfall_forecast_24h_mm
shortwave_radiation_mj_m2_day
eto_forecast_24h_mm
```

## Complete Live Prediction Request

Example request to `POST /predict-live`:

```json
{
  "tree": {
    "tree_id": "TREE-001",
    "species": "Acer platanoides",
    "age_category": "young",
    "effective_depth_m": 0.3,
    "irrigated_area_m2": 2.0,
    "field_capacity_vwc": 0.30,
    "wilting_point_vwc": 0.12,
    "target_vwc": 0.26,
    "critical_vwc": 0.15,
    "allowable_depletion": 0.40,
    "site_adjusted_tree_coefficient": 0.65,
    "rainfall_capture_efficiency": 0.70,
    "irrigation_efficiency": 0.80,
    "rain_replacement_fraction": 0.70,
    "minimum_litres": 5.0,
    "maximum_litres": 50.0
  },
  "sensor": {
    "timestamp": "2026-06-27T16:00:00Z",
    "soil_vwc": 0.19,
    "soil_temperature_c": 23.4,
    "sensor_status": "OK"
  },
  "latitude": 50.7374,
  "longitude": 7.0982,
  "timezone": "auto"
}
```

## Values That Change During Operation

These values are variable and should be updated regularly:

| Value                | Source               | Suggested update frequency              |
| -------------------- | -------------------- | --------------------------------------- |
| `soil_vwc`           | Soil-moisture sensor | Hourly or several times daily           |
| `soil_temperature_c` | Soil sensor          | With each sensor reading                |
| `sensor_status`      | Sensor diagnostics   | With each reading                       |
| Weather forecast     | Open-Meteo           | Every prediction or cached periodically |
| Forecast rainfall    | Open-Meteo           | Every prediction                        |
| Forecast ET₀         | Open-Meteo           | Every prediction                        |

## Values That Normally Remain Fixed

These values are configured per tree or installation and only change after calibration, inspection or system changes:

```text
tree_id
species
age_category
latitude
longitude
effective_depth_m
irrigated_area_m2
field_capacity_vwc
wilting_point_vwc
target_vwc
critical_vwc
allowable_depletion
site_adjusted_tree_coefficient
rainfall_capture_efficiency
irrigation_efficiency
rain_replacement_fraction
minimum_litres
maximum_litres
```

## Values Calculated by the Model

The following values are calculated automatically:

| Output                       | Meaning                                               |
| ---------------------------- | ----------------------------------------------------- |
| `eto_mm_day`                 | Reference evapotranspiration                          |
| `tree_et_mm_day`             | Estimated tree/site water use                         |
| `current_vwc`                | Current measured VWC                                  |
| `predicted_vwc_24h`          | Predicted VWC after the forecast period               |
| `refill_threshold_vwc`       | Moisture threshold used for irrigation decisions      |
| `effective_rain_forecast_mm` | Forecast rain after capture losses                    |
| `expected_rain_litres`       | Useful rainfall over the irrigated area               |
| `water_deficit_litres`       | Net amount needed to reach target VWC                 |
| `calculated_gross_litres`    | Water required after irrigation-efficiency losses     |
| `recommended_litres`         | Final operational recommendation                      |
| `recommendation_capped`      | Whether minimum or maximum limits affected the result |
| `predicted_drainage_mm`      | Estimated storage above field capacity                |
| `decision`                   | Irrigation action                                     |
| `priority_score`             | Operational urgency                                   |
| `data_quality`               | Sensor-data reliability category                      |

## Irrigation Decisions

The model can return:

### `NO_WATER_NEEDED`

Current moisture is at or above the target.

### `MONITOR`

Moisture is below target but is not expected to cross the refill threshold within the forecast period.

### `WAIT_FOR_RAIN`

Forecast useful rain is expected to replace a sufficient fraction of the calculated soil-water deficit.

### `WATER_WITHIN_24H`

Predicted moisture is expected to fall below the refill threshold.

### `WATER_NOW`

Current moisture is at or below the critical threshold.

### `SENSOR_INSPECTION_REQUIRED`

The sensor is failed or uncalibrated, so the watering recommendation should not be trusted.

## Water-Balance Logic

The current sensor measurement is used as the present soil-water state:

```text
Current measured root-zone storage
- forecast tree/site evapotranspiration
+ effective forecast rainfall
= predicted future storage
```

The model then converts predicted storage back into VWC.

The current sensor value already reflects previous rainfall, irrigation and water losses. Therefore, previous events are not added again to the current state.

## Data Collection Sheet

For each tree, prepare a table with these columns:

```text
tree_id
species
age_category
latitude
longitude
effective_depth_m
irrigated_area_m2
field_capacity_vwc
wilting_point_vwc
target_vwc
critical_vwc
allowable_depletion
site_adjusted_tree_coefficient
rainfall_capture_efficiency
irrigation_efficiency
rain_replacement_fraction
minimum_litres
maximum_litres
sensor_id
installation_date
last_calibration_date
```

## Sensor History

Store ongoing sensor records with:

```text
tree_id
sensor_id
timestamp
raw_sensor_value
soil_vwc
soil_temperature_c
sensor_status
battery_voltage
```

## Irrigation History

Store every irrigation event for validation and future calibration:

```text
tree_id
timestamp
applied_litres
irrigation_duration_minutes
water_source
operator
```

Historical irrigation is useful for model evaluation, but it is not added directly to the current sensor VWC.

## Prediction Output

Predictions may be stored in:

```text
data/predictions.csv
```

The output may include:

```text
tree_id
timestamp
eto_mm_day
tree_et_mm_day
current_vwc
predicted_vwc_24h
refill_threshold_vwc
target_vwc
critical_vwc
effective_rain_forecast_mm
expected_rain_litres
water_deficit_litres
calculated_gross_litres
recommended_litres
recommendation_capped
predicted_drainage_mm
decision
priority_score
data_quality
```

## Validation

The model should be validated using real field measurements.

For each prediction, record:

```text
prediction timestamp
predicted VWC after 24 hours
observed VWC after 24 hours
forecast rainfall
observed rainfall
recommended litres
actual applied litres
sensor status
```

Recommended evaluation measures include:

* Mean absolute error of predicted VWC
* Mean prediction bias
* Error during dry periods
* Error during rainfall
* Error after irrigation
* Percentage of correct irrigation decisions

Machine learning may later be added to correct systematic residual errors after enough validated field data has been collected.

## Current Limitations

* Tree and soil parameters require local calibration.
* A single VWC sensor may not represent the entire root zone.
* Surface runoff and deep drainage are simplified.
* Forecast accuracy depends on the weather provider.
* The model currently uses an aggregated forecast period.
* Sensor calibration errors directly affect the result.
* The current system is a physical decision model, not a trained ML model.
* Recommended litres should be field-tested before fully automated irrigation.

## Technologies Used

* Python
* FastAPI
* Pydantic
* HTTPX
* Open-Meteo
* pytest
* Uvicorn
* CSV-based prediction storage

## Future Improvements

* Store tree configuration in a database
* Accept only `tree_id` and sensor data at prediction time
* Connect directly to the physical sensor network
* Add sensor calibration management
* Add local rain-gauge observations
* Add irrigation-controller integration
* Add database-based sensor and prediction history
* Add forecast caching and retry handling
* Add multiple sensor depths
* Add dashboards and map visualization
* Add automated field-validation reports
* Add machine-learning residual correction after sufficient data collection
* Add authentication and API access control

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a new branch:

```bash
git checkout -b feature/your-feature-name
```

3. Commit the changes:

```bash
git commit -m "Add new feature"
```

4. Push the branch:

```bash
git push origin feature/your-feature-name
```

5. Open a pull request.

## Author

**Ragini**

GitHub: [ragini9m](https://github.com/ragini9m)

## License

This project is currently provided for educational, research and development purposes.

Add an appropriate license file before distributing or reusing the project publicly.
