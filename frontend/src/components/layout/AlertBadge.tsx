interface AlertBadgeProps {
  count: number
}

export function AlertBadge({ count }: AlertBadgeProps) {
  if (count === 0) return null

  return (
    <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full px-1 leading-none">
      {count > 99 ? '99+' : count}
    </span>
  )
}
