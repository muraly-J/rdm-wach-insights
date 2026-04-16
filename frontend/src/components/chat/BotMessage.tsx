import React, { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { NavigateTarget } from '../../api/client';
import type { ActionItem, ToolCall, AHUSummary, ChartCardData } from '../../types/chat';
import ChatChartModal, { ChartEntry } from './ChatChartModal';
import { replaceDeviceIds } from '../../utils/deviceNames';
import AgentReasoning from './AgentReasoning';
import WorkOrderCard from './cards/WorkOrderCard';
import AHUSummaryCard from './cards/AHUSummaryCard';
import ChartCard from './cards/ChartCard';

interface BotMessageProps {
  content: string;
  navigate?: NavigateTarget | null;
  onNavigate?: (target: NavigateTarget) => void;
  isLast?: boolean;
  onClearChat?: () => void;
  actions?: ActionItem[];
  tool_calls?: ToolCall[];
  ahu_summary?: AHUSummary | null;
  chart_data?: ChartCardData | null;
}

// Matches "e0301: 0.9%" (list format) or "| e0303 | 4.0 |" (markdown table format)
const DEVICE_VALUE_RE = /\b(e\d{4})\b[^:\n|]{0,20}[:|]\s*([\d.]+)\s*(%|kW|kWh|A|V|Hz)?/gi;

function extractChartData(
  text: string
): { entries: ChartEntry[]; unit: string; title: string } | null {
  const matches = [...text.matchAll(DEVICE_VALUE_RE)];
  if (matches.length < 3) return null;

  const seen = new Set<string>();
  const entries: ChartEntry[] = [];
  let unit = '';

  for (const m of matches) {
    const label = m[1];
    if (seen.has(label)) continue;
    seen.add(label);
    entries.push({ label, value: parseFloat(m[2]) });
    if (m[3] && !unit) unit = m[3];
  }

  if (entries.length < 3) return null;

  const titleMap: Record<string, string> = {
    '%': 'Percentage Values by Device',
    kW: 'Power (kW) by Device',
    kWh: 'Energy (kWh) by Device',
    A: 'Current (A) by Device',
    V: 'Voltage (V) by Device',
    Hz: 'Frequency (Hz) by Device',
  };
  const title = titleMap[unit] ?? 'Values by Device';

  return { entries, unit, title };
}

const BotMessage: React.FC<BotMessageProps> = ({
  content,
  navigate,
  onNavigate,
  isLast,
  onClearChat,
  actions,
  tool_calls,
  ahu_summary,
  chart_data,
}) => {
  const [showModal, setShowModal] = useState(false);

  const navigateLabel = navigate
    ? navigate.view === 'prediction' && navigate.device
      ? `View Predictions — ${navigate.device}`
      : navigate.device
        ? `Navigate to ${navigate.device} — Level ${navigate.level}`
        : `Navigate to Level ${navigate.level}`
    : null;

  const chartData = extractChartData(content);
  const showActions = isLast && (navigateLabel || onClearChat || chartData);

  return (
    <>
      <motion.div
        className="flex justify-start mb-4"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
      >
        <div className="max-w-[85%] flex flex-col gap-2">
          <div
            className="
              bg-[#222d3d]
              rounded-[16px_16px_16px_4px]
              px-4 py-3
            "
          >
            <div className="text-sm text-[#E8ECF1] leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{replaceDeviceIds(content)}</ReactMarkdown>
            </div>
          </div>

          {/* Agent reasoning */}
          {tool_calls && tool_calls.length > 0 && <AgentReasoning toolCalls={tool_calls} />}

          {/* Structured cards */}
          {ahu_summary && <AHUSummaryCard summary={ahu_summary} />}
          {chart_data && <ChartCard data={chart_data} />}
          {actions && actions.length > 0 && <WorkOrderCard actions={actions} />}

          {showActions && (
            <div className="flex items-center gap-2 flex-wrap">
              {chartData && (
                <button
                  onClick={() => setShowModal(true)}
                  className="
                    flex items-center gap-1.5
                    text-xs font-medium
                    text-[#4fbd95]
                    border border-[#4fbd95]/30
                    rounded-full
                    px-3 py-2.5 min-h-[44px]
                    hover:bg-[#4fbd95]/10
                    transition-colors duration-150
                  "
                >
                  <span>View Chart ↗</span>
                </button>
              )}

              {navigateLabel && onNavigate && navigate && (
                <button
                  onClick={() => onNavigate(navigate)}
                  className="
                    flex items-center gap-1.5
                    text-xs font-medium
                    text-[#4fbd95]
                    border border-[#4fbd95]/30
                    rounded-full
                    px-3 py-2.5 min-h-[44px]
                    hover:bg-[#4fbd95]/10
                    transition-colors duration-150
                  "
                >
                  <span>↗</span>
                  <span>{navigateLabel}</span>
                </button>
              )}

              {onClearChat && (
                <button
                  onClick={onClearChat}
                  className="
                    flex items-center gap-1.5
                    text-xs font-medium
                    text-[#6d6e71]
                    border border-[#6d6e71]/20
                    rounded-full
                    px-3 py-2.5 min-h-[44px]
                    hover:bg-[#6d6e71]/10
                    hover:text-[#E8ECF1]
                    transition-colors duration-150
                  "
                >
                  <span>✕</span>
                  <span>Clear Conversation</span>
                </button>
              )}
            </div>
          )}
        </div>
      </motion.div>

      {showModal && chartData && (
        <ChatChartModal
          title={chartData.title}
          entries={chartData.entries}
          unit={chartData.unit}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
};

export default BotMessage;
