import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { Tank, Reading } from '../../types'
import { formatChartLabel } from '../../utils/formatDateTime'

type Period = '6h' | '24h' | '7d' | '30d'

const TANK_COLORS = [
  '#1D9E75',
  '#3B82F6',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#06B6D4',
  '#EC4899',
  '#84CC16',
]

const BUCKET_MS = 30_000

function bucketTime(isoStr: string): number {
  return Math.round(new Date(isoStr).getTime() / BUCKET_MS) * BUCKET_MS
}

function mergeReadings(
  readingsMap: Map<number, Reading[]>,
): Record<string, number | string>[] {
  const buckets = new Map<number, Record<string, number | string>>()

  for (const [tankId, readings] of readingsMap) {
    for (const r of readings) {
      const ts = bucketTime(r.recorded_at)
      if (!buckets.has(ts)) {
        buckets.set(ts, { time: new Date(ts).toISOString() })
      }
      const bucket = buckets.get(ts)!
      const key = `temp_${tankId}`
      const existing = bucket[key] as number | undefined
      bucket[key] = existing === undefined ? r.temperature : (existing + r.temperature) / 2
    }
  }

  return Array.from(buckets.entries())
    .sort(([a], [b]) => a - b)
    .map(([, data]) => data)
}

interface MultiTankHistoryChartProps {
  tankIds: number[]
  tanks: Tank[]
  readingsMap: Map<number, Reading[]>
  period: Period
  isLoading: boolean
}

function CustomTooltip({
  active,
  payload,
  period,
  tanks,
}: {
  active?: boolean
  payload?: { dataKey: string; value: number; color: string }[]
  period: Period
  tanks: Tank[]
}) {
  if (!active || !payload?.length) return null
  const time = payload[0]?.payload?.time as string | undefined

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 min-w-[140px]">
      {time && (
        <p className="text-xs text-gray-400 mb-1">{formatChartLabel(time, period)}</p>
      )}
      {payload.map((entry) => {
        const tankId = Number(entry.dataKey.replace('temp_', ''))
        const tank = tanks.find((t) => t.id === tankId)
        return (
          <p key={entry.dataKey} className="text-xs font-medium" style={{ color: entry.color }}>
            {tank?.name ?? `Panela ${tankId}`}: {entry.value.toFixed(1)}°C
          </p>
        )
      })}
    </div>
  )
}

export function MultiTankHistoryChart({
  tankIds,
  tanks,
  readingsMap,
  period,
  isLoading,
}: MultiTankHistoryChartProps) {
  const chartData = mergeReadings(readingsMap)

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="h-[300px] bg-gray-50 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (tankIds.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 h-[300px] flex items-center justify-center">
        <p className="text-sm text-gray-400">Selecione ao menos uma panela</p>
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 h-[300px] flex items-center justify-center">
        <p className="text-sm text-gray-400">Sem dados para o período selecionado</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />

          <XAxis
            dataKey="time"
            tickFormatter={(v: string) => formatChartLabel(v, period)}
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            minTickGap={60}
          />

          <YAxis
            tickFormatter={(v: number) => `${v.toFixed(0)}°`}
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            width={36}
          />

          <Tooltip
            content={({ active, payload }) => (
              <CustomTooltip
                active={active}
                payload={payload as { dataKey: string; value: number; color: string }[] | undefined}
                period={period}
                tanks={tanks}
              />
            )}
            cursor={{ stroke: '#E5E7EB', strokeWidth: 1 }}
          />

          <Legend
            formatter={(value: string) => {
              const tankId = Number(value.replace('temp_', ''))
              const tank = tanks.find((t) => t.id === tankId)
              return (
                <span className="text-xs text-gray-600">
                  {tank?.name ?? `Panela ${tankId}`}
                </span>
              )
            }}
          />

          {tankIds.map((id, idx) => (
            <Line
              key={id}
              type="monotone"
              dataKey={`temp_${id}`}
              stroke={TANK_COLORS[idx % TANK_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              isAnimationActive={false}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
