import { useState, useCallback, useRef } from 'react';
import { streamChat, sendChatMessage } from '../api/client';
import type { Message, ToolCall, ActionItem } from '../types/chat';

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
        const stream = streamChat(text, {
          level: context.level,
          device: context.device,
          financial_impact: context.financial_impact,
          history,
          persona: context.persona,
        });

        for await (const event of stream) {
          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === botMsgId);
            if (idx === -1) return prev;
            const msg = { ...updated[idx] };

            switch (event.type) {
              case 'text_delta':
                msg.content += event.data as string;
                break;
              case 'tool_call_start':
                msg.tool_calls = [...(msg.tool_calls ?? []), event.data as ToolCall];
                break;
              case 'tool_call_result': {
                const result = event.data as { name: string; result: string };
                msg.tool_calls = (msg.tool_calls ?? []).map((tc) =>
                  tc.name === result.name ? { ...tc, result: result.result } : tc
                );
                break;
              }
              case 'actions':
                msg.actions = event.data as ActionItem[];
                break;
              case 'navigate':
                msg.navigate = event.data as Message['navigate'];
                if (msg.navigate && options?.onNavigate) {
                  options.onNavigate(msg.navigate);
                }
                break;
              case 'suggestions':
                msg.suggestions = event.data as string[];
                break;
              case 'ahu_summary':
                msg.ahu_summary = event.data as Message['ahu_summary'];
                break;
              case 'chart_data':
                msg.chart_data = event.data as Message['chart_data'];
                break;
              case 'done':
                break;
            }

            updated[idx] = msg;
            return updated;
          });
        }
      } catch {
        // SSE failed — fall back to non-streaming
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
                  }
                : m
            )
          );
        } catch {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, content: 'Sorry, something went wrong. Please try again.' }
                : m
            )
          );
        }
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
