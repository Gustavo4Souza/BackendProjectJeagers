interface LoadingSkeletonProps {
  className?: string
}

export function LoadingSkeleton({ className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
  )
}

export function TankCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="flex justify-between">
        <LoadingSkeleton className="h-3 w-12" />
        <LoadingSkeleton className="h-4 w-4 rounded-full" />
      </div>
      <LoadingSkeleton className="h-5 w-3/4" />
      <LoadingSkeleton className="h-8 w-1/2" />
      <LoadingSkeleton className="h-1 w-full rounded-full" />
      <LoadingSkeleton className="h-5 w-16 rounded-full" />
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <div className="flex justify-between items-center">
        <LoadingSkeleton className="h-5 w-48" />
        <div className="flex gap-2">
          {[...Array(4)].map((_, i) => (
            <LoadingSkeleton key={i} className="h-7 w-10 rounded-md" />
          ))}
        </div>
      </div>
      <LoadingSkeleton className="h-48 w-full rounded-lg" />
    </div>
  )
}
