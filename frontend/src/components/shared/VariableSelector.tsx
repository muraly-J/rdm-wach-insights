import React, { useState, useRef, useEffect } from 'react';
import type { MetricOption } from '../../types';

interface VariableSelectorProps {
  availableMetrics: MetricOption[];
  selectedMetrics: string[];
  onChange: (keys: string[]) => void;
  maxSelectable?: number;
  label?: string;
}

export default function VariableSelector({
  availableMetrics,
  selectedMetrics,
  onChange,
  maxSelectable = 5,
  label = 'Add Variables',
}: VariableSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggle = (key: string) => {
    if (selectedMetrics.includes(key)) {
      onChange(selectedMetrics.filter((k) => k !== key));
    } else if (selectedMetrics.length < maxSelectable) {
      onChange([...selectedMetrics, key]);
    }
  };

  const count = selectedMetrics.length;

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border transition-colors ${
          count > 0
            ? 'border-[#4fbd95] bg-[#4fbd95]/10 text-[#4fbd95]'
            : 'border-[#2e3f55] text-[#6d6e71] hover:border-[#2A3A4A]'
        }`}
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        {label}
        {count > 0 && (
          <span className="bg-[#4fbd95] text-[#1c2431] text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {count}
          </span>
        )}
      </button>

      {/* Popover */}
      {open && (
        <div className="absolute z-50 top-full mt-2 right-0 w-64 bg-[#2a3649] border border-[#2e3f55] rounded-xl shadow-2xl p-3">
          <p className="text-[10px] text-[#4A5568] mb-2 uppercase tracking-wider">
            Select up to {maxSelectable}
          </p>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {availableMetrics.map((m) => {
              const isSelected = selectedMetrics.includes(m.key);
              const isDisabled = !isSelected && count >= maxSelectable;
              return (
                <label
                  key={m.key}
                  className={`flex items-start gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${
                    isDisabled ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#1c2431]'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isDisabled}
                    onChange={() => toggle(m.key)}
                    className="mt-0.5 accent-[#4fbd95]"
                  />
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-white font-medium">{m.label}</span>
                      {m.unit && (
                        <span className="text-[10px] text-[#4A5568] border border-[#2e3f55] rounded px-1">
                          {m.unit}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-[#4A5568] leading-tight">{m.description}</p>
                  </div>
                </label>
              );
            })}
          </div>
          {count > 0 && (
            <button
              onClick={() => onChange([])}
              className="mt-2 w-full text-[10px] text-[#4A5568] hover:text-red-400 transition-colors"
            >
              Clear all
            </button>
          )}
        </div>
      )}
    </div>
  );
}
