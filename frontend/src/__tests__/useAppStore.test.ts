import { useAppStore, initialState } from '../store/useAppStore';

// Reset store to initial state before each test — merge actions back in to
// avoid wiping Zustand action functions when using replace mode.
beforeEach(() => {
  const actions = useAppStore.getState();
  useAppStore.setState(
    {
      ...actions,
      ...initialState,
      timeRange: '7d',
      financialImpact: null,
      hamburgerOpen: false,
      siteSummaryData: null,
    },
    true,
  );
});

describe('useAppStore — initial state', () => {
  it('selectedLevel is null initially', () => {
    expect(useAppStore.getState().selectedLevel).toBeNull();
  });

  it('selectedDevice is null initially', () => {
    expect(useAppStore.getState().selectedDevice).toBeNull();
  });

  it('chatOpen is false initially', () => {
    expect(useAppStore.getState().chatOpen).toBe(false);
  });
});

describe('useAppStore — level selection', () => {
  it('selectLevel updates selectedLevel', () => {
    useAppStore.getState().selectLevel(5);
    expect(useAppStore.getState().selectedLevel).toBe(5);
  });

  it('selectLevel resets selectedDevice', () => {
    useAppStore.getState().selectDevice('e0202');
    useAppStore.getState().selectLevel(3);
    expect(useAppStore.getState().selectedDevice).toBeNull();
  });

  it('selectLevel handles all valid levels 1–11', () => {
    for (let l = 1; l <= 11; l++) {
      useAppStore.getState().selectLevel(l);
      expect(useAppStore.getState().selectedLevel).toBe(l);
    }
  });
});

describe('useAppStore — device selection', () => {
  it('selectDevice updates selectedDevice', () => {
    useAppStore.getState().selectDevice('e0101');
    expect(useAppStore.getState().selectedDevice).toBe('e0101');
  });

  it('selectDevice accepts null to clear', () => {
    useAppStore.getState().selectDevice('e0101');
    useAppStore.getState().selectDevice(null);
    expect(useAppStore.getState().selectedDevice).toBeNull();
  });
});

describe('useAppStore — chat state', () => {
  it('openChat sets chatOpen to true', () => {
    useAppStore.getState().openChat();
    expect(useAppStore.getState().chatOpen).toBe(true);
  });

  it('closeChat sets chatOpen to false', () => {
    useAppStore.getState().openChat();
    useAppStore.getState().closeChat();
    expect(useAppStore.getState().chatOpen).toBe(false);
  });

  it('toggleChat flips chatOpen', () => {
    expect(useAppStore.getState().chatOpen).toBe(false);
    useAppStore.getState().toggleChat();
    expect(useAppStore.getState().chatOpen).toBe(true);
    useAppStore.getState().toggleChat();
    expect(useAppStore.getState().chatOpen).toBe(false);
  });
});

describe('useAppStore — dashboard mode', () => {
  it('dashboardMode defaults to simple', () => {
    expect(useAppStore.getState().dashboardMode).toBe('simple');
  });

  it('setDashboardMode updates dashboardMode', () => {
    useAppStore.getState().setDashboardMode('deepdive');
    expect(useAppStore.getState().dashboardMode).toBe('deepdive');
  });

  it('deepDiveSubMode defaults to single', () => {
    expect(useAppStore.getState().deepDiveSubMode).toBe('single');
  });

  it('setDeepDiveSubMode updates deepDiveSubMode', () => {
    useAppStore.getState().setDeepDiveSubMode('compare');
    expect(useAppStore.getState().deepDiveSubMode).toBe('compare');
  });

  it('compareDevices defaults to empty array', () => {
    expect(useAppStore.getState().compareDevices).toEqual([]);
  });

  it('setCompareDevices replaces the array', () => {
    useAppStore.getState().setCompareDevices(['e0101', 'e0202']);
    expect(useAppStore.getState().compareDevices).toEqual(['e0101', 'e0202']);
  });

  it('setCompareDevices enforces max 3 devices', () => {
    useAppStore.getState().setCompareDevices(['e0101', 'e0202', 'e0303', 'e0404']);
    expect(useAppStore.getState().compareDevices).toHaveLength(3);
  });
});

describe('useAppStore — timeRange all', () => {
  it('setTimeRange accepts all', () => {
    useAppStore.getState().setTimeRange('all');
    expect(useAppStore.getState().timeRange).toBe('all');
  });
});
