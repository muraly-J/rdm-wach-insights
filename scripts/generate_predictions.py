#!/usr/bin/env python3
"""
scripts/generate_predictions.py
────────────────────────────────
Pre-generate predictions_multihorizon.csv for all devices.

Usage:
    python scripts/generate_predictions.py
    python scripts/generate_predictions.py --devices e0202 e0207
    python scripts/generate_predictions.py --mode append

Output: data/predictions_multihorizon.csv
Schema: timestamp, ahu_id, level, delta_kwh, pred_1h, pred_12h, pred_24h, pred_168h
"""
import sys
import argparse
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pandas as pd
from models.schemas import AHU_LEVEL_CONFIG, DEVICE_TO_LEVEL
from core.prediction_engine import compute_predictions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUT_PATH = Path(__file__).parent.parent / "data" / "predictions_multihorizon.csv"
HORIZONS = ["1h", "12h", "24h", "168h"]


def run(devices: list[str], mode: str) -> None:
    rows = []
    total = len(devices)
    for i, device_id in enumerate(devices, 1):
        logger.info("[%d/%d] Computing predictions for %s ...", i, total, device_id)
        try:
            result = compute_predictions(device_id, horizons=HORIZONS)
            if result is None:
                logger.warning("  Skipped %s (no data)", device_id)
                continue
            level = DEVICE_TO_LEVEL.get(device_id, "?")
            level_str = level  # DEVICE_TO_LEVEL already returns "Level N"
            now_ts = result["t_now"]
            row = {
                "timestamp": now_ts,
                "device_id": device_id,
                "level": level_str,
                "delta_kwh": result["horizons"].get("1h", {}).get("delta_kwh"),
            }
            for h in HORIZONS:
                key = f"pred_{h}"
                h_data = result["horizons"].get(h, {})
                row[key] = h_data.get("predictions", {}).get("energy_import")
            rows.append(row)
        except Exception as exc:
            logger.error("  Error for %s: %s", device_id, exc)

    if not rows:
        logger.warning("No predictions generated.")
        return

    df_new = pd.DataFrame(rows)
    cols = ["timestamp", "device_id", "level", "delta_kwh", "pred_1h", "pred_12h", "pred_24h", "pred_168h"]
    df_new = df_new.reindex(columns=cols)

    if mode == "append" and OUT_PATH.exists():
        df_old = pd.read_csv(OUT_PATH)
        df_out = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_out = df_new

    df_out.to_csv(OUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df_out), OUT_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", nargs="+", default=None)
    parser.add_argument("--mode", choices=["overwrite", "append"], default="overwrite")
    args = parser.parse_args()

    # Collect all devices from AHU_LEVEL_CONFIG
    all_devices = []
    for level_config in AHU_LEVEL_CONFIG.values():
        all_devices.extend(level_config.get("device_ids", []))

    devices = args.devices if args.devices else all_devices
    run(devices, args.mode)
