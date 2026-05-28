import { useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { useTankReadings } from '../../hooks/useTankReadings'
import { formatChartLabel } from '../../utils/formatDateTime'

type Period = '6h' | '24h' | '7d' | '30d'

interface TankHistoryChartProps {
  tankId: number
  tankName: string
  tempMin: number
  tempMax: number
}

interface ChartDataPoint {
  time: string
  temp: number
}

const PERIODS: { value: Period; label: string }[] = [
  { value: '6h', label: '6h' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
]

function CustomTooltip({
  active,
  payload,
  period,
}: {
  active?: boolean
  payload?: { value: number; payload: ChartDataPoint }[]
  period: Period
}) {
  if (!active || !payload?.length) return null
  const { value, payload: point } = payload[0]

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2">
      <p className="text-xs text-gray-400 mb-0.5">{formatChartLabel(point.time, period)}</p>
      <p className="text-sm font-semibold text-gray-900">{value.toFixed(1)}°C</p>
    </div>
  )
}

export function TankHistoryChart({ tankId, tankName, tempMin, tempMax }: TankHistoryChartProps) {
  const [period, setPeriod] = useState<Period>('24h')
  const { data: readings, isLoading } = useTankReadings(tankId, period)

  const chartData = readings?.map((r) => ({ time: r.recorded_at, temp: r.temperature })) ?? []

  const allTemps = chartData.map((d) => d.temp)
  const dataMin = allTemps.length ? Math.min(...allTemps) : tempMin
  const dataMax = allTemps.length ? Math.max(...allTemps) : tempMax
  const yMin = Math.min(dataMin, tempMin)
  const yMax = Math.max(dataMax, tempMax)
  const pad = (yMax - yMin) * 0.12 || 1

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-gray-800 min-w-0 truncate">
          Panela {tankId}
          {tankName && (
            <span className="text-gray-400 font-normal"> · {tankName}</span>
          )}
        </h3>

        <div className="flex items-center gap-1 flex-shrink-0">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${
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

      {/* Reference line legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed border-blue-400" />
          Mín {tempMin}°C
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-t-2 border-dashed border-red-400" />
          Máx {tempMax}°C
        </span>
      </div>

      {/* Chart area */}
      {isLoading ? (
        <div className="flex-1 min-h-[180px] bg-gray-50 animate-pulse rounded-lg" />
      ) : chartData.length === 0 ? (
        <div className="flex-1 min-h-[180px] flex items-center justify-center text-sm text-gray-400">
          Sem dados para o período selecionado
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />

            <XAxis
              dataKey="time"
              tickFormatter={(v: string) => formatChartLabel(v, period)}
              tick={{ fontSize: 11, fill: '#9CA3AF' }}
              tickLine={false}
              axisLine={false}
              minTickGap={48}
            />

            <YAxis
              domain={[yMin - pad, yMax + pad]}
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
                  payload={payload as unknown as { value: number; payload: ChartDataPoint }[] | undefined}
                  period={period}
                />
              )}
              cursor={{ stroke: '#E5E7EB', strokeWidth: 1 }}
            />

            <ReferenceLine
              y={tempMin}
              stroke="#60A5FA"
              strokeDasharray="5 3"
              strokeWidth={1.5}
            />
            <ReferenceLine
              y={tempMax}
              stroke="#F87171"
              strokeDasharray="5 3"
              strokeWidth={1.5}
            />

            <Line
              type="monotone"
              dataKey="temp"
              stroke="#1D9E75"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#1D9E75', strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
