// frontend/src/components/dashboard/DashboardControls.tsx
import React from 'react';
import { TimeRange, useAppStore } from '../../store/useAppStore';

// ── Constants ──────────────────────────────────────────────────────────────
const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const TIME_RANGES: TimeRange[] = ['24h', '7d', '30d'];

// ── Types ──────────────────────────────────────────────────────────────────
interface DashboardControlsProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
}

type OpenPanel = 'level' | 'device' | 'range' | null;

// ── DropdownSegment ────────────────────────────────────────────────────────
// Internal sub-component — not exported.
interface SegmentProps {
  label: string;
  value: string;
  isActive: boolean;       // green accent colour
  isOpen: boolean;         // #1A2330 highlight
  isDisabled?: boolean;    // #4A5568, cursor default, click ignored
  onClick: () => void;
  children: React.ReactNode; // panel content
}

const DropdownSegment: React.FC<SegmentProps> = ({
  label,
  value,
  isActive,
  isOpen,
  isDisabled = false,
  onClick,
  children,
}) => {
  const segRef = React.useRef<HTMLDivElement>(null);

  // Resolve text colour
  let textColour = '#8A95A5';
  if (isDisabled) textColour = '#4A5568';
  else if (isActive) textColour = '#00E5A0';

  const segBg = isOpen ? '#1A2330' : 'transparent';

  // Viewport-clamped panel: align left edge of panel to left edge of segment.
  // If that would overflow the right edge of the viewport, shift left.
  const [panelLeft, setPanelLeft] = React.useState<number>(0);

  React.useEffect(() => {
    if (!isOpen || !segRef.current) return;
    const rect = segRef.current.getBoundingClientRect();
    const panelMinWidth = 140;
    const rightEdge = rect.left + panelMinWidth;
    const viewportWidth = window.innerWidth;
    if (rightEdge > viewportWidth - 8) {
      setPanelLeft(viewportWidth - 8 - panelMinWidth - rect.left);
    } else {
      setPanelLeft(0);
    }
  }, [isOpen]);

  return (
    <div ref={segRef} style={{ position: 'relative', display: 'inline-block' }}>
      {/* Segment button */}
      <div
        role="button"
        aria-expanded={isOpen}
        aria-disabled={isDisabled}
        onClick={isDisabled ? undefined : onClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          padding: '8px 13px',
          fontSize: '12px',
          color: textColour,
          cursor: isDisabled ? 'default' : 'pointer',
          whiteSpace: 'nowrap',
          background: segBg,
          transition: 'color 0.15s, background 0.15s',
          userSelect: 'none',
        }}
      >
        <span style={{ fontSize: '9px', color: '#4A5568' }}>{label}</span>
        <span style={{ fontWeight: 600 }}>{value}</span>
        {!isDisabled && (
          <span style={{ fontSize: '9px', opacity: 0.5 }}>{isOpen ? '▴' : '▾'}</span>
        )}
      </div>

      {/* Floating panel */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: panelLeft,
            background: '#141D28',
            border: '1px solid #1E2A3A',
            borderRadius: '10px',
            padding: '6px',
            minWidth: '140px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3)',
            zIndex: 50,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// ── Shared panel item style helpers ───────────────────────────────────────
const PanelItem: React.FC<{
  label: string;
  selected: boolean;
  disabled?: boolean;
  onClick?: () => void;
}> = ({ label, selected, disabled = false, onClick }) => (
  <div
    onClick={disabled ? undefined : onClick}
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '7px 10px',
      borderRadius: '6px',
      fontSize: '12px',
      color: disabled ? '#4A5568' : selected ? '#00E5A0' : '#8A95A5',
      fontWeight: selected ? 600 : 400,
      cursor: disabled ? 'default' : 'pointer',
    }}
    onMouseEnter={(e) => {
      if (!disabled) (e.currentTarget as HTMLElement).style.background = '#1E2A3A';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.background = 'transparent';
    }}
  >
    <span>{label}</span>
    {selected && <span style={{ fontSize: '6px', color: '#00E5A0' }}>●</span>}
  </div>
);

