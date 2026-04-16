import { useCallback, useEffect, useRef } from 'react';

interface UsePollingOptions {
  /** Base interval in ms (default 30 000) */
  interval?: number;
  /** Max backoff interval in ms (default 300 000 = 5 min) */
  maxInterval?: number;
  /** Backoff multiplier on consecutive errors (default 2) */
  backoffMultiplier?: number;
  /** Run immediately on mount before first interval elapses (default true) */
  runOnMount?: boolean;
  /** Pause polling when the tab is hidden (default true) */
  pauseOnHidden?: boolean;
  /** Only poll when enabled (default true) */
  enabled?: boolean;
}

/**
 * Calls `fn` on a recurring interval.
 * - Pauses when the tab is hidden and resumes when it becomes visible again.
 * - Applies exponential backoff on consecutive errors; resets on success.
 */
export function usePolling(
  fn: () => Promise<void> | void,
  options: UsePollingOptions = {}
): void {
  const {
    interval = 30_000,
    maxInterval = 300_000,
    backoffMultiplier = 2,
    runOnMount = true,
    pauseOnHidden = true,
    enabled = true,
  } = options;

  const fnRef = useRef(fn);
  fnRef.current = fn;

  const consecutiveErrors = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isHidden = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const schedule = useCallback(
    (delay: number) => {
      clearTimer();
      timerRef.current = setTimeout(async () => {
        if (isHidden.current) return; // don't fire while hidden; visibility handler will reschedule
        try {
          await fnRef.current();
          consecutiveErrors.current = 0;
          schedule(interval);
        } catch {
          consecutiveErrors.current += 1;
          const backoff = Math.min(
            interval * Math.pow(backoffMultiplier, consecutiveErrors.current),
            maxInterval
          );
          schedule(backoff);
        }
      }, delay);
    },
    [clearTimer, interval, maxInterval, backoffMultiplier]
  );

  useEffect(() => {
    if (!enabled) {
      clearTimer();
      return;
    }

    const run = async () => {
      try {
        await fnRef.current();
        consecutiveErrors.current = 0;
        schedule(interval);
      } catch {
        consecutiveErrors.current += 1;
        const backoff = Math.min(
          interval * Math.pow(backoffMultiplier, consecutiveErrors.current),
          maxInterval
        );
        schedule(backoff);
      }
    };

    if (runOnMount) {
      run();
    } else {
      schedule(interval);
    }

    if (pauseOnHidden) {
      const onVisibilityChange = () => {
        if (document.hidden) {
          isHidden.current = true;
          clearTimer();
        } else {
          isHidden.current = false;
          // Immediate catch-up poll then resume normal cadence
          run();
        }
      };
      document.addEventListener('visibilitychange', onVisibilityChange);
      return () => {
        document.removeEventListener('visibilitychange', onVisibilityChange);
        clearTimer();
      };
    }

    return clearTimer;
  }, [enabled, runOnMount, pauseOnHidden, interval, maxInterval, backoffMultiplier, schedule, clearTimer]);
}
