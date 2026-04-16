import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolCall } from '../../types/chat';

interface AgentReasoningProps {
  toolCalls: ToolCall[];
}

export default function AgentReasoning({ toolCalls }: AgentReasoningProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!toolCalls.length) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="
          flex items-center gap-1
          text-[11px] font-mono text-[#556677]
          hover:text-[#8899aa]
          transition-colors duration-150
          p-0 bg-transparent border-none cursor-pointer
          select-none
        "
      >
        <span
          style={{
            display: 'inline-block',
            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 150ms ease',
            fontSize: 9,
            lineHeight: 1,
          }}
        >
          ▶
        </span>
        <span>
          {toolCalls.length} tool call{toolCalls.length > 1 ? 's' : ''}
        </span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div
              className="
                mt-1.5 px-2.5 py-2
                bg-[#0D1520]
                rounded-lg
                border border-[#1a2638]
                flex flex-col gap-1
              "
            >
              {toolCalls.map((tc, i) => (
                <div
                  key={i}
                  className="text-[11px] font-mono leading-relaxed"
                >
                  <span className="text-[#00E5A0]">{tc.name}</span>
                  <span className="text-[#556677]">
                    (
                    {Object.entries(tc.args)
                      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                      .join(', ')}
                    )
                  </span>
                  {tc.result && (
                    <span className="text-[#6d6e71]"> → {tc.result}</span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
