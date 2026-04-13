import React from 'react';
import { useAppStore, TimeRange } from '../../store/useAppStore';
import { resolveDeviceLabel, DeviceInfo } from '../../utils/deviceLabel';

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
];

interface FilterBarProps {
  levelDevices: DeviceInfo[];
}

type OpenPanel = 'level' | 'device' | null;

const FilterBar: React.FC<FilterBarProps> = ({ levelDevices }) => {
  const {
    selectedLevel,
    selectLevel,
    clearLevel,
    selectedDevice,
    selectDevice,
    timeRange,
    setTimeRange,
    dashboardMode,
    deepDiveSubMode,
    compareDevices,
    setCompareDevices,
  } = useAppStore();

  const [openPanel, setOpenPanel] = React.useState<OpenPanel>(null);
  const [deviceSearch, setDeviceSearch] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  const isCompareMode = dashboardMode === 'deepdive' && deepDiveSubMode === 'compare';

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filteredDevices = deviceSearch
    ? levelDevices.filter((d) => {
        const label = resolveDeviceLabel(d.id, levelDevices).toLowerCase();
        return (
          label.includes(deviceSearch.toLowerCase()) || d.id.includes(deviceSearch.toLowerCase())
        );
      })
    : levelDevices;

  const levelLabel = selectedLevel !== null ? `Level ${selectedLevel}` : 'All Levels';

  const deviceLabel = isCompareMode
    ? compareDevices.length > 0
      ? `${compareDevices.length} device${compareDevices.length > 1 ? 's' : ''}`
      : 'Select devices'
    : selectedDevice && selectedDevice !== 'all'
      ? resolveDeviceLabel(selectedDevice, levelDevices)
      : 'All AHUs';

  const toggleCompareDevice = (id: string) => {
    if (compareDevices.includes(id)) {
      setCompareDevices(compareDevices.filter((d) => d !== id));
    } else if (compareDevices.length < 3) {
      setCompareDevices([...compareDevices, id]);
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 30,
        background: 'rgba(11,15,20,0.92)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.30)',
      }}
    >
      <div
        style={{ maxWidth: 1280, margin: '0 auto' }}
        className="px-4 sm:px-6 py-2.5 flex items-center gap-4"
      >
        {/* Brand */}
        <span
          style={{
            color: '#00E5A0',
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: '0.08em',
            flexShrink: 0,
          }}
        >
          RDM-WACH
        </span>

        {/* Filter pills */}
        <div
          className="flex items-center gap-1 flex-1 overflow-x-auto"
          style={{ overflow: openPanel ? 'visible' : 'auto' }}
        >
          {/* Level selector */}
          <div style={{ position: 'relative', zIndex: openPanel === 'level' ? 60 : 'auto' }}>
            <button
              onClick={() => setOpenPanel(openPanel === 'level' ? null : 'level')}
              style={{
                background: selectedLevel !== null ? 'rgba(0,229,160,0.12)' : '#1a2234',
                border: `1px solid ${selectedLevel !== null ? '#00E5A0' : '#2e3f55'}`,
                color: selectedLevel !== null ? '#00E5A0' : '#8899aa',
                borderRadius: 20,
                padding: '4px 12px',
                fontSize: 12,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              {levelLabel}
              <span style={{ fontSize: 9, opacity: 0.6 }}>{openPanel === 'level' ? '▴' : '▾'}</span>
            </button>
            {openPanel === 'level' && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  left: 0,
                  background: '#141D28',
                  border: '1px solid #2e3f55',
                  borderRadius: 10,
                  padding: 6,
                  minWidth: 140,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                  zIndex: 50,
                  maxHeight: 280,
                  overflowY: 'auto',
                }}
              >
                <FilterItem
                  label="All Levels"
                  selected={selectedLevel === null}
                  onClick={() => {
                    clearLevel();
                    setOpenPanel(null);
                  }}
                />
                {LEVELS.map((lvl) => (
                  <FilterItem
                    key={lvl}
                    label={`Level ${lvl}`}
                    selected={selectedLevel === lvl}
                    onClick={() => {
                      selectLevel(lvl);
                      setOpenPanel(null);
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          {selectedLevel !== null && (
            <>
              <span style={{ color: '#2e3f55', fontSize: 11 }}>›</span>
              {/* Device selector */}
              <div style={{ position: 'relative', zIndex: openPanel === 'device' ? 60 : 'auto' }}>
                <button
                  onClick={() => setOpenPanel(openPanel === 'device' ? null : 'device')}
                  style={{
                    background: (
                      isCompareMode
                        ? compareDevices.length > 0
                        : selectedDevice && selectedDevice !== 'all'
                    )
                      ? 'rgba(0,229,160,0.12)'
                      : '#1a2234',
                    border: `1px solid ${(isCompareMode ? compareDevices.length > 0 : selectedDevice && selectedDevice !== 'all') ? '#00E5A0' : '#2e3f55'}`,
                    color: (
                      isCompareMode
                        ? compareDevices.length > 0
                        : selectedDevice && selectedDevice !== 'all'
                    )
                      ? '#00E5A0'
                      : '#8899aa',
                    borderRadius: 20,
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    maxWidth: 220,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {deviceLabel}
                  </span>
                  <span style={{ fontSize: 9, opacity: 0.6, flexShrink: 0 }}>
                    {openPanel === 'device' ? '▴' : '▾'}
                  </span>
                </button>
                {openPanel === 'device' && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 6px)',
                      left: 0,
                      background: '#141D28',
                      border: '1px solid #2e3f55',
                      borderRadius: 10,
                      padding: 6,
                      minWidth: 200,
                      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                      zIndex: 50,
                    }}
                  >
                    <input
                      autoFocus
                      placeholder="Search…"
                      value={deviceSearch}
                      onChange={(e) => setDeviceSearch(e.target.value)}
                      onMouseDown={(e) => e.stopPropagation()}
                      style={{
                        width: '100%',
                        background: '#1c2431',
                        border: '1px solid #2e3f55',
                        borderRadius: 6,
                        padding: '6px 10px',
                        fontSize: 11,
                        color: '#E8ECF1',
                        marginBottom: 6,
                        outline: 'none',
                      }}
                    />
                    <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                      {!isCompareMode && (
                        <FilterItem
                          label="All AHUs"
                          selected={!selectedDevice || selectedDevice === 'all'}
                          onClick={() => {
                            selectDevice(null);
                            setOpenPanel(null);
                            setDeviceSearch('');
                          }}
                        />
                      )}
                      {isCompareMode && (
                        <p style={{ fontSize: 10, color: '#556', padding: '4px 10px' }}>
                          Select up to 3 devices
                        </p>
                      )}
                      {filteredDevices.map((d) => {
                        const label = resolveDeviceLabel(d.id, levelDevices);
                        const isSelected = isCompareMode
                          ? compareDevices.includes(d.id)
                          : selectedDevice === d.id;
                        const isDisabled =
                          isCompareMode && !isSelected && compareDevices.length >= 3;
                        return (
                          <FilterItem
                            key={d.id}
                            label={label}
                            selected={isSelected}
                            disabled={isDisabled}
                            onClick={() => {
                              if (isCompareMode) {
                                toggleCompareDevice(d.id);
                              } else {
                                selectDevice(d.id);
                                setOpenPanel(null);
                                setDeviceSearch('');
                              }
                            }}
                          />
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Time range pills */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {TIME_RANGES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setTimeRange(value)}
              style={{
                background: timeRange === value ? '#00E5A0' : '#1a2234',
                border: `1px solid ${timeRange === value ? '#00E5A0' : '#2e3f55'}`,
                color: timeRange === value ? '#000' : '#8899aa',
                borderRadius: 20,
                padding: '4px 10px',
                fontSize: 11,
                fontWeight: timeRange === value ? 700 : 400,
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const FilterItem: React.FC<{
  label: string;
  selected: boolean;
  disabled?: boolean;
  onClick?: () => void;
}> = ({ label, selected, disabled = false, onClick }) => (
  <div
    onClick={disabled ? undefined : onClick}
    style={{
      padding: '7px 10px',
      borderRadius: 6,
      fontSize: 12,
      color: disabled ? '#3a4a5a' : selected ? '#00E5A0' : '#8899aa',
      fontWeight: selected ? 600 : 400,
      cursor: disabled ? 'default' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}
    onMouseEnter={(e) => {
      if (!disabled) (e.currentTarget as HTMLElement).style.background = '#2e3f55';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.background = 'transparent';
    }}
  >
    <span>{label}</span>
    {selected && <span style={{ fontSize: 6, color: '#00E5A0' }}>●</span>}
  </div>
);

export default FilterBar;
