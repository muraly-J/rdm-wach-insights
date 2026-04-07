// frontend/src/components/chat/ChatChartModal.tsx
import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'

export interface ChartEntry {
  label: string
  value: number
}

interface ChatChartModalProps {
  title: string
  entries: ChartEntry[]
  unit: string
  onClose: () => void
}

const ChatChartModal: React.FC<ChatChartModalProps> = ({ title, entries, unit, onClose }) => (
  <AnimatePresence>
    <motion.div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal panel */}
      <motion.div
        className="relative z-10 bg-[#1c2431] border border-[#1E2633] rounded-2xl
                   w-[min(90vw,900px)] h-[min(85vh,560px)] flex flex-col overflow-hidden"
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E2633] shrink-0">
          <h2 className="text-sm font-semibold text-[#E8ECF1] tracking-wide">{title}</h2>
          <button
            onClick={onClose}
            className="text-[#6d6e71] hover:text-[#E8ECF1] transition-colors text-base leading-none"
            aria-label="Close chart"
          >
            ✕
          </button>
        </div>

        {/* Chart */}
        <div className="flex-1 px-4 py-4 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={entries}
              margin={{ top: 8, right: 16, left: 8, bottom: 56 }}
            >
              <XAxis
                dataKey="label"
                tick={{ fill: '#6d6e71', fontSize: 10, fontFamily: 'Oswald, monospace' }}
                angle={-45}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fill: '#6d6e71', fontSize: 11 }}
                tickFormatter={(v: number) => `${v}${unit ? ' ' + unit : ''}`}
                width={60}
              />
              <Tooltip
                cursor={{ fill: 'rgba(79,189,149,0.05)' }}
                contentStyle={{
                  background: '#222d3d',
                  border: '1px solid #1E2633',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: '#E8ECF1', fontFamily: 'Oswald, monospace' }}
                itemStyle={{ color: '#4fbd95' }}
                formatter={(v: number) => [`${v}${unit ? ' ' + unit : ''}`, '']}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={40}>
                {entries.map((_, i) => (
                  <Cell key={i} fill="#4fbd95" fillOpacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </motion.div>
  </AnimatePresence>
)

export default ChatChartModal
