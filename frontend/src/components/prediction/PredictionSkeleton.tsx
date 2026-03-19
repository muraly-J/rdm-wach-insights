// frontend/src/components/prediction/PredictionSkeleton.tsx
export default function PredictionSkeleton() {
  return (
    <div className="w-full animate-pulse space-y-4 p-6 bg-[#131A23] rounded-xl border border-[#1E2A3A]">
      <div className="h-5 w-48 bg-[#1E2A3A] rounded" />
      <div className="h-64 w-full bg-[#1E2A3A] rounded-lg" />
      <div className="grid grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-[#1E2A3A] rounded-lg" />
        ))}
      </div>
    </div>
  );
}
