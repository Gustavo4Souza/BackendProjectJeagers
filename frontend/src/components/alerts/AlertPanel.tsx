import type { Alert } from '../../types'
import { formatRelative } from '../../utils/formatDateTime'
import { formatTemp } from '../../utils/formatTemp'

interface AlertPanelProps {
  alerts: Alert[]
  onAcknowledge: (alertId: number) => void
  isAcknowledging?: boolean
}

function AlertIcon({ type }: { type: Alert['type'] }) {
  if (type === 'above_max') {
    return (
      <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
          clipRule="evenodd"
        />
      </svg>
    )
  }
  return (
    <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-3 text-center">
      <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: '#D1FAE5' }}>
        <svg className="w-5 h-5" style={{ color: '#1D9E75' }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-700">Tudo certo</p>
        <p className="text-xs text-gray-400 mt-0.5">Nenhum alerta ativo</p>
      </div>
    </div>
  )
}

export function AlertPanel({ alerts, onAcknowledge, isAcknowledging }: AlertPanelProps) {
  const sorted = [...alerts].sort(
    (a, b) => new Date(b.fired_at).getTime() - new Date(a.fired_at).getTime()
  )

  return (
    <div className="bg-white rounded-xl border border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-800">Alertas ativos</h3>
        {alerts.length > 0 && (
          <span className="text-xs font-bold bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="divide-y divide-gray-50">
            {sorted.map((alert) => (
              <li key={alert.id} className="px-4 py-3 flex items-start gap-3">
                {/* Icon */}
                <div className="mt-0.5">
                  <AlertIcon type={alert.type} />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-gray-800 truncate">
                    {alert.tank_name}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {formatTemp(alert.temperature)} ·{' '}
                    {alert.type === 'above_max' ? 'acima do máximo' : 'abaixo do mínimo'}
                  </p>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    {formatRelative(alert.fired_at)}
                  </p>
                </div>

                {/* Acknowledge button */}
                <button
                  onClick={() => onAcknowledge(alert.id)}
                  disabled={isAcknowledging}
                  className="flex-shrink-0 text-xs text-gray-500 border border-gray-200 rounded-md px-2 py-1 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-colors"
                >
                  Reconhecer
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
