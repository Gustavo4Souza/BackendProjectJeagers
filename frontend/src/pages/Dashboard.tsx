import { useState } from 'react'
import { useTanks, useTankWebSocket, useUpdateTankConfig } from '../hooks/useTanks'
import { useAlerts, useAcknowledgeAlert, useAlertsWebSocket } from '../hooks/useAlerts'
import { useControlWebSocket } from '../hooks/useTankControl'
import { TopBar } from '../components/layout/TopBar'
import { TankGrid } from '../components/tanks/TankGrid'
import { TankHistoryChart } from '../components/chart/TankHistoryChart'
import { AlertPanel } from '../components/alerts/AlertPanel'
import { TankConfigModal } from '../components/tanks/TankConfigModal'
import { ErrorBanner } from '../components/base/ErrorBanner'

const TANK_IDS = [1, 2, 3, 4, 5, 6, 7, 8]

function TankWebSocketConnector({ tankId }: { tankId: number }) {
  useTankWebSocket(tankId)
  return null
}

function AlertsWebSocketConnector() {
  useAlertsWebSocket()
  return null
}

function ControlWebSocketConnector() {
  useControlWebSocket()
  return null
}

export default function Dashboard() {
  const [selectedTankId, setSelectedTankId] = useState<number>(1)
  const [configModalTankId, setConfigModalTankId] = useState<number | null>(null)

  const { data: tanks, isLoading: tanksLoading, error: tanksError, refetch } = useTanks()
  const { data: alerts = [] } = useAlerts()
  const { mutate: acknowledge, isPending: isAcknowledging } = useAcknowledgeAlert()
  const { mutate: updateConfig, isPending: isSaving, error: saveError, reset: resetSaveError } = useUpdateTankConfig()

  const selectedTank = tanks?.find((t) => t.id === selectedTankId)
  const configTank = configModalTankId !== null ? tanks?.find((t) => t.id === configModalTankId) : undefined

  function handleOpenConfig(tankId: number) {
    resetSaveError()
    setConfigModalTankId(tankId)
  }

  function handleSaveConfig(data: { name: string; temp_min: number; temp_max: number }) {
    if (!configModalTankId) return
    updateConfig(
      { id: configModalTankId, data },
      { onSuccess: () => setConfigModalTankId(null) }
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* WebSocket connectors — sem DOM */}
      {TANK_IDS.map((id) => (
        <TankWebSocketConnector key={id} tankId={id} />
      ))}
      <AlertsWebSocketConnector />
      <ControlWebSocketConnector />

      <TopBar alertCount={alerts.length} />

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-6">
        {tanksError && (
          <ErrorBanner
            message="Erro ao carregar panelas. Verifique a conexão com o backend."
            onRetry={() => refetch()}
          />
        )}

        {/* Tank cards grid */}
        <TankGrid
          tanks={tanks}
          isLoading={tanksLoading}
          selectedTankId={selectedTankId}
          onSelectTank={setSelectedTankId}
          onConfigTank={handleOpenConfig}
        />

        {/* Bottom section: chart + alerts */}
        <div className="grid grid-cols-3 gap-4 items-start">
          <div className="col-span-2">
            {selectedTank ? (
              <TankHistoryChart
                tankId={selectedTank.id}
                tankName={selectedTank.name}
                tempMin={selectedTank.temp_min}
                tempMax={selectedTank.temp_max}
              />
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-4 min-h-[200px] flex items-center justify-center">
                <p className="text-sm text-gray-400">Selecione uma panela para ver o histórico</p>
              </div>
            )}
          </div>

          <AlertPanel
            alerts={alerts}
            onAcknowledge={acknowledge}
            isAcknowledging={isAcknowledging}
          />
        </div>
      </main>

      {/* Config modal */}
      {configTank && (
        <TankConfigModal
          tank={configTank}
          onClose={() => setConfigModalTankId(null)}
          onSave={handleSaveConfig}
          isSaving={isSaving}
          saveError={saveError ? 'Erro ao salvar. Tente novamente.' : null}
        />
      )}
    </div>
  )
}
