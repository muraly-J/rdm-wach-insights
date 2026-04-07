#!/usr/bin/env python3
"""Test that run_health_etl_historical produces >1 row per device."""
import sys, os

def test_multiple_rows_per_device():
    """After a partial run, each device should have >1 row in DuckDB."""
    print("SKIP: history_generator now writes to DuckDB; use test_e2e_pipeline.py to verify row counts")

if __name__ == "__main__":
    test_multiple_rows_per_device()
