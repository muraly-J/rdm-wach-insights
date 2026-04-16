import { useState, useCallback, useEffect } from 'react';
import type { Message } from '../types/chat';

const STORAGE_KEY = 'rdm-atlas-history';
const MAX_CONVERSATIONS = 50;

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convos: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convos.slice(0, MAX_CONVERSATIONS)));
}

export function useConversationHistory() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  const saveCurrentConversation = useCallback(
    (messages: Message[]) => {
      if (messages.length <= 1) return;

      const firstUserMsg = messages.find((m) => m.role === 'user');
      const title = firstUserMsg
        ? firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
        : 'New conversation';
      const now = new Date().toISOString();

      setConversations((prev) => {
        if (activeId) {
          return prev.map((c) =>
            c.id === activeId ? { ...c, messages, title, updatedAt: now } : c
          );
        }
        const newConvo: Conversation = {
          id: `conv-${Date.now()}`,
          title,
          messages,
          createdAt: now,
          updatedAt: now,
        };
        setActiveId(newConvo.id);
        return [newConvo, ...prev];
      });
    },
    [activeId]
  );

  const loadConversation = useCallback((id: string): Message[] | null => {
    const convo = conversations.find((c) => c.id === id);
    if (!convo) return null;
    setActiveId(id);
    return convo.messages;
  }, [conversations]);

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }, [activeId]);

  const startNewConversation = useCallback(() => {
    setActiveId(null);
  }, []);

  return {
    conversations,
    activeId,
    saveCurrentConversation,
    loadConversation,
    deleteConversation,
    startNewConversation,
  };
}
