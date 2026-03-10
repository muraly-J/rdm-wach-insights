import React from 'react';

type SkeletonShape = 'rect' | 'circle' | 'text' | 'card';
type SkeletonSize = 'sm' | 'md' | 'lg';

interface SkeletonProps {
  shape?: SkeletonShape;
  size?: SkeletonSize;
  className?: string;
}

/**
 * Skeleton - Loading state placeholder component
 * 
 * Uses shimmer animation with gradient from border-subtle to bg-tertiary
 */
const Skeleton: React.FC<SkeletonProps> = ({
  shape = 'rect',
  size = 'md',
  className = '',
}) => {
  // Base shimmer animation
  const baseStyles = 'shimmer bg-[#1E2A3A] animate-shimmer';

  // Shape-specific styles
  const shapeStyles: Record<SkeletonShape, string> = {
    rect: 'rounded',
    circle: 'rounded-full',
    text: 'h-4 rounded w-full',
    card: `rounded-[16px] p-[24px] bg-[#111820] border border-[#1E2A3A]`,
  };

  // Size-specific dimensions
  const sizeStyles: Record<SkeletonSize, string> = {
    sm: 'w-8 h-8',
    md: 'w-full h-16',
    lg: 'w-full h-48',
  };

  return (
    <div
      className={`
        ${baseStyles}
        ${shapeStyles[shape]}
        ${sizeStyles[size]}
        ${className}
      `}
    />
  );
};

/**
 * SkeletonCard - Full card skeleton with nested elements
 */
export const SkeletonCard: React.FC<{ header?: boolean; contentLines?: number }> = ({
  header = true,
  contentLines = 3,
}) => {
  return (
    <div className="card p-6 w-full">
      {header && (
        <div className="mb-4 flex justify-between items-center">
          <Skeleton shape="text" size="md" className="w-1/3 h-6" />
          <Skeleton shape="circle" size="sm" className="w-12 h-6" />
        </div>
      )}
      <div className="space-y-3">
        {Array.from({ length: contentLines }).map((_, i) => (
          <Skeleton key={i} shape="rect" size="md" className={`w-full h-4 ${i === contentLines - 1 ? 'w-2/3' : ''}`} />
        ))}
      </div>
    </div>
  );
};

/**
 * SkeletonChart - Chart placeholder with multiple data points
 */
export const SkeletonChart: React.FC<{ bars?: number }> = ({ bars = 5 }) => {
  return (
    <div className="card p-6 w-full h-[300px] flex items-end justify-between gap-2">
      {Array.from({ length: bars }).map((_, i) => {
        const height = 20 + Math.random() * 70;
        return (
          <div key={i} className="w-full bg-[#1E2A3A] rounded-t">
            <div
              className="shimmer bg-[#1A2230] w-full rounded-t"
              style={{ height: `${height}%` }}
            />
          </div>
        );
      })}
    </div>
  );
};

/**
 * SkeletonScoreCard - Score card with big number, sparkline, and trend
 */
export const SkeletonScoreCard: React.FC = () => {
  return (
    <div className="card p-6 w-full">
      <Skeleton shape="text" size="sm" className="w-32 h-5 mb-4" />
      <div className="flex items-baseline gap-3 mb-2">
        <Skeleton shape="rect" size="md" className="w-16 h-10 text-3xl font-mono" />
        <Skeleton shape="rect" size="sm" className="w-10 h-4 text-sm" />
      </div>
      <Skeleton shape="rect" size="md" className="w-full h-10 mb-2" />
      <div className="flex justify-between items-center">
        <Skeleton shape="rect" size="sm" className="w-20 h-3" />
        <Skeleton shape="circle" size="sm" className="w-4 h-4" />
      </div>
    </div>
  );
};

export default Skeleton;
