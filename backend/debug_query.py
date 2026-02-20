import asyncio
from backend.llm.translator import translate_query
from backend.influx_client import fetch_time_series

async def main():
    query = "compare e0101 vs e0206 power total for the past 30 days"
    print(f"\nInput: \"{query}\"")

    result, error = await translate_query(query)
    if error:
        print(f"❌ LLM failed: {error}")
        return

    print(f"✅ LLM output:")
    print(f"   devices  : {result.device_ids}")
    print(f"   metric   : {result.metric}")
    print(f"   range    : {result.time_range}")

    df = fetch_time_series(result.device_ids, result.metric, result.time_range)
    print(f"\nInfluxDB returned: {len(df)} rows, columns: {list(df.columns)}")
    for col in df.columns:
        non_zero = (df[col] != 0).sum()
        print(f"   {col}: min={df[col].min():.4f}, max={df[col].max():.4f}, non-zero rows={non_zero}/{len(df)}")

if __name__ == "__main__":
    asyncio.run(main())
