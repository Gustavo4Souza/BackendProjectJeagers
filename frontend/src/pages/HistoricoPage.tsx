import { useState, useMemo } from 'react'
import { useQueries } from '@tanstack/react-query'
import { useTanks } from '../hooks/useTanks'
import { readingsService } from '../services/readings'
import { TopBar } from '../components/layout/TopBar'
import { MultiTankHistoryChart } from '../components/chart/MultiTankHistoryChart'
import { useAlerts } from '../hooks/useAlerts'
import type { Reading } from '../types'

type Period = '6h' | '24h' | '7d' | '30d'

const PERIODS: { value: Period; label: string }[] = [
  { value: '6h', label: '6h' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
]

const MAX_TANKS = 4

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function HistoricoPage() {
  const [selectedIds, setSelectedIds] = useState<number[]>([1])
  const [period, setPeriod] = useState<Period>('24h')
  const [exportingId, setExportingId] = useState<number | null>(null)

  const { data: tanks = [] } = useTanks()
  const { data: activeAlerts = [] } = useAlerts()

  const queries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey: ['readings', id, period],
      queryFn: () => readingsService.getByTank(id, period),
      staleTime: 60_000,
    })),
  })

  const isLoading = queries.some((q) => q.isLoading)

  const readingsMap = useMemo(() => {
    const map = new Map<number, Reading[]>()
    selectedIds.forEach((id, idx) => {
      const data = queries[idx]?.data
      if (data) map.set(id, data)
    })
    return map
  }, [selectedIds, queries])

  function toggleTank(id: number) {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id)
      }
      if (prev.length >= MAX_TANKS) return prev
      return [...prev, id]
    })
  }

  async function handleExport(tankId: number) {
    setExportingId(tankId)
    try {
      const blob = await readingsService.exportCSV(tankId, period)
      downloadBlob(blob, `panela-${tankId}-${period}.csv`)
    } finally {
      setExportingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar alertCount={activeAlerts.length} />

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">Histórico de Temperaturas</h1>
        </div>

        {/* Controls row */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap items-start gap-6">
          {/* Tank selector */}
          <div className="flex-1 min-w-[260px]">
            <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
              Panelas (máx. {MAX_TANKS})
            </p>
            <div className="flex flex-wrap gap-2">
              {tanks.map((tank) => {
                const isSelected = selectedIds.includes(tank.id)
                const isDisabled = !isSelected && selectedIds.length >= MAX_TANKS
                return (
                  <button
                    key={tank.id}
                    onClick={() => toggleTank(tank.id)}
                    disabled={isDisabled}
                    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium transition-colors
                      ${isSelected
                        ? 'bg-green-50 border-green-400 text-green-700'
                        : isDisabled
                        ? 'border-gray-200 text-gray-300 cursor-not-allowed'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${isSelected ? 'bg-green-500' : 'bg-gray-300'}`}
                    />
                    {tank.id} · {tank.name}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Period selector */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Período</p>
            <div className="flex gap-1">
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    period === p.value
                      ? 'text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                  style={period === p.value ? { backgroundColor: '#1D9E75' } : undefined}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Export buttons */}
          {selectedIds.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Exportar CSV</p>
              <div className="flex flex-wrap gap-2">
                {selectedIds.map((id) => {
                  const tank = tanks.find((t) => t.id === id)
                  return (
                    <button
                      key={id}
                      onClick={() => handleExport(id)}
                      disabled={exportingId === id}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      {exportingId === id ? 'Exportando...' : `Panela ${id}${tank ? ' · ' + tank.name : ''}`}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Chart */}
        <MultiTankHistoryChart
          tankIds={selectedIds}
          tanks={tanks}
          readingsMap={readingsMap}
          period={period}
          isLoading={isLoading}
        />
      </main>
    </div>
  )
}
