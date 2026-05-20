import React from 'react';
import StateBadge from './StateBadge';
import { useGreyState, UseGreyStateInput } from '../../hooks/useGreyState';

interface GreyStateWrapperProps extends UseGreyStateInput {
  children: React.ReactNode;
  badgePlacement?: 'top-right' | 'top-left' | 'none';
  className?: string;
  style?: React.CSSProperties;
}

const GreyStateWrapper: React.FC<GreyStateWrapperProps> = ({
  children,
  badgePlacement = 'top-right',
  className,
  style,
  ...stateInput
}) => {
  const grey = useGreyState(stateInput);
  const showBadge = grey.isGrey && badgePlacement !== 'none' && grey.state;

  const overlayPos: React.CSSProperties =
    badgePlacement === 'top-left' ? { top: 8, left: 8 } : { top: 8, right: 8 };

  return (
    <div
      data-testid="grey-state-wrapper"
      className={className}
      style={{
        position: 'relative',
        opacity: grey.opacity,
        filter: grey.filter,
        transition: 'opacity 200ms ease, filter 200ms ease',
        ...style,
      }}
    >
      {children}
      {showBadge && (
        <div
          data-testid="grey-state-badge"
          style={{ position: 'absolute', zIndex: 5, ...overlayPos, filter: 'none', opacity: 1 }}
        >
          <StateBadge state={grey.state!} lastMeasured={grey.lastMeasured ?? undefined} />
        </div>
      )}
    </div>
  );
};

export default GreyStateWrapper;
