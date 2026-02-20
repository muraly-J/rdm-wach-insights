"""
Test script for Stage 4 — Visualization & CSV Engine
Run from the project root: python3 backend/tests/test_charts.py

Hits real InfluxDB so you can see actual chart payloads and summaries.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import asyncio
from backend.core.influx_client import fetch_time_series, fetch_ranking
from backend.core.charts import build_line_chart, build_bar_chart
from backend.core.summarizer import generate_summary

async def run_tests():
    print("\n" + "="*60)
    print(" WACH INSIGHT - CHART & SUMMARY TEST ".center(60, "="))
    print("="*60)


    # ── Test 1: Line chart (time series) ─────────────────────────────────────────
    print("\n[Test 1] Line chart — e0101 power_total last 24h...")

    df_ts = fetch_time_series(
        device_ids=["e0101"],
        metric="power_total",
        time_range="last_24h",
    )

    payload_line = build_line_chart(df_ts, metric="power_total", time_range="last_24h")

    print(f"   chart_type : {payload_line['chart_type']}")
    print(f"   device_ids : {payload_line['device_ids']}")
    print(f"   data rows  : {len(payload_line['data'])}")
    print(f"   sample row : {payload_line['data'][0] if payload_line['data'] else 'empty'}")
    print(f"   csv lines  : {len(payload_line['csv'].splitlines())} lines")

    if payload_line['data']:
        print("   ✅ Line chart payload built successfully")
    else:
        print("   ⚠️  No data returned — check device e0101 has data in last 24h")

    print("\n   Generating summary...")
    summary_line = await generate_summary(
        chart_payload=payload_line,
        query_type="time_series",
        device_ids=["e0101"],
        metric="power_total",
        time_range="last_24h",
    )
    print(f"   Summary: {summary_line}")
    print("   ✅ Summary generated" if summary_line else "   ❌ Summary empty")


    # ── Test 2: Bar chart (ranking) ───────────────────────────────────────────────
    print("\n[Test 2] Bar chart — top 5 devices by power_total last 7d...")

    df_rank = fetch_ranking(
        metric="power_total",
        time_range="last_7d",
        device_ids=[],
        top_n=5,
    )

    payload_bar = build_bar_chart(df_rank, metric="power_total", time_range="last_7d", top_n=5)

    print(f"   chart_type : {payload_bar['chart_type']}")
    print(f"   data rows  : {len(payload_bar['data'])}")
    print(f"   top device : {payload_bar['data'][0] if payload_bar['data'] else 'empty'}")
    print(f"   csv lines  : {len(payload_bar['csv'].splitlines())} lines")

    if payload_bar['data']:
        print("   ✅ Bar chart payload built successfully")
    else:
        print("   ⚠️  No data returned")

    print("\n   Generating summary...")
    summary_bar = await generate_summary(
        chart_payload=payload_bar,
        query_type="ranking",
        device_ids=[],
        metric="power_total",
        time_range="last_7d",
    )
    print(f"   Summary: {summary_bar}")
    print("   ✅ Summary generated" if summary_bar else "   ❌ Summary empty")


    # ── Test 3: CSV spot-check ────────────────────────────────────────────────────
    print("\n[Test 3] CSV format check...")
    csv_lines = payload_line['csv'].splitlines()
    if len(csv_lines) > 1:
        print(f"   Header : {csv_lines[0]}")
        print(f"   Row 1  : {csv_lines[1]}")
        print("   ✅ CSV looks well-formed")
    else:
        print("   ⚠️  CSV is empty or only has a header")


    print("\n" + "="*60)
    print(" STAGE 4 TEST COMPLETE ".center(60, "="))
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