// ── DashboardControls ──────────────────────────────────────────────────────
const DashboardControls: React.FC<DashboardControlsProps> = ({ devices }) => {
  const { selectedLevel, selectLevel, clearLevel, selectedDevice, selectDevice, timeRange, setTimeRange } =
    useAppStore();

  const [openPanel, setOpenPanel] = React.useState<OpenPanel>(null);
  const [deviceSearch, setDeviceSearch] = React.useState('');

  const containerRef = React.useRef<HTMLDivElement>(null);

  // Click-outside — single listener on document
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const togglePanel = (panel: OpenPanel) =>
    setOpenPanel((prev) => (prev === panel ? null : panel));

  // Filtered devices for search
  const filteredDevices = deviceSearch
    ? devices.filter((d) => d.id.toLowerCase().includes(deviceSearch.toLowerCase()))
    : devices;

  // Segment display values
  const lvlValue = selectedLevel !== null ? `L${selectedLevel}` : 'All';
  const devValue =
    selectedDevice && selectedDevice !== 'all' ? selectedDevice : 'All';
  const devIsActive = Boolean(selectedDevice && selectedDevice !== 'all');
  const devIsDisabled = selectedLevel === null;

  return (
    <div ref={containerRef}>
          {/* Unified pill strip */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              background: '#111820',
              border: '1px solid #1E2A3A',
              borderRadius: '10px',
              overflow: 'visible',
            }}
          >
            {/* LVL segment */}
            <DropdownSegment
              label="LVL"
              value={lvlValue}
              isActive={selectedLevel !== null}
              isOpen={openPanel === 'level'}
              onClick={() => togglePanel('level')}
            >
              <PanelItem
                key="all"
                label="All Levels"
                selected={selectedLevel === null}
                onClick={() => {
                  clearLevel();
                  setOpenPanel(null);
                }}
              />
              {LEVELS.map((lvl) => (
                <PanelItem
                  key={lvl}
                  label={`Level ${lvl}`}
                  selected={selectedLevel === lvl}
                  onClick={() => {
                    selectLevel(lvl);
                    setOpenPanel(null);
                  }}
                />
              ))}
            </DropdownSegment>

            {/* Separator */}
            <div style={{ width: '1px', height: '20px', background: '#1E2A3A', flexShrink: 0 }} />

            {/* DEV segment */}
            <DropdownSegment
              label="DEV"
              value={devIsDisabled ? '—' : devValue}
              isActive={devIsActive}
              isOpen={openPanel === 'device'}
              isDisabled={devIsDisabled}
              onClick={() => togglePanel('device')}
            >
              {/* Search input */}
              <input
                autoFocus
                placeholder="Search…"
                value={deviceSearch}
                onChange={(e) => setDeviceSearch(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0B0F14',
                  border: '1px solid #1E2A3A',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  fontSize: '11px',
                  color: '#E8ECF1',
                  marginBottom: '6px',
                  outline: 'none',
                }}
                onMouseDown={(e) => e.stopPropagation()}
              />

              {/* Scrollable list — max 240px */}
              <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
                {/* All AHUs */}
                <PanelItem
                  label="All AHUs"
                  selected={!selectedDevice || selectedDevice === 'all'}
                  onClick={() => {
                    selectDevice(null);
                    setOpenPanel(null);
                    setDeviceSearch('');
                  }}
                />

                {devices.length === 0 ? (
                  <PanelItem label="No devices available" selected={false} disabled />
                ) : (
                  filteredDevices.map((d) => (
                    <div
                      key={d.id}
                      title={[d.label, d.department].filter(Boolean).join(' — ') || d.id}
                    >
                      <PanelItem
                        label={d.id}
                        selected={selectedDevice === d.id}
                        onClick={() => {
                          selectDevice(d.id);
                          setOpenPanel(null);
                          setDeviceSearch('');
                        }}
                      />
                    </div>
                  ))
                )}
              </div>
            </DropdownSegment>

            {/* Separator */}
            <div style={{ width: '1px', height: '20px', background: '#1E2A3A', flexShrink: 0 }} />

            {/* RANGE segment */}
            <DropdownSegment
              label="RANGE"
              value={timeRange}
              isActive={true}
              isOpen={openPanel === 'range'}
              onClick={() => togglePanel('range')}
            >
              {TIME_RANGES.map((r) => (
                <PanelItem
                  key={r}
                  label={r}
                  selected={timeRange === r}
                  onClick={() => {
                    setTimeRange(r);
                    setOpenPanel(null);
                  }}
                />
              ))}
            </DropdownSegment>
          </div>
    </div>
  );
};

export default DashboardControls;
