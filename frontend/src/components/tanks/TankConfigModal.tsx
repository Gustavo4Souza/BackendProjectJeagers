import { useState, useEffect, useRef } from 'react'
import type { Tank } from '../../types'
import { useTankControl, useSetControl, useTankETA } from '../../hooks/useTankControl'
import { ETADisplay } from '../control/ETADisplay'

interface TankConfigModalProps {
  tank: Tank
  onClose: () => void
  onSave: (update: { name: string; temp_min: number; temp_max: number }) => void
  isSaving?: boolean
  saveError?: string | null
}

const MODE_PILL: Record<string, { label: string; cls: string }> = {
  cooling: { label: '↓ Resfriando', cls: 'bg-blue-100 text-blue-700' },
  heating: { label: '↑ Aquecendo', cls: 'bg-orange-100 text-orange-700' },
  idle: { label: '✓ Estável', cls: 'bg-green-100 text-green-700' },
}

export function TankConfigModal({ tank, onClose, onSave, isSaving, saveError }: TankConfigModalProps) {
  const [name, setName] = useState(tank.name)
  const [tempMin, setTempMin] = useState(String(tank.temp_min))
  const [tempMax, setTempMax] = useState(String(tank.temp_max))
  const [validationError, setValidationError] = useState<string | null>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  const { data: control } = useTankControl(tank.id)
  const setControlMutation = useSetControl(tank.id)
  const [setpointInput, setSetpointInput] = useState<string>(
    control ? String(control.setpoint) : ''
  )
  const [controlError, setControlError] = useState<string | null>(null)

  useEffect(() => {
    if (control && !setpointInput) {
      setSetpointInput(String(control.setpoint))
    }
  }, [control, setpointInput])

  function handleApplySetpoint() {
    setControlError(null)
    const val = parseFloat(setpointInput)
    if (isNaN(val)) {
      setControlError('Informe um valor numérico válido.')
      return
    }
    setControlMutation.mutate(val, {
      onError: () => setControlError('Erro ao aplicar setpoint. Tente novamente.'),
    })
  }

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setValidationError(null)

    const min = parseFloat(tempMin)
    const max = parseFloat(tempMax)

    if (isNaN(min) || isNaN(max)) {
      setValidationError('Informe valores numéricos válidos para a faixa de temperatura.')
      return
    }
    if (min >= max) {
      setValidationError('A temperatura mínima deve ser menor que a máxima.')
      return
    }

    onSave({ name: name.trim(), temp_min: min, temp_max: max })
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Configurar Panela {tank.id}</h2>
            <p className="text-xs text-gray-400 mt-0.5">{tank.location}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 -mr-1"
            aria-label="Fechar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-6">
          {/* Section 1 — Nome da bebida */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
              Nome da bebida
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Pilsen Lager, IPA Americana..."
              maxLength={50}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent"
              style={{ '--tw-ring-color': '#1D9E75' } as React.CSSProperties}
            />
            <p className="text-[11px] text-gray-400 text-right">{name.length}/50</p>
          </div>

          {/* Section 2 — Faixa de temperatura */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
              Faixa de temperatura (°C)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Mínima</label>
                <input
                  type="number"
                  value={tempMin}
                  onChange={(e) => { setTempMin(e.target.value); setValidationError(null) }}
                  step="0.1"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:border-transparent"
                  style={{ '--tw-ring-color': '#1D9E75' } as React.CSSProperties}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Máxima</label>
                <input
                  type="number"
                  value={tempMax}
                  onChange={(e) => { setTempMax(e.target.value); setValidationError(null) }}
                  step="0.1"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:border-transparent"
                  style={{ '--tw-ring-color': '#1D9E75' } as React.CSSProperties}
                />
              </div>
            </div>
            {validationError && (
              <p className="text-xs text-red-500 mt-1">{validationError}</p>
            )}
            {saveError && (
              <p className="text-xs text-red-500 mt-1">{saveError}</p>
            )}
          </div>

          {/* Section 3 — Controle de temperatura */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                Controle de temperatura
              </label>
              {control && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide ${MODE_PILL[control.mode]?.cls ?? 'bg-gray-100 text-gray-500'}`}>
                  {MODE_PILL[control.mode]?.label ?? control.mode}
                </span>
              )}
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs text-gray-500 mb-1 block">Temperatura alvo (°C)</label>
                <input
                  type="number"
                  value={setpointInput}
                  onChange={(e) => { setSetpointInput(e.target.value); setControlError(null) }}
                  step="0.5"
                  min="-20"
                  max="60"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:border-transparent"
                  style={{ '--tw-ring-color': '#1D9E75' } as React.CSSProperties}
                  placeholder="Ex: 8.0"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={handleApplySetpoint}
                  disabled={setControlMutation.isPending}
                  className="text-sm text-white rounded-lg px-4 py-2 font-medium transition-opacity disabled:opacity-60 whitespace-nowrap"
                  style={{ backgroundColor: '#1D9E75' }}
                >
                  {setControlMutation.isPending ? 'Aplicando...' : 'Aplicar setpoint'}
                </button>
              </div>
            </div>

            {controlError && (
              <p className="text-xs text-red-500">{controlError}</p>
            )}
            {setControlMutation.isSuccess && (
              <p className="text-xs text-green-600">Setpoint aplicado com sucesso.</p>
            )}

            <ETADisplay tankId={tank.id} />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 text-sm text-gray-600 border border-gray-200 rounded-lg py-2.5 hover:bg-gray-50 transition-colors font-medium"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 text-sm text-white rounded-lg py-2.5 font-medium transition-opacity disabled:opacity-60"
              style={{ backgroundColor: '#1D9E75' }}
            >
              {isSaving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
