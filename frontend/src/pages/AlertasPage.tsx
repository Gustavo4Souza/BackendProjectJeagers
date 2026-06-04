import { useState } from 'react'
import { useAlerts, useAcknowledgeAlert, useAcknowledgeAllAlerts, useAlertsWebSocket } from '../hooks/useAlerts'
import { useTanks } from '../hooks/useTanks'
import { TopBar } from '../components/layout/TopBar'
import { formatRelative } from '../utils/formatDateTime'
import { formatTemp } from '../utils/formatTemp'
import type { AlertFilters } from '../services/alerts'

type StatusFilter = 'active' | 'resolved' | 'all'
type PeriodFilter = '24h' | '7d' | '30d' | 'all'

const STATUS_LABELS: Record<StatusFilter, string> = {
  all: 'Todos',
  active: 'Ativos',
  resolved: 'Resolvidos',
}

const PERIOD_LABELS: Record<PeriodFilter, string> = {
  all: 'Todo o histórico',
  '24h': 'Últimas 24h',
  '7d': 'Últimos 7 dias',
  '30d': 'Últimos 30 dias',
}

function StatusBadge({ resolvedAt, acknowledgedBy }: { resolvedAt: string | null; acknowledgedBy: number | null }) {
  if (resolvedAt) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
        Resolvido
      </span>
    )
  }
  if (acknowledgedBy) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
        Reconhecido
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">
      Ativo
    </span>
  )
}

export default function AlertasPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active')
  const [tankFilter, setTankFilter] = useState<number | undefined>(undefined)
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>('all')

  useAlertsWebSocket()

  const filters: AlertFilters = {}
  if (statusFilter !== 'all') filters.status = statusFilter
  if (tankFilter !== undefined) filters.tank_id = tankFilter
  if (periodFilter !== 'all') filters.period = periodFilter

  const { data: alerts = [], isLoading } = useAlerts(filters)
  const { data: allActiveAlerts = [] } = useAlerts({ status: 'active' })
  const { data: tanks = [] } = useTanks()
  const { mutate: acknowledge, isPending: isAcknowledging } = useAcknowledgeAlert()
  const { mutate: acknowledgeAll, isPending: isAckingAll } = useAcknowledgeAllAlerts()

  const unacknowledgedCount = allActiveAlerts.filter((a) => !a.acknowledged_by).length

  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar alertCount={allActiveAlerts.length} />

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-lg font-semibold text-gray-900">Alertas</h1>

          {unacknowledgedCount > 0 && (
            <button
              onClick={() => acknowledgeAll()}
              disabled={isAckingAll}
              className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {isAckingAll ? 'Reconhecendo...' : `Reconhecer todos (${unacknowledgedCount})`}
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-4 items-end">
          {/* Status */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Status</p>
            <div className="flex gap-1">
              {(Object.keys(STATUS_LABELS) as StatusFilter[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    statusFilter === s ? 'text-white' : 'text-gray-500 hover:bg-gray-100'
                  }`}
                  style={statusFilter === s ? { backgroundColor: '#1D9E75' } : undefined}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
          </div>

          {/* Panela */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Panela</p>
            <select
              value={tankFilter ?? ''}
              onChange={(e) => setTankFilter(e.target.value ? Number(e.target.value) : undefined)}
              className="text-xs px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="">Todas as panelas</option>
              {tanks.map((t) => (
                <option key={t.id} value={t.id}>
                  Panela {t.id} · {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Período */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Período</p>
            <div className="flex gap-1">
              {(Object.keys(PERIOD_LABELS) as PeriodFilter[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriodFilter(p)}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    periodFilter === p ? 'text-white' : 'text-gray-500 hover:bg-gray-100'
                  }`}
                  style={periodFilter === p ? { backgroundColor: '#1D9E75' } : undefined}
                >
                  {p === 'all' ? 'Todos' : p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="p-8 flex justify-center">
              <div
                className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: '#1D9E75', borderTopColor: 'transparent' }}
              />
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-10 flex flex-col items-center gap-3 text-center">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: '#D1FAE5' }}>
                <svg className="w-5 h-5" style={{ color: '#1D9E75' }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">Nenhum alerta encontrado para os filtros selecionados</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Panela</th>
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Temperatura</th>
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Tipo</th>
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Disparado</th>
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Resolvido</th>
                    <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {alerts.map((alert) => (
                    <tr key={alert.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-medium text-gray-800">
                          {alert.tank_name || `Panela ${alert.tank_id}`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-700 font-mono">
                        {formatTemp(alert.temperature)}
                      </td>
                      <td className="px-4 py-3">
                        {alert.alert_type === 'above_max' ? (
                          <span className="flex items-center gap-1 text-red-600 text-xs">
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                            </svg>
                            Acima do máx.
                          </span>
                        ) : alert.alert_type === 'below_min' ? (
                          <span className="flex items-center gap-1 text-blue-600 text-xs">
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                            Abaixo do mín.
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {formatRelative(alert.fired_at)}
                        <span className="block text-gray-400">
                          {new Date(alert.fired_at).toLocaleString('pt-BR', {
                            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                          })}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {alert.resolved_at ? (
                          <>
                            {formatRelative(alert.resolved_at)}
                            <span className="block text-gray-400">
                              {new Date(alert.resolved_at).toLocaleString('pt-BR', {
                                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                              })}
                            </span>
                          </>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          resolvedAt={alert.resolved_at}
                          acknowledgedBy={alert.acknowledged_by}
                        />
                      </td>
                      <td className="px-4 py-3">
                        {!alert.resolved_at && !alert.acknowledged_by && (
                          <button
                            onClick={() => acknowledge(alert.id)}
                            disabled={isAcknowledging}
                            className="text-xs px-2.5 py-1 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors whitespace-nowrap"
                          >
                            Reconhecer
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer count */}
          {alerts.length > 0 && (
            <div className="border-t border-gray-100 px-4 py-2">
              <p className="text-xs text-gray-400">{alerts.length} alerta{alerts.length !== 1 ? 's' : ''} encontrado{alerts.length !== 1 ? 's' : ''}</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
