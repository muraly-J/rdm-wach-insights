import { useAppStore, initialState } from '../store/useAppStore';

// Reset store to initial state before each test
beforeEach(() => {
  useAppStore.setState(initialState);
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
