import { useCallback, useEffect, useRef, useState } from 'react';
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
  // Ref tracks activeId synchronously so saveCurrentConversation never sees a stale value
  // between two rapid state updates (user msg + bot response in the same tick).
  const activeIdRef = useRef<string | null>(null);

  const _setActiveId = useCallback((id: string | null) => {
    activeIdRef.current = id;
    setActiveId(id);
  }, []);

  // Debounced save to localStorage (only after 1s of inactivity)
  useEffect(() => {
    const timeout = setTimeout(() => {
      saveConversations(conversations);
    }, 1000);

    return () => clearTimeout(timeout);
  }, [conversations]);

  const saveCurrentConversation = useCallback((messages: Message[]) => {
    if (messages.length <= 1) return;

    const firstUserMsg = messages.find((m) => m.role === 'user');
    const title = firstUserMsg
      ? firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
      : 'New conversation';
    const now = new Date().toISOString();

    setConversations((prev) => {
      const currentId = activeIdRef.current;
      if (currentId) {
        return prev.map((c) =>
          c.id === currentId ? { ...c, messages, title, updatedAt: now } : c
        );
      }

      const newConvo: Conversation = {
        id: `conv-${Date.now()}`,
        title,
        messages,
        createdAt: now,
        updatedAt: now,
      };
      // Update ref synchronously so the next call in the same tick sees the new id
      activeIdRef.current = newConvo.id;
      setActiveId(newConvo.id);
      return [newConvo, ...prev];
    });
  }, []);

  const loadConversation = useCallback(
    (id: string): Message[] | null => {
      const convo = conversations.find((c) => c.id === id);
      if (!convo) return null;
      _setActiveId(id);
      return convo.messages;
    },
    [conversations, _setActiveId]
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeIdRef.current === id) _setActiveId(null);
    },
    [_setActiveId]
  );

  const startNewConversation = useCallback(() => {
    _setActiveId(null);
  }, [_setActiveId]);

  return {
    conversations,
    activeId,
    saveCurrentConversation,
    loadConversation,
    deleteConversation,
    startNewConversation,
  };
}
