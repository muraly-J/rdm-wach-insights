import React from 'react';
import { useAppStore } from '../../store/useAppStore';

const WorkOrderBadge: React.FC = () => {
  const { workOrderDraftsCount, toggleWorkOrderPanel, workOrderPanelOpen } = useAppStore();

  return (
    <button
      onClick={toggleWorkOrderPanel}
      title={workOrderPanelOpen ? 'Close Work Orders' : 'Open Work Orders'}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        background: workOrderPanelOpen ? 'rgba(0,229,160,0.1)' : '#1a2234',
        border: `1px solid ${workOrderPanelOpen ? '#00E5A0' : '#2a3649'}`,
        borderRadius: 8,
        padding: '6px 12px',
        color: workOrderPanelOpen ? '#00E5A0' : '#8899aa',
        fontSize: 12,
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
        <rect x="9" y="3" width="6" height="4" rx="1" />
        <path d="M9 12h6M9 16h4" />
      </svg>
      Work Orders
      {workOrderDraftsCount > 0 && (
        <span
          style={{
            background: '#f59e0b',
            color: '#000',
            borderRadius: '50%',
            fontSize: 9,
            fontWeight: 700,
            minWidth: 16,
            height: 16,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 3px',
          }}
        >
          {workOrderDraftsCount > 99 ? '99+' : workOrderDraftsCount}
        </span>
      )}
    </button>
  );
};

export default WorkOrderBadge;
