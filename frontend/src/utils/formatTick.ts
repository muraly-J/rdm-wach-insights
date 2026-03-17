/**
 * formatTickByRange
 * ─────────────────
 * Returns a human-readable tick label for a chart X-axis given a timestamp
 * string (ISO 8601) and the active time range.
 *
 *   24h  →  "14:00"           (time-of-day only; all points are within today)
 *   7d   →  "Mar 10 14:00"    (date + time; hourly granularity)
 *   30d  →  "Mar 13"          (date only; daily granularity)
 */
export type TimeRange = '24h' | '7d' | '30d';

export function formatTickByRange(timestamp: string, range: TimeRange): string {
  const d = new Date(timestamp);
  if (range === '24h') {
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  }
  if (range === '7d') {
    const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    return `${date} ${time}`;
  }
  // 30d
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * tickIntervalByRange
 * ───────────────────
 * Returns the Recharts `interval` prop value so that ~7-8 ticks are shown
 * regardless of total data point count.
 *
 *   24h  → every 3 hours  (interval=2  → shows 00:00 03:00 06:00 … 21:00)
 *   7d   → every 24 hours (interval=23 → shows one tick per day)
 *   30d  → every 4 days   (interval=3  → shows ~8 ticks across 30 days)
 */
export function tickIntervalByRange(range: TimeRange): number {
  if (range === '24h') return 2;   // every 3rd point of 24 = 8 ticks
  if (range === '7d') return 23;   // every 24th point of 168 = 7 ticks
  return 3;                         // every 4th point of 30 = ~8 ticks
}
