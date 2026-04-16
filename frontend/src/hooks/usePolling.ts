import { useCallback, useEffect, useRef, useState } from 'react';

interface UsePollingOptions {
    enabled?: boolean;
    interval?: number; // ms
    pauseWhenHidden?: boolean;
    onError?: (error: Error) => void;
    exponentialBackoff?: boolean;
}

export function usePolling<T>(
    fetcher: () => Promise<T>,
    interval: number = 5000,
    options: UsePollingOptions = {}
) {
    const {
        enabled = true,
        pauseWhenHidden = true,
        onError,
        exponentialBackoff = true,
    } = options;

    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const intervalRef = useRef<NodeJS.Timeout>();
    const backoffRef = useRef(1);

    const refetch = useCallback(async () => {
        try {
            const result = await fetcher();
            setData(result);
            setError(null);
            backoffRef.current = 1;
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err));
            setError(error);
            onError?.(error);
            if (exponentialBackoff) {
                backoffRef.current = Math.min(backoffRef.current * 2, 32);
            }
        }
    }, [fetcher, onError, exponentialBackoff]);

    useEffect(() => {
        if (!enabled) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            return;
        }

        // Check visibility
        const isVisible = () => {
            if (!pauseWhenHidden) return true;
            return !document.hidden;
        };

        // Initial fetch
        if (isVisible()) {
            refetch();
        }

        // Setup interval
        const currentInterval = exponentialBackoff ? interval * backoffRef.current : interval;
        intervalRef.current = setInterval(() => {
            if (isVisible()) {
                refetch();
            }
        }, currentInterval);

        // Visibility listener
        const handleVisibilityChange = () => {
            if (document.hidden) return;
            refetch();
        };

        if (pauseWhenHidden) {
            document.addEventListener('visibilitychange', handleVisibilityChange);
        }

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
            if (pauseWhenHidden) {
                document.removeEventListener('visibilitychange', handleVisibilityChange);
            }
        };
    }, [enabled, interval, pauseWhenHidden, refetch, exponentialBackoff]);

    return { data, error, refetch };
}
