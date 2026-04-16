import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

interface SuggestedPromptsProps {
  suggestions?: string[];
  onSelect: (prompt: string) => void;
  hasMessages: boolean;
}

function getInitialPrompts(level: number | null, device: string | null): string[] {
  const prompts: string[] = [];
  if (level) {
    prompts.push(`How is Level ${level} performing?`);
    prompts.push(`Any alerts on Level ${level}?`);
  } else {
    prompts.push('Which level has the most issues?');
    prompts.push('Show me site-wide health summary');
  }
  if (device && device !== 'all') {
    prompts.push(`What's wrong with ${device}?`);
    prompts.push(`Show predictions for ${device}`);
  }
  prompts.push('Show me the worst performing AHUs');
  prompts.push('Any maintenance recommendations?');
  return prompts.slice(0, 6);
}

export default function SuggestedPrompts({ suggestions, onSelect, hasMessages }: SuggestedPromptsProps) {
  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);

  const prompts = suggestions && suggestions.length > 0
    ? suggestions
    : !hasMessages
      ? getInitialPrompts(selectedLevel, selectedDevice)
      : [];

  if (!prompts.length) return null;

  return (
    <div className="flex gap-1.5 flex-wrap px-3 py-1.5">
      {prompts.map((prompt, i) => (
        <motion.button
          key={prompt}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(prompt)}
          className="bg-[#141920] border border-[#1a2638] rounded-full px-3 py-1 text-[11px] text-[#8899aa] cursor-pointer whitespace-nowrap hover:border-[#00E5A0] hover:text-[#E8ECF1] transition-colors"
          whileHover={{ borderColor: '#00E5A0', color: '#E8ECF1' }}
        >
          {prompt}
        </motion.button>
      ))}
    </div>
  );
}
