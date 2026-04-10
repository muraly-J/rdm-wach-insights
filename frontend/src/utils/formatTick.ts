/**
 * formatTickByRange
 * ─────────────────
 * Returns a human-readable tick label for a chart X-axis given a timestamp
 * string (ISO 8601) and the active time range. All times displayed in MYT (UTC+8).
 *
 *   24h  →  "14:00"           (time-of-day only; all points are within today)
 *   7d   →  "Mar 10 14:00"    (date + time; hourly granularity)
 *   30d  →  "Mar 13"          (date only; daily granularity)
 */
export type TimeRange = '24h' | '7d' | '30d';

const MYT_TIMEZONE = 'Asia/Kuala_Lumpur';

// Format date in MYT (Asia/Kuala_Lumpur)
export function formatDateMYT(date: Date, options?: Intl.DateTimeFormatOptions): string {
  return date.toLocaleDateString('en-US', {
    ...options,
    timeZone: MYT_TIMEZONE
  });
}

// Format time in MYT (Asia/Kuala_Lumpur)
export function formatTimeMYT(date: Date, options?: Intl.DateTimeFormatOptions): string {
  return date.toLocaleTimeString('en-US', {
    ...options,
    timeZone: MYT_TIMEZONE
  });
}

// Format both date and time in MYT
export function formatDateTimeMYT(date: Date, options?: Intl.DateTimeFormatOptions): string {
  return date.toLocaleString('en-US', {
    ...options,
    timeZone: MYT_TIMEZONE
  });
}

export function formatTickByRange(timestamp: string, range: TimeRange): string {
  const d = new Date(timestamp);
  const tzOptions = { timeZone: MYT_TIMEZONE };

  if (range === '24h') {
    return formatTimeMYT(d, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }
  if (range === '7d') {
    const date = formatDateMYT(d, {
      month: 'short',
      day: 'numeric'
    });
    const time = formatTimeMYT(d, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    return `${date} ${time}`;
  }
  // 30d
  return formatDateMYT(d, {
    month: 'short',
    day: 'numeric'
  });
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
