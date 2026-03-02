"""
forecast.py
───────────
24-hour power_total forecast using pre-trained XGBoost models.
Supports devices: e0202, e0207, e0211

Strategy:
  1. Fetch last 7 days of power_total at 15-min resolution from InfluxDB (chart history)
  2. Fetch last 25 hours for lag feature calculation
  3. Fetch latest electrical measurements (held constant across forecast horizon)
  4. Iteratively predict 96 steps (24h × 4/hr), feeding predictions back as lag inputs
  5. Return historical + forecast arrays + summary
"""

import os
import math
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

_URL    = os.getenv("INFLUX_URL")
_TOKEN  = os.getenv("INFLUX_TOKEN")
_ORG    = os.getenv("INFLUX_ORG")
_BUCKET = os.getenv("INFLUX_BUCKET")

# Supported devices and their model paths
# Models are located in paraquet_data/models/saved/ at project root
# Path resolution: backend/routes/forecast.py -> .. -> .. -> .. = project_root
_FILE_PATH = Path(__file__).resolve()
PROJECT_ROOT = _FILE_PATH.parent.parent.parent  # up 3 levels from backend/routes/forecast.py
MODEL_DIR = PROJECT_ROOT / "paraquet_data" / "models" / "saved"

# Try multiple locations for models
MODEL_PATHS = [
    MODEL_DIR,
]

MODEL_BASE_PATH = None
for path in MODEL_PATHS:
    if path.exists() and (path / "raw_data_e0202_model.pkl").exists():
        MODEL_BASE_PATH = path
        break

if MODEL_BASE_PATH is None:
    # Final fallback to model dir if nothing else works
    MODEL_BASE_PATH = MODEL_DIR

FORECAST_DEVICES = {
    "e0202": str(MODEL_BASE_PATH / "raw_data_e0202_model.pkl"),
    "e0207": str(MODEL_BASE_PATH / "raw_data_e0207_model.pkl"),
    "e0211": str(MODEL_BASE_PATH / "raw_data_e0211_model.pkl"),
}

# Modal 'table' value observed across all training parquet files
_TABLE_DEFAULT = 1.5


def _get_client():
    return InfluxDBClient(url=_URL, token=_TOKEN, org=_ORG, timeout=30_000_000)


def _fetch_power_history(device_id: str, hours: int) -> pd.Series:
    """
    Returns a 15-min resampled Series of power_total for the last `hours` hours.
    Index is UTC datetime, values are kW.
    """
    client = _get_client()
    try:
        flux = f'''
        from(bucket: "{_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r._measurement == "wach_{device_id}_power_total")
          |> sort(columns: ["_time"])
        '''
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list):
            df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
        if df.empty:
            return pd.Series(dtype=float)

        df = df[["_time", "_value"]].copy()
        df["_time"] = pd.to_datetime(df["_time"], utc=True)
        df = df.set_index("_time")["_value"]
        df = df.resample("15min").mean().ffill()
        return df
    except Exception as e:
        print(f"[forecast] _fetch_power_history failed: {e}")
        return pd.Series(dtype=float)
    finally:
        client.close()


def _fetch_latest_electrical(device_id: str) -> dict:
    """
    Returns the most recent averaged values of the 7 electrical input features.
    Falls back to safe defaults if unavailable.
    """
    metrics = {
        "power_factor_avg": 0.85,
        "current_l1":       5.0,
        "current_l2":       5.0,
        "current_l3":       5.0,
        "volts_l1_n":       230.0,
        "volts_l2_n":       230.0,
        "volts_l3_n":       230.0,
    }

    client = _get_client()
    try:
        for metric, default in metrics.items():
            flux = f'''
            from(bucket: "{_BUCKET}")
              |> range(start: -2h)
              |> filter(fn: (r) => r._measurement == "wach_{device_id}_{metric}")
              |> mean()
            '''
            tables = client.query_api().query(flux)
            for table in tables:
                for record in table.records:
                    val = record.get_value()
                    if val is not None and not math.isnan(float(val)):
                        metrics[metric] = float(val)
    except Exception as e:
        print(f"[forecast] _fetch_latest_electrical failed: {e}")
    finally:
        client.close()

    return metrics


