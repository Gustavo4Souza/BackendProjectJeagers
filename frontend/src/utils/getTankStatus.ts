import type { Tank, TankStatus } from '../types'

export const STATUS_COLORS = {
  normal: {
    dot: '#1D9E75',
    border: 'border-gray-200',
    temp: 'text-gray-900',
    pill: 'bg-green-100 text-green-800',
    pillLabel: 'Normal',
  },
  warning: {
    dot: '#EF9F27',
    border: 'border-amber-400',
    temp: 'text-amber-700',
    pill: 'bg-amber-100 text-amber-800',
    pillLabel: 'Atenção',
  },
  alert: {
    dot: '#D85A30',
    border: 'border-red-500',
    temp: 'text-red-600',
    pill: 'bg-red-100 text-red-700',
    pillLabel: 'Alerta',
  },
  offline: {
    dot: '#9CA3AF',
    border: 'border-gray-200',
    temp: 'text-gray-400',
    pill: 'bg-gray-100 text-gray-500',
    pillLabel: 'Offline',
  },
} as const

export function getTankStatus(tank: Tank): TankStatus {
  if (!tank.current_temperature || !tank.last_reading_at) return 'offline'

  const lastReading = new Date(tank.last_reading_at)
  if (Date.now() - lastReading.getTime() > 30_000) return 'offline'

  const temp = tank.current_temperature
  if (temp > tank.temp_max || temp < tank.temp_min) return 'alert'
  if (temp > tank.temp_max - 0.5 || temp < tank.temp_min + 0.5) return 'warning'
  return 'normal'
}
