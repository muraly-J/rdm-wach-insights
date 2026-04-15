import React from 'react';
import { ReferenceArea } from 'recharts';
import type { OffPeriod } from '../types';

/**
 * Render greyed-out ReferenceArea components for periods where devices are offline.
 *
 * This function handles two data formats:
 * 1. Data array with is_on flags: [{timestamp, value, is_on, ...}]
 *    - Generates off-periods automatically from consecutive is_on=false points
 * 2. OffPeriod array: [{start, end}]
 *    - Renders off-periods directly
 *
 * @param data - Either OffPeriod[] OR data array with is_on flags
 * @returns Array of ReferenceArea components to render in AreaChart
 */
export function renderOffPeriodAreas(
  data: any[] | OffPeriod[] | undefined,
  xKey?: string
): React.ReactNode {
  if (!data?.length) return null;

  // Check if this is an OffPeriod array (has start/end properties)
  if ('start' in data[0] && 'end' in data[0]) {
    // Legacy: handle OffPeriod[] format
    return (data as OffPeriod[]).map((p, i) => (
      <ReferenceArea
        key={i}
        x1={p.start}
        x2={p.end}
        fill="rgba(80,80,80,0.25)"
        label={{ value: 'OFF', position: 'insideTopLeft', fontSize: 9, fill: '#6d6e71' }}
        ifOverflow="hidden"
      />
    ));
  }

  // New: handle data array with is_on flags - generate off-periods
  // When xKey is provided (e.g. 'timestamp'), use that field's value for ReferenceArea x1/x2
  // so it matches the categorical XAxis. Without xKey, use numeric indices (works for
  // sparkline charts with no explicit XAxis).
  const xVal = (idx: number) => (xKey ? data[idx]?.[xKey] ?? idx : idx);

  const areas: React.ReactNode[] = [];
  let offStart: number | null = null;

  data.forEach((point, index) => {
    const isOff = point.is_on === false; // Only grey when explicitly false

    if (isOff) {
      // Start of an off-period
      if (offStart === null) {
        offStart = index;
      }
    } else {
      // End of an off-period
      if (offStart !== null) {
        // Render ReferenceArea for the off-period from offStart to index-1
        areas.push(
          <ReferenceArea
            key={`off-period-${offStart}-${index - 1}`}
            x1={xVal(offStart)}
            x2={xVal(index - 1)}
            fill="rgba(128, 128, 128, 0.15)" // Light grey
            stroke="none"
            label={null}
          />
        );
        offStart = null;
      }
    }
  });

  // If we end in an off-period, close it at the last index
  if (offStart !== null) {
    areas.push(
      <ReferenceArea
        key={`off-period-${offStart}-end`}
        x1={xVal(offStart)}
        x2={xVal(data.length - 1)}
        fill="rgba(128, 128, 128, 0.15)"
        stroke="none"
        label={null}
      />
    );
  }

  return areas;
}
