# Health Index Chart: Fix Data Duplication & Color Segmentation

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the health index chart to eliminate duplicate data points and restrict on/off color inversion to single-AHU views only.

**Architecture:** 
- Simplify `healthChartData` construction in App.tsx to avoid duplicate merging
- Add conditional rendering in HealthIndexChart: single-device views get color segmentation, multi-device views get simple lines
- Track whether we're viewing a single device vs. all devices and pass that context to the chart

**Tech Stack:** React, Recharts, TypeScript

---

## File Structure

**Modified Files:**
- `frontend/src/App.tsx` – Chart data construction + pass single-device flag
- `frontend/src/components/dashboard/HealthIndexChart.tsx` – Conditional rendering of color segments

---

## Task 1: Understand Current Chart Data Issue

**Files:**
- Read: `frontend/src/App.tsx:159-193`

- [ ] **Step 1: Log the raw API response to see data structure**

Open DevTools → Network → find the `/api/level/1/health-index?time_range=7d` request → copy response JSON and inspect the structure. Note:
- How many devices are returned?
- How many data points per device?
- Are timestamps unique across devices or duplicated?

- [ ] **Step 2: Log healthChartData after merge**

Add temporary `console.log` in App.tsx after the healthChartData computation:
```typescript
const healthChartData = React.useMemo(() => {
    // ... existing merge logic ...
    const result = Array.from(dataByTimestamp.values())
      .sort((a, b) => a.originalTs.localeCompare(b.originalTs))
      .map(({ values }) => values);
    console.log('healthChartData:', result.length, 'points, timestamps:', result.map(p => p.timestamp).slice(0, 5));
    return result;
  }, [healthData, selectedDevice, chartRange, labelMap]);
```

Refresh and check console. Expected: Should see ~168 points for 7d (one per hour per device merged by timestamp).

- [ ] **Step 3: Check if timestamps are being duplicated**

In the same log, add:
```typescript
const timestampCounts = new Map<string, number>();
result.forEach(p => {
  const ts = p.timestamp;
  timestampCounts.set(ts, (timestampCounts.get(ts) || 0) + 1);
});
const duplicates = Array.from(timestampCounts.entries()).filter(([_, count]) => count > 1);
console.log('Duplicate timestamps:', duplicates);
```

If duplicates exist, the merge logic is broken.

- [ ] **Step 4: Commit observation (no code changes)**

```bash
git commit --allow-empty -m "debug: inspect health chart data duplication issue"
```

---

## Task 2: Fix healthChartData Merge Logic

**Files:**
- Modify: `frontend/src/App.tsx:159-193`

**Issue:** The current merge is grouping by timestamp string, which causes issues when multiple devices have data at the same timestamp. Need to preserve the original behavior for multi-device views.

- [ ] **Step 1: Revert to simpler merge for all-devices view**

Replace the `healthChartData` computation with:

```typescript
const healthChartData = React.useMemo(() => {
  if (!healthData?.devices?.length) return [];
  const series = selectedDevice && selectedDevice !== 'all'
    ? healthData.devices.filter((d) => d.id === selectedDevice)
    : healthData.devices;

  // For single device: use all data points (will include on/off segments)
  if (selectedDevice && selectedDevice !== 'all') {
    return series[0]?.data?.map((point: any) => ({
      timestamp: formatTickByRange(point.timestamp, chartRange),
      originalTs: point.timestamp,
      value: point.value,
      is_on: point.is_on,
    })) || [];
  }

  // For all devices: merge by index (original behavior), no on/off colors
  const refData = series[0]?.data ?? [];
  return refData.map((point, idx) => {
    const timestamp = formatTickByRange(point.timestamp, chartRange);
    const entry: Record<string, any> = { timestamp };
    series.forEach(({ id, data }) => {
      entry[labelMap[id] ?? id] = data[idx]?.value ?? null;
    });
    return entry;
  });
}, [healthData, selectedDevice, chartRange, labelMap]);
```

Key changes:
- Single device: Return all data points as-is with `is_on` field intact
- Multi-device: Use original index-based merge (no on/off logic)

- [ ] **Step 2: Compute isSingleDevice flag**

Add after the healthChartData definition:

```typescript
const isSingleDevice = selectedDevice && selectedDevice !== 'all';
```

- [ ] **Step 3: Pass flag to HealthIndexChart**

Find where HealthIndexChart is rendered (around line 266):

```typescript
<HealthIndexChart data={healthChartData as any} devices={chartDevices} showColorSegments={isSingleDevice} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix: separate chart data logic for single vs multi-device views

- Single device: preserve all data points with is_on field for color segments
- Multi-device: use index-based merge without color logic
- Add isSingleDevice flag to control chart rendering"
```

---

## Task 3: Update HealthIndexChart Props

**Files:**
- Modify: `frontend/src/components/dashboard/HealthIndexChart.tsx:15-28`

- [ ] **Step 1: Add showColorSegments prop**

