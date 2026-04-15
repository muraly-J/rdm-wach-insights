interface DataFreshnessIndicatorProps {
  dataAsOf: string | null;
}

function formatTimeAgo(isoString: string): string {
  const then = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export default function DataFreshnessIndicator({ dataAsOf }: DataFreshnessIndicatorProps) {
  if (!dataAsOf) return null;

  return (
    <span className="text-xs text-gray-500 font-mono">Data as of {formatTimeAgo(dataAsOf)}</span>
  );
}
