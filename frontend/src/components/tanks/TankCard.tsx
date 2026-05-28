import type { Tank } from '../../types'
import { getTankStatus } from '../../utils/getTankStatus'
import { formatTemp } from '../../utils/formatTemp'
import { formatRelative } from '../../utils/formatDateTime'
import { TempBar } from './TempBar'

interface TankCardProps {
  tank: Tank
  isSelected: boolean
  onSelect: () => void
  onConfig: () => void
}

const DOT_COLOR: Record<ReturnType<typeof getTankStatus>, string> = {
  normal: '#1D9E75',
  warning: '#EF9F27',
  alert: '#D85A30',
  offline: '#9CA3AF',
}

const BORDER_COLOR: Record<ReturnType<typeof getTankStatus>, string> = {
  normal: '#E5E7EB',
  warning: '#EF9F27',
  alert: '#D85A30',
  offline: '#E5E7EB',
}

const TEMP_CLASS: Record<ReturnType<typeof getTankStatus>, string> = {
  normal: 'text-gray-900',
  warning: 'text-amber-700',
  alert: 'text-red-600',
  offline: 'text-gray-400',
}

const PILL_CLASS: Record<ReturnType<typeof getTankStatus>, string> = {
  normal: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  alert: 'bg-red-100 text-red-700',
  offline: 'bg-gray-100 text-gray-500',
}

const PILL_LABEL: Record<ReturnType<typeof getTankStatus>, string> = {
  normal: 'Normal',
  warning: 'Atenção',
  alert: 'Alerta',
  offline: 'Offline',
}

export function TankCard({ tank, isSelected, onSelect, onConfig }: TankCardProps) {
  const status = getTankStatus(tank)
  const isOffline = status === 'offline'

  const cardStyle: React.CSSProperties = {
    borderColor: BORDER_COLOR[status],
    borderWidth: status === 'warning' || status === 'alert' ? '2px' : '1px',
    outline: isSelected ? '2px solid #1D9E75' : undefined,
    outlineOffset: isSelected ? '2px' : undefined,
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === 'Enter' && onSelect()}
      className="bg-white rounded-xl border p-4 cursor-pointer transition-shadow hover:shadow-md focus:outline-none select-none"
      style={cardStyle}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
            style={{ backgroundColor: DOT_COLOR[status] }}
          />
          <span className="text-xs text-gray-400 font-medium">Panela {tank.id}</span>
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); onConfig() }}
          className="text-gray-300 hover:text-gray-500 transition-colors p-0.5 -mt-0.5 -mr-0.5"
          aria-label="Configurar panela"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      {/* Drink name */}
      <p className="text-sm font-semibold text-gray-800 truncate mb-3 min-h-[1.25rem]">
        {tank.name || <span className="text-gray-400 font-normal italic">Sem nome</span>}
      </p>

      {/* Temperature */}
      <p className={`text-3xl font-bold tabular-nums leading-none mb-3 ${TEMP_CLASS[status]}`}>
        {isOffline ? '—' : formatTemp(tank.current_temperature)}
      </p>

      {/* TempBar */}
      {!isOffline && tank.current_temperature !== null ? (
        <TempBar
          temperature={tank.current_temperature}
          tempMin={tank.temp_min}
          tempMax={tank.temp_max}
          status={status}
        />
      ) : (
        <div className="w-full h-1 bg-gray-100 rounded-full" />
      )}

      {/* Footer: pill + last reading */}
      <div className="flex items-center justify-between mt-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PILL_CLASS[status]}`}>
          {PILL_LABEL[status]}
        </span>
        {tank.last_reading_at && !isOffline && (
          <span className="text-xs text-gray-400">
            {formatRelative(tank.last_reading_at)}
          </span>
        )}
      </div>
    </div>
  )
}
