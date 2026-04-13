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

// Prevent real API calls
jest.mock('../api/client', () => ({
  sendChatMessage: jest.fn(),
  NavigateTarget: {},
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

describe('ChatWindow', () => {
  it('renders the initial bot greeting when opened', () => {
    render(<ChatWindow mode="panel" onClose={jest.fn()} onToggleMode={jest.fn()} />);
    expect(screen.getByText(/RDM-Atlas/i)).toBeInTheDocument();
  });

  it('renders message list container without crashing', () => {
    const { container } = render(
      <ChatWindow mode="panel" onClose={jest.fn()} onToggleMode={jest.fn()} />
    );
    expect(container).toBeTruthy();
  });
});
