import React from 'react';
import { ReferenceArea } from 'recharts';
import type { OffPeriod } from '../types';

export function renderOffPeriodAreas(offPeriods: OffPeriod[] | undefined): React.ReactNode {
  if (!offPeriods?.length) return null;
  return offPeriods.map((p, i) => (
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
