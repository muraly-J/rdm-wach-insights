import { create } from 'zustand';
import { AppState, ChatMessage, DashboardData, FinancialImpact, SiteSummaryData } from '../types';
import type { Toast } from '../hooks/useToast';
import type { Message } from '../types/chat';

// Default chat message for initial bot greeting
const INITIAL_BOT_MESSAGE: ChatMessage = {
  id: 'init-1',
  role: 'bot',
  content:
    "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
  timestamp: new Date(),
};

const INITIAL_CONVERSATION: Message[] = [
  {
    id: 'init-1',
    role: 'bot',
    content:
      "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
  },
];

// Initial state matching spec Section 8.1
export const initialState: AppState = {
  selectedLevel: null,
  selectedDevice: null,
  chatOpen: false,
  chatMessages: [INITIAL_BOT_MESSAGE],
  dashboardData: null,
  isLoading: false,
  heroVisible: true,
  dashboardMode: 'simple' as const,
  deepDiveSubMode: 'single' as const,
  compareDevices: [] as string[],
  chatMode: 'panel' as const,
  workOrderPanelOpen: false,
  workOrderDraftsCount: 0,
};

export type TimeRange = '24h' | '7d' | '30d' | 'all';
export type DashboardMode = 'simple' | 'deepdive' | 'workorders';
export type DeepDiveSubMode = 'single' | 'compare';

// Zustand store (from spec Section 8.1)
interface AppStore extends AppState {
  // Level selection
  selectLevel: (level: number | null) => void;
  clearLevel: () => void;

  // Device selection
  selectDevice: (deviceId: string | null) => void;

  // Time range
  timeRange: TimeRange;
  setTimeRange: (range: TimeRange) => void;

  // Chat toggle
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;

  // Chat messages
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;

  // Dashboard data
  setDashboardData: (data: DashboardData | null) => void;

  // Loading state
  setLoading: (loading: boolean) => void;

  // Financial impact (latest loaded, passed to chat)
  financialImpact: FinancialImpact | null;
  setFinancialImpact: (data: FinancialImpact | null) => void;

  // Hamburger menu
  hamburgerOpen: boolean;
  toggleHamburger: () => void;

  // Site summary
  siteSummaryData: SiteSummaryData | null;
  setSiteSummaryData: (d: SiteSummaryData) => void;

  // Hero visibility
  heroVisible: boolean;
  setHeroVisible: (visible: boolean) => void;

  // Dashboard mode
  dashboardMode: DashboardMode;
  setDashboardMode: (mode: DashboardMode) => void;

  // Deep dive sub-mode
  deepDiveSubMode: DeepDiveSubMode;
  setDeepDiveSubMode: (mode: DeepDiveSubMode) => void;

  // Compare devices
  compareDevices: string[];
  setCompareDevices: (devices: string[]) => void;

  // Chat mode
  chatMode: 'panel' | 'fullscreen' | 'split';
  setChatMode: (mode: 'panel' | 'fullscreen' | 'split') => void;

  // Chat conversation (persists across mode changes)
  chatConversation: Message[];
  setChatConversation: (messages: Message[]) => void;

  // Work order panel
  workOrderPanelOpen: boolean;
  toggleWorkOrderPanel: () => void;
  setWorkOrderPanelOpen: (open: boolean) => void;

  // Work order drafts count (badge on mode toggle)
  workOrderDraftsCount: number;
  setWorkOrderDraftsCount: (count: number) => void;

  // Toast notifications
  toasts: Toast[];
  addToast: (toast: Toast) => void;
  removeToast: (id: string) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  ...initialState,

  // Time range (default 7 days)
  /** Get the current time range filter for dashboard data */
  timeRange: '7d',
  /** Set the time range filter for dashboard data */
  setTimeRange: (range) => set({ timeRange: range }),

  // Level selection
  /** Select a building level and reset device selection */
  selectLevel: (level) => set({ selectedLevel: level, selectedDevice: null }),
  /** Clear the selected level and device */
  clearLevel: () => set({ selectedLevel: null, selectedDevice: null }),

  // Device selection
  /** Select a specific AHU device */
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // Chat toggle
  /** Toggle chat panel open/closed state */
  toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),
  /** Open the chat panel */
  openChat: () => set({ chatOpen: true }),
  /** Close the chat panel */
  closeChat: () => set({ chatOpen: false }),

  // Chat messages
  /** Add a new message to the chat history */
  addMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),
  /** Replace all chat messages at once */
  setMessages: (messages) => set({ chatMessages: messages }),

  // Dashboard data
  /** Set the current dashboard data */
  setDashboardData: (data) => set({ dashboardData: data }),

  // Loading state
  /** Set the loading state for data fetches */
  setLoading: (loading) => set({ isLoading: loading }),

  // Financial impact
  /** Get the latest financial impact data */
  financialImpact: null,
  /** Set the financial impact data */
  setFinancialImpact: (data) => set({ financialImpact: data }),

  // Hamburger menu
  /** Get the hamburger menu open state */
  hamburgerOpen: false,
  /** Toggle hamburger menu open/closed state */
  toggleHamburger: () => set((state) => ({ hamburgerOpen: !state.hamburgerOpen })),

  // Site summary
  /** Get the site-wide summary data */
  siteSummaryData: null,
  /** Set the site-wide summary data */
  setSiteSummaryData: (d) => set({ siteSummaryData: d }),

  // Hero visibility
  /** Set hero section visibility on dashboard */
  setHeroVisible: (visible) => set({ heroVisible: visible }),

  // Dashboard mode
  /** Get the current dashboard mode (simple or deepdive) */
  dashboardMode: 'simple',
  /** Set the dashboard mode (simple or deepdive) */
  setDashboardMode: (mode) => set({ dashboardMode: mode }),

  // Deep dive sub-mode
  /** Get the deep dive view sub-mode (single or compare) */
  deepDiveSubMode: 'single',
  /** Set the deep dive view sub-mode (single device or compare multiple) */
  setDeepDiveSubMode: (mode) => set({ deepDiveSubMode: mode }),

  // Compare devices
  /** Get list of devices selected for comparison (max 3) */
  compareDevices: [],
  /** Set devices for comparison view, limited to 3 devices */
  setCompareDevices: (devices) => set({ compareDevices: devices.slice(0, 3) }),

  // Chat mode
  /** Get the current chat display mode (panel, fullscreen, or split) */
  chatMode: 'panel',
  /** Set the chat display mode (panel, fullscreen, or split) */
  setChatMode: (mode) => set({ chatMode: mode }),

  // Chat conversation (persists across mode changes)
  chatConversation: INITIAL_CONVERSATION,
  setChatConversation: (messages) => set({ chatConversation: messages }),

  // Work order panel
  workOrderPanelOpen: false,
  toggleWorkOrderPanel: () => set((state) => ({ workOrderPanelOpen: !state.workOrderPanelOpen })),
  setWorkOrderPanelOpen: (open) => set({ workOrderPanelOpen: open }),

  // Work order drafts count
  workOrderDraftsCount: 0,
  setWorkOrderDraftsCount: (count) => set({ workOrderDraftsCount: count }),

  // Toast notifications
  toasts: [],
  addToast: (toast) => set((state) => ({ toasts: [...state.toasts, toast] })),
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
