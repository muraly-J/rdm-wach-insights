import { useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

/**
 * Returns a `showToast(message, variant?, duration?)` function.
 * Toasts are stored in the Zustand store so ToastContainer can render them
 * from anywhere in the tree.
 */
export function useToast() {
  const addToast = useAppStore((s) => s.addToast);

  const showToast = useCallback(
    (message: string, variant: ToastVariant = 'info', duration = 4000) => {
      addToast({ id: `toast-${Date.now()}-${Math.random()}`, message, variant, duration });
    },
    [addToast]
  );

  return { showToast };
}