Update the interface:

```typescript
interface HealthIndexChartProps {
  data: Array<{ timestamp: string; [key: string]: number; originalTs?: string; is_on?: boolean }>;
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  showColorSegments?: boolean;
}
```

- [ ] **Step 2: Update component signature**

Change:
```typescript
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices }) => {
```

To:
```typescript
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices, showColorSegments = false }) => {
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/HealthIndexChart.tsx
git commit -m "feat: add showColorSegments prop to HealthIndexChart"
```

---

## Task 4: Simplify Chart Rendering for Multi-Device

**Files:**
- Modify: `frontend/src/components/dashboard/HealthIndexChart.tsx:150-220` (Area rendering section)

- [ ] **Step 1: Replace Area rendering with conditional logic**

Find the section that renders Areas (around line 150-220) and replace it with:

```typescript
{/* Multi-device: simple lines, no color segments */}
{!showColorSegments && devices.map((device, index) => (
  <Area
    key={device.id}
    type="monotone"
    dataKey={device.name}
    stroke={getColor(index)}
    strokeWidth={2}
    fill="none"
    connectNulls
    dot={false}
  />
))}

{/* Single device: render on/off color segments */}
{showColorSegments && devices.map((device, index) => {
  const baseColor = getColor(index);
  const invertedColor = invertColor(baseColor);

  return (
    <React.Fragment key={device.id}>
      {/* On-time: normal color */}
      <Area
        type="monotone"
        dataKey={device.name}
        data={data}
        stroke={baseColor}
        strokeWidth={2}
        fill="none"
        connectNulls
        dot={false}
        shape={(props: any) => {
          const { points } = props;
          if (!points || points.length === 0) return null;

          let pathD = '';
          for (let i = 0; i < points.length; i++) {
            const point = points[i];
            if (point && (data[i] as any).is_on !== false) {
              const cmd = i === 0 ? 'M' : 'L';
              pathD += `${cmd} ${point.x} ${point.y} `;
            }
          }
          return <path d={pathD} stroke={baseColor} strokeWidth={2} fill="none" />;
        }}
      />

      {/* Off-time: inverted color */}
      <Area
        type="monotone"
        dataKey={device.name}
        data={data}
        stroke={invertedColor}
        strokeWidth={2}
        fill="none"
        connectNulls
        dot={false}
        opacity={0.7}
        shape={(props: any) => {
          const { points } = props;
          if (!points || points.length === 0) return null;

          let pathD = '';
          for (let i = 0; i < points.length; i++) {
            const point = points[i];
            if (point && (data[i] as any).is_on === false) {
              const cmd = i === 0 ? 'M' : 'L';
              pathD += `${cmd} ${point.x} ${point.y} `;
            }
          }
          return <path d={pathD} stroke={invertedColor} strokeWidth={2} fill="none" opacity={0.7} />;
        }}
      />
    </React.Fragment>
  );
})}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/HealthIndexChart.tsx
git commit -m "fix: conditionally render color segments only for single-device views

- Multi-device: simple line chart without color changes
- Single device: on/off color segments (normal/inverted)
- Eliminates visual overlap and data duplication"
```

---

## Task 5: Test and Verify

**Files:**
- Test: Manual verification in browser

- [ ] **Step 1: View Level 1 (all AHUs)**

- Hard-refresh https://demo-wach-insight.vercel.app
- Select Level 1, view all AHUs (don't select a specific device)
- Expected: Clean line chart with multiple colored lines, no squashing on left, no color segments

- [ ] **Step 2: View single AHU (e0212)**

- Select e0212 from Level 1
- Expected: Single line with color changes (green on, inverted color off), continuous line

- [ ] **Step 3: Verify time ranges work**

- Try 24h, 7d, 30d
- Expected: Chart expands to fill the x-axis properly at all ranges

- [ ] **Step 4: Verify "all" view still works**

- Switch back to all AHUs
- Expected: All lines visible without color segments

---

## Task 6: Deploy

**Files:**
- No changes needed

- [ ] **Step 1: Push to main**

```bash
git push origin main
```

- [ ] **Step 2: Deploy to Vercel**

```bash
vercel deploy --prod
```

Wait for deployment to complete. Expected: Build succeeds, no TypeScript errors.

- [ ] **Step 3: Verify in production**

- Visit https://demo-wach-insight.vercel.app
- Hard-refresh
- Test Level 1 all AHUs view (clean lines)
- Test single AHU view (color segments)

- [ ] **Step 4: Final commit reference**

```bash
git log --oneline -5
```

Should see your commits from Tasks 2, 3, 4.

---

## Summary of Changes

| File | Change | Why |
|------|--------|-----|
| `App.tsx` | Split healthChartData logic by view (single vs. multi) | Prevents duplicate merging for multi-device, preserves is_on for single |
| `HealthIndexChart.tsx` | Add showColorSegments prop + conditional Area rendering | Renders simple lines for level view, color segments for single device |
