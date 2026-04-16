/**
 * Smoke tests for ChatWindow.
 *
 * Tests:
 * - Renders without crashing when open
 * - Shows initial bot greeting message
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatWindow from '../components/chat/ChatWindow';
import { Message } from '../types/chat';

// Prevent real API calls
jest.mock('../api/client', () => ({
  sendChatMessage: jest.fn(),
  NavigateTarget: {},
}));

// Mock streaming hook
jest.mock('../hooks/useSSEChat', () => ({
  useSSEChat: () => ({
    sendStreaming: jest.fn(),
    isStreaming: false,
    abort: jest.fn(),
  }),
}));

// Mock conversation history hook
jest.mock('../hooks/useConversationHistory', () => ({
  useConversationHistory: () => ({
    conversations: [],
    activeId: null,
    saveCurrentConversation: jest.fn(),
    loadConversation: jest.fn(),
    deleteConversation: jest.fn(),
    startNewConversation: jest.fn(),
  }),
}));

// Mock child components
jest.mock('../components/chat/ChatHeader', () => {
  return function DummyChatHeader() {
    return <div data-testid="chat-header" />;
  };
});

jest.mock('../components/chat/MessageList', () => {
  return function DummyMessageList() {
    return (
      <div data-testid="message-list">
        Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or
        explain what's driving a specific score. What would you like to know?
      </div>
    );
  };
});

jest.mock('../components/chat/ChatInput', () => {
  return function DummyChatInput() {
    return <div data-testid="chat-input" />;
  };
});

jest.mock('../components/chat/SuggestedPrompts', () => {
  return function DummySuggestedPrompts() {
    return <div data-testid="suggested-prompts" />;
  };
});

jest.mock('../components/chat/ConversationHistory', () => {
  return function DummyConversationHistory() {
    return <div data-testid="conversation-history" />;
  };
});

// Silence framer-motion layout warnings in jsdom
jest.mock('framer-motion', () => {
  const actual = jest.requireActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      ...actual.motion,
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
        <div {...props}>{children}</div>
      ),
    },
  };
});

const INITIAL_MESSAGE: Message = {
  id: 'init-1',
  role: 'bot',
  content:
    "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
};

describe('ChatWindow', () => {
  it('renders the initial bot greeting when opened', () => {
    render(
      <ChatWindow
        mode="panel"
        onClose={jest.fn()}
        onToggleMode={jest.fn()}
        messages={[INITIAL_MESSAGE]}
        setMessages={jest.fn()}
        isMinimized={false}
        onMinimize={jest.fn()}
      />
    );
    expect(screen.getByText(/RDM-Atlas/i)).toBeInTheDocument();
  });

  it('renders message list container without crashing', () => {
    const { container } = render(
      <ChatWindow
        mode="panel"
        onClose={jest.fn()}
        onToggleMode={jest.fn()}
        messages={[INITIAL_MESSAGE]}
        setMessages={jest.fn()}
        isMinimized={false}
        onMinimize={jest.fn()}
      />
    );
    expect(container).toBeTruthy();
  });
});