def _build_forecast(
    device_id: str,
    model,
    power_history: pd.Series,
    electrical: dict,
) -> list[dict]:
    """
    Iteratively predicts 96 timesteps (24 hours) using the XGBoost model.
    Returns a list of {"time": ISO string, "value": float} dicts.
    """
    # Work with a mutable list of (timestamp, value) for lag/rolling calculations
    hist_times = list(power_history.index)
    hist_values = list(power_history.values)

    if len(hist_values) < 97:
        raise ValueError(
            f"Not enough historical data for {device_id} — "
            f"need 97+ points at 15-min intervals, got {len(hist_values)}"
        )

    now = power_history.index[-1]
    predictions = []

    for step in range(96):
        next_time = now + timedelta(minutes=15 * (step + 1))

        # Lag features — look back into combined history + predictions so far
        combined = hist_values + [p["value"] for p in predictions]

        lag_1  = combined[-1]                  # 15 min ago
        lag_4  = combined[-4]  if len(combined) >= 4  else combined[0]   # 1h ago
        lag_96 = combined[-96] if len(combined) >= 96 else combined[0]   # 24h ago

        # Rolling features over last 4 values (1 hour)
        window = combined[-4:] if len(combined) >= 4 else combined
        rolling_mean = float(np.mean(window))
        rolling_std  = float(np.std(window)) if len(window) > 1 else 0.0

        # Time features
        local_time  = next_time  # UTC — adjust if local timezone needed
        hour        = local_time.hour
        dayofweek   = local_time.dayofweek
        month       = local_time.month
        is_weekend  = 1 if dayofweek >= 5 else 0

        row = {
            "result":                    0.0,
            "table":                     _TABLE_DEFAULT,
            "site":                      0.0,
            "power_factor_avg":          electrical["power_factor_avg"],
            "units":                     0.0,
            "current_l1":                electrical["current_l1"],
            "current_l2":                electrical["current_l2"],
            "current_l3":                electrical["current_l3"],
            "volts_l1_n":                electrical["volts_l1_n"],
            "volts_l2_n":                electrical["volts_l2_n"],
            "volts_l3_n":                electrical["volts_l3_n"],
            "hour":                      hour,
            "dayofweek":                 dayofweek,
            "month":                     month,
            "is_weekend":                is_weekend,
            "power_total_lag_1":         lag_1,
            "power_total_lag_4":         lag_4,
            "power_total_lag_96":        lag_96,
            "power_total_rolling_mean_4": rolling_mean,
            "power_total_rolling_std_4":  rolling_std,
        }

        input_df = pd.DataFrame([row])
        pred_value = float(model.predict(input_df)[0])
        pred_value = max(0.0, pred_value)  # clamp to non-negative

        predictions.append({
            "time":  next_time.isoformat(),
            "value": round(pred_value, 4),
        })

    return predictions


def _build_summary(
    device_id: str,
    forecast: list[dict],
    recent_avg: float,
) -> str:
    """
    Returns a plain-English summary with threshold alerts if forecast is anomalous.
    """
    values = [p["value"] for p in forecast]
    peak   = max(values)
    avg    = sum(values) / len(values)
    peak_time = forecast[values.index(peak)]["time"]

    # Parse peak time for readable label
    try:
        pt = datetime.fromisoformat(peak_time)
        peak_label = pt.strftime("%H:%M UTC")
    except Exception:
        peak_label = peak_time

    alert = ""
    if recent_avg > 0 and peak > recent_avg * 1.5:
        alert = (
            f" ⚠️ Forecast peak of {peak:.2f} kW at {peak_label} is more than 50% above "
            f"the recent 7-day average of {recent_avg:.2f} kW — this may indicate abnormal load. "
            f"Consider inspecting {device_id} before the predicted peak."
        )
    elif recent_avg > 0 and avg < recent_avg * 0.5:
        alert = (
            f" ℹ️ Forecast average of {avg:.2f} kW is significantly below the recent average of "
            f"{recent_avg:.2f} kW — this may indicate reduced occupancy or a sensor issue."
        )

    return (
        f"24-hour power forecast for {device_id}: predicted average {avg:.2f} kW, "
        f"peak {peak:.2f} kW at {peak_label}.{alert}"
    )


@router.get("/forecast/{device_id}")
async def get_forecast(device_id: str):
    """
    Returns 7-day historical power_total + 24-hour forecast for a supported device.
    """
    if device_id not in FORECAST_DEVICES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Forecast is only available for: {', '.join(FORECAST_DEVICES.keys())}",
                "suggestion": "Try one of: e0202, e0207, e0211",
            }
        )

    model_path = FORECAST_DEVICES[device_id]
    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=500,
            detail={"error": f"Model file not found: {model_path}"}
        )

    # 1. Load model
    try:
        model = joblib.load(model_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Failed to load model: {e}"})

    # 2. Fetch 7 days of history for chart
    history_7d = _fetch_power_history(device_id, hours=168)
    if history_7d.empty or len(history_7d) < 97:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Not enough historical data for {device_id}. "
                         f"Need at least 25 hours of 15-min power readings. "
                         f"Got {len(history_7d)} points."
            }
        )

    # 3. Fetch latest electrical measurements
    electrical = _fetch_latest_electrical(device_id)

    # 4. Generate forecast
    try:
        forecast = _build_forecast(device_id, model, history_7d, electrical)
    except ValueError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

    # 5. Build summary
    recent_avg = float(history_7d.tail(96).mean())  # last 24h average
    summary = _build_summary(device_id, forecast, recent_avg)

    # 6. Format history for chart — downsample to max 672 points (7d × 4/hr × 24)
    history_data = [
        {"time": ts.isoformat(), "value": round(float(v), 4)}
        for ts, v in history_7d.items()
        if not math.isnan(v)
    ]

    return {
        "query_type":   "forecast",
        "device_id":    device_id,
        "history":      history_data,
        "forecast":     forecast,
        "recent_avg":   round(recent_avg, 4),
        "summary":      summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }