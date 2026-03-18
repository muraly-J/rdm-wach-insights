import { create } from 'zustand';
import { AppState, ChatMessage, DashboardData, FinancialImpact } from '../types';

// Default chat message for initial bot greeting
const INITIAL_BOT_MESSAGE: ChatMessage = {
  id: 'init-1',
  role: 'bot',
  content: "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
  timestamp: new Date(),
};

// Initial state matching spec Section 8.1
export const initialState: AppState = {
  selectedLevel: null,
  selectedDevice: null,
  chatOpen: false,
  chatMessages: [INITIAL_BOT_MESSAGE],
  dashboardData: null,
  isLoading: false,
};

export type TimeRange = '24h' | '7d' | '30d';

// Zustand store (from spec Section 8.1)
interface AppStore extends AppState {
  // Level selection
  selectLevel: (level: number) => void;

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
}

export const useAppStore = create<AppStore>((set) => ({
  ...initialState,

  // Time range (default 7 days)
  timeRange: '7d',
  setTimeRange: (range) => set({ timeRange: range }),

  // Level selection
  selectLevel: (level) => set({ selectedLevel: level, selectedDevice: null }),

  // Device selection
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  // Chat toggle
  toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),
  openChat: () => set({ chatOpen: true }),
  closeChat: () => set({ chatOpen: false }),

  // Chat messages
  addMessage: (message) => set((state) => ({
    chatMessages: [...state.chatMessages, message],
  })),
  setMessages: (messages) => set({ chatMessages: messages }),

  // Dashboard data
  setDashboardData: (data) => set({ dashboardData: data }),

  // Loading state
  setLoading: (loading) => set({ isLoading: loading }),

  // Financial impact
  financialImpact: null,
  setFinancialImpact: (data) => set({ financialImpact: data }),
}));
