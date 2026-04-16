import { motion } from 'framer-motion';
import type { Conversation } from '../../hooks/useConversationHistory';

interface ConversationHistoryProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

function groupByDate(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const c of conversations) {
    const d = new Date(c.updatedAt);
    if (d >= today) groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else if (d >= weekAgo) groups[2].items.push(c);
    else groups[3].items.push(c);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
}: ConversationHistoryProps) {
  const groups = groupByDate(conversations);

  return (
    <div className="w-[220px] border-r border-[#1a2638] bg-[#0B0F14] flex flex-col h-full overflow-hidden">
      <button
        onClick={onNewChat}
        className="m-2.5 mb-1.5 bg-[#00E5A0] text-[#0B0F14] border-none rounded-lg py-1.5 text-[12px] font-semibold cursor-pointer hover:bg-[#00c98a] transition-colors"
      >
        + New Chat
      </button>

      <div className="flex-1 overflow-y-auto px-1.5 scrollbar-hidden">
        {groups.length === 0 && (
          <div className="text-[11px] text-[#556677] text-center pt-4">No conversations yet</div>
        )}
        {groups.map((group) => (
          <div key={group.label}>
            <div className="text-[9px] text-[#556677] uppercase tracking-wide px-1.5 pt-2.5 pb-1 font-semibold">
              {group.label}
            </div>
            {group.items.map((convo) => (
              <motion.div
                key={convo.id}
                onClick={() => onSelect(convo.id)}
                className="px-2 py-1.5 rounded-md text-[11px] cursor-pointer flex justify-between items-center mb-px"
                style={{
                  color: convo.id === activeId ? '#E8ECF1' : '#8899aa',
                  background: convo.id === activeId ? '#141920' : 'transparent',
                }}
                whileHover={{ background: '#141920' }}
              >
                <span className="overflow-hidden text-ellipsis whitespace-nowrap flex-1">
                  {convo.title}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(convo.id); }}
                  className="bg-transparent border-none text-[#556677] cursor-pointer text-[12px] px-0.5 opacity-50 hover:opacity-100 flex-shrink-0 ml-1"
                >
                  ×
                </button>
              </motion.div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
