import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface Toast {
    id: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
}

const COLORS: Record<string, { bg: string; text: string; icon: string }> = {
    success: { bg: '#00E5A020', text: '#00E5A0', icon: '✓' },
    error: { bg: '#FF4D4D20', text: '#FF4D4D', icon: '✕' },
    info: { bg: '#4DA6FF20', text: '#4DA6FF', icon: 'ℹ' },
    warning: { bg: '#FFA31A20', text: '#FFA31A', icon: '⚠' },
};

interface UseToastReturn {
    toasts: Toast[];
    addToast: (message: string, type?: 'success' | 'error' | 'info' | 'warning', duration?: number) => void;
    removeToast: (id: string) => void;
}

export function useToast(): UseToastReturn {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', duration = 4000) => {
        const id = Math.random().toString(36).substr(2, 9);
        const toast: Toast = { id, message, type, duration };

        setToasts((prev) => [...prev, toast]);

        if (duration > 0) {
            setTimeout(() => removeToast(id), duration);
        }
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return { toasts, addToast, removeToast };
}

interface ToastContainerProps {
    toasts: Toast[];
    onRemove: (id: string) => void;
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
    return (
        <div className= "fixed bottom-6 right-6 z-60 space-y-3 pointer-events-none" >
        <AnimatePresence mode="popLayout" >
        {
            toasts.map((toast) => {
                const color = COLORS[toast.type];
                return (
                    <motion.div
              key= { toast.id }
                initial = {{ opacity: 0, y: 16, x: 400 }
            }
              animate = {{ opacity: 1, y: 0, x: 0 }}
    exit = {{ opacity: 0, y: -8, x: 400 }
}
transition = {{ type: 'spring', damping: 20, stiffness: 300 }}
className = "pointer-events-auto"
    >
    <div
                className="px-4 py-3 rounded-lg border flex items-center gap-3"
style = {{
    background: color.bg,
        borderColor: color.text,
                }}
              >
    <span
                  className="text-lg font-bold"
style = {{ color: color.text }}
                >
    { color.icon }
    </span>
    < p
className = "text-sm"
style = {{ color: color.text }}
                >
    { toast.message }
    </p>
    < button
onClick = {() => onRemove(toast.id)}
className = "ml-2 opacity-70 hover:opacity-100"
style = {{ color: color.text }}
                >
                  ✕
</button>
    </div>
    </motion.div>
          );
        })}
</AnimatePresence>
    </div>
  );
}
