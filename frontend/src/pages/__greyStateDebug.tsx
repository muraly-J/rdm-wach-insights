import React from 'react';
import GreyStateWrapper from '../components/shared/GreyStateWrapper';

const cases: Array<{ label: string; props: any }> = [
  { label: 'On / fresh', props: { operationalState: 'On', lastMeasured: new Date().toISOString() } },
  { label: 'Off', props: { operationalState: 'Off', lastMeasured: null } },
  { label: 'Off · Stale', props: { operationalState: 'Off_Stale', lastMeasured: '2020-01-01T00:00:00Z' } },
  { label: 'Inactive', props: { operationalState: 'Inactive' } },
  { label: 'Stale by age', props: { operationalState: 'On', lastMeasured: new Date(Date.now() - 12 * 3600_000).toISOString() } },
  { label: 'Low confidence', props: { operationalState: 'On', confidence: 0.2 } },
];

export default function GreyStateDebug() {
  return (
    <div style={{ padding: 24, background: '#0B0F14', color: '#E8ECF1', minHeight: '100vh' }}>
      <h1>useGreyState visual matrix</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {cases.map((c) => (
          <GreyStateWrapper key={c.label} {...c.props}>
            <div style={{ background: '#1a2234', border: '1px solid #2a3649', borderRadius: 12, padding: 24, height: 160 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{c.label}</div>
              <div style={{ marginTop: 8, fontSize: 11, color: '#8899aa' }}>
                {JSON.stringify(c.props)}
              </div>
            </div>
          </GreyStateWrapper>
        ))}
      </div>
    </div>
  );
}