#!/usr/bin/env python3
"""One-shot migration: rename ahu_id → device_id in CSV data files.
Safe to re-run — skips files that already have device_id column.
"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).parents[1]

TARGETS = [
    ROOT / "data" / "health_all_levels.csv",
    ROOT / "data" / "predictions.csv",
]

for path in TARGETS:
    if not path.exists():
        print(f"SKIP {path} — not found")
        continue
    df_head = pd.read_csv(path, nrows=0)  # headers only, fast
    if 'device_id' not in df_head.columns:
        print(f"SKIP {path} — no ahu_id column (already migrated?)")
        continue
    print(f"Migrating {path} ({path.stat().st_size // 1024} KB) …", flush=True)
    df = pd.read_csv(path)
    df = df.rename(columns={'device_id': 'device_id'})
    df.to_csv(path, index=False)
    print(f"  Done. {len(df):,} rows, column renamed.")
