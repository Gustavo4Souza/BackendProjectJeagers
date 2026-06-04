import { useTankETA } from '../../hooks/useTankControl'

interface ETADisplayProps {
  tankId: number
}

function formatETA(minutes: number | null): string {
  if (minutes === null) return '—'
  if (minutes < 1) return '< 1 min'
  if (minutes < 60) return `~${Math.round(minutes)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `~${h}h ${m}min` : `~${h}h`
}

function formatRate(rate: number | null): string {
  if (rate === null) return '—'
  const sign = rate >= 0 ? '+' : ''
  return `${sign}${rate.toFixed(2)}°C/min`
}

export function ETADisplay({ tankId }: ETADisplayProps) {
  const { data, isLoading } = useTankETA(tankId)

  if (isLoading) {
    return (
      <div className="bg-gray-50 rounded-lg p-3 space-y-1 animate-pulse">
        <div className="h-3 bg-gray-200 rounded w-3/4" />
        <div className="h-3 bg-gray-200 rounded w-1/2" />
      </div>
    )
  }

  if (!data || !data.sufficient_data) {
    return (
      <div className="bg-gray-50 rounded-lg p-3">
        <p className="text-xs text-gray-400">
          {!data ? 'Dados de ETA indisponíveis' : 'Dados insuficientes — aguardando leituras'}
        </p>
      </div>
    )
  }

  return (
    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3 space-y-1">
      <p className="text-sm font-semibold text-emerald-800">
        Estimativa: {formatETA(data.eta_minutes)} para atingir {data.setpoint.toFixed(1)}°C
      </p>
      <p className="text-xs text-emerald-600">
        Taxa atual: {formatRate(data.rate_per_minute)}
      </p>
      {data.current_temp !== null && (
        <p className="text-xs text-emerald-600">
          Temperatura atual: {data.current_temp.toFixed(1)}°C
        </p>
      )}
    </div>
  )
}
