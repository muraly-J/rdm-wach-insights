import { useMemo } from 'react';
import type { OperationalState } from '../types';

export const STALE_HOURS = 6;
export const CONFIDENCE_MIN = 0.5;

export type GreyReason = 'off' | 'stale' | 'low_confidence';

export interface UseGreyStateInput {
  operationalState?: OperationalState;
  lastMeasured?: string | null;
  confidence?: number;
  isOn?: boolean;
}

export interface GreyStateResult {
  isGrey: boolean;
  reason: GreyReason | null;
  opacity: number;
  filter: string;
  state: OperationalState | undefined;
  lastMeasured: string | null | undefined;
}

function isOff(input: UseGreyStateInput): boolean {
  if (input.isOn === false) return true;
  const s = input.operationalState;
  return s === 'Off' || s === 'Inactive';
}

function isStale(
  lastMeasured: string | null | undefined,
  operationalState?: OperationalState
): boolean {
  if (operationalState === 'Off_Stale') return true;
  if (!lastMeasured) return false;
  const ageMs = Date.now() - new Date(lastMeasured).getTime();
  return ageMs > STALE_HOURS * 3600_000;
}

export function useGreyState(input: UseGreyStateInput): GreyStateResult {
  return useMemo(() => {
    let reason: GreyReason | null = null;
    if (isOff(input)) reason = 'off';
    else if (isStale(input.lastMeasured, input.operationalState)) reason = 'stale';
    else if (typeof input.confidence === 'number' && input.confidence < CONFIDENCE_MIN)
      reason = 'low_confidence';

    const isGrey = reason !== null;
    return {
      isGrey,
      reason,
      opacity: isGrey ? 0.4 : 1,
      filter: isGrey ? 'grayscale(85%) saturate(0.4)' : 'none',
      state: input.operationalState,
      lastMeasured: input.lastMeasured,
    };
  }, [input.operationalState, input.lastMeasured, input.confidence, input.isOn]);
}
