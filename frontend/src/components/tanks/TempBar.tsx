import type { TankStatus } from '../../types'

interface TempBarProps {
  temperature: number
  tempMin: number
  tempMax: number
  status: TankStatus
}

const BAR_COLOR: Record<TankStatus, string> = {
  normal: '#1D9E75',
  warning: '#EF9F27',
  alert: '#D85A30',
  offline: '#9CA3AF',
}

export function TempBar({ temperature, tempMin, tempMax, status }: TempBarProps) {
  const range = tempMax - tempMin
  const pct = range > 0
    ? Math.max(0, Math.min(100, ((temperature - tempMin) / range) * 100))
    : 0

  return (
    <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: BAR_COLOR[status] }}
      />
    </div>
  )
}
