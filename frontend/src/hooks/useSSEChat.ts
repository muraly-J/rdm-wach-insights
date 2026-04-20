import { useState, useCallback, useRef } from 'react';
import { sendChatMessage } from '../api/client';
import type { Message, ActionItem } from '../types/chat';

interface UseSSEChatOptions {
  onNavigate?: (target: { level: number; device?: string; view?: string }) => void;
}

export function useSSEChat(options?: UseSSEChatOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendStreaming = useCallback(
    async (
      text: string,
      messages: Message[],
      setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
      context: {
        level?: number;
        device?: string | null;
        financial_impact?: number | null;
        persona?: string | null;
      }
    ) => {
      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
      };

      const botMsgId = `bot-${Date.now()}`;
      const botMsg: Message = {
        id: botMsgId,
        role: 'bot',
        content: '',
        tool_calls: [],
        actions: [],
        suggestions: [],
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);

      const history = messages
        .filter((m) => m.id !== messages[0]?.id)
        .map((m) => ({
          role: (m.role === 'bot' ? 'model' : 'user') as 'user' | 'model',
          content: m.content,
        }));

      try {
        const data = await sendChatMessage(text, {
          level: context.level,
          device: context.device,
          financial_impact: context.financial_impact,
          history,
          persona: context.persona,
        });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? {
                  ...m,
                  content: data.reply,
                  navigate: data.navigate ?? null,
                  actions: (data.actions as ActionItem[]) ?? [],
                }
              : m
          )
        );
        if (data.navigate && options?.onNavigate) {
          options.onNavigate(data.navigate);
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId
              ? { ...m, content: 'Sorry, something went wrong. Please try again.' }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [options]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { sendStreaming, isStreaming, abort };
}
