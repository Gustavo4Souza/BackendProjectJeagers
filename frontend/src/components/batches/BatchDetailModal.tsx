import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { batchesService, type CreateBatchEventPayload } from '../../services/batches'
import type { BatchDetail, BatchStatus, YeastProfile } from '../../types'

const STATUS_LABELS: Record<BatchStatus, string> = {
  planned: 'Planejado',
  active: 'Em Fermentação',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

const STATUS_COLORS: Record<BatchStatus, string> = {
  planned: 'bg-gray-100 text-gray-600',
  active: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-600',
}

const EVENT_TYPES = [
  'pitch',
  'dry hop',
  'cold crash',
  'lautering',
  'transferência',
  'adição de adjunto',
  'medição de gravidade',
  'outro',
]

function formatDate(dateStr: string | null) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface AddEventFormProps {
  batchId: number
  onDone: () => void
}

function AddEventForm({ batchId, onDone }: AddEventFormProps) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<CreateBatchEventPayload>({
    event_type: 'pitch',
    description: '',
    value: undefined,
    unit: '',
    occurred_at: new Date().toISOString().slice(0, 16),
  })
  const [error, setError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation({
    mutationFn: (data: CreateBatchEventPayload) => batchesService.addEvent(batchId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] })
      onDone()
    },
    onError: () => setError('Erro ao adicionar evento'),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.description.trim()) { setError('Descrição obrigatória'); return }
    setError(null)
    mutate({
      ...form,
      value: form.value !== undefined && form.value !== null && !isNaN(Number(form.value)) ? Number(form.value) : undefined,
      unit: form.unit || undefined,
      occurred_at: form.occurred_at ? new Date(form.occurred_at).toISOString() : undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 bg-gray-50 rounded-lg p-4 space-y-3 border border-gray-200">
      <p className="text-xs font-semibold text-gray-700">Novo Evento</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Tipo</label>
          <select
            value={form.event_type}
            onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Data/Hora</label>
          <input
            type="datetime-local"
            value={form.occurred_at as string}
            onChange={(e) => setForm((f) => ({ ...f, occurred_at: e.target.value }))}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-400"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">Descrição</label>
        <input
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-400"
          placeholder="Descreva o evento..."
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Valor (opcional)</label>
          <input
            type="number"
            step="any"
            value={form.value ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, value: e.target.value === '' ? undefined : parseFloat(e.target.value) }))}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-400"
            placeholder="ex: 1.050"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Unidade (opcional)</label>
          <input
            value={form.unit ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-400"
            placeholder="ex: SG, g, L"
          />
        </div>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={onDone}
          className="text-xs px-3 py-1.5 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-100 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="text-xs px-3 py-1.5 rounded-md text-white disabled:opacity-50 transition-colors"
          style={{ backgroundColor: '#1D9E75' }}
        >
          {isPending ? 'Salvando...' : 'Adicionar'}
        </button>
      </div>
    </form>
  )
}

interface BatchDetailModalProps {
  batchId: number
  onClose: () => void
  yeastProfiles: YeastProfile[]
}

export function BatchDetailModal({ batchId, onClose, yeastProfiles }: BatchDetailModalProps) {
  const queryClient = useQueryClient()
  const [showAddEvent, setShowAddEvent] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<BatchDetail>>({})
  const [editError, setEditError] = useState<string | null>(null)

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => batchesService.getById(batchId),
  })

  const { mutate: updateBatch, isPending: isUpdating } = useMutation({
    mutationFn: (data: Partial<BatchDetail>) => batchesService.update(batchId, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['batch', batchId], updated)
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      setEditing(false)
      setEditError(null)
    },
    onError: () => setEditError('Erro ao atualizar lote'),
  })

  function startEditing() {
    if (!batch) return
    setEditForm({
      name: batch.name,
      style: batch.style,
      status: batch.status,
      fermenter_id: batch.fermenter_id ?? '',
      original_gravity: batch.original_gravity ?? undefined,
      final_gravity: batch.final_gravity ?? undefined,
      volume_liters: batch.volume_liters ?? undefined,
      yeast_profile_id: batch.yeast_profile_id ?? undefined,
      notes: batch.notes ?? '',
    })
    setEditing(true)
  }

  function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault()
    const payload: Record<string, unknown> = {}
    if (editForm.name !== undefined) payload.name = editForm.name
    if (editForm.style !== undefined) payload.style = editForm.style
    if (editForm.status !== undefined) payload.status = editForm.status
    if (editForm.fermenter_id !== undefined) payload.fermenter_id = editForm.fermenter_id || null
    if (editForm.original_gravity !== undefined) payload.original_gravity = editForm.original_gravity || null
    if (editForm.final_gravity !== undefined) payload.final_gravity = editForm.final_gravity || null
    if (editForm.volume_liters !== undefined) payload.volume_liters = editForm.volume_liters || null
    if (editForm.yeast_profile_id !== undefined) payload.yeast_profile_id = editForm.yeast_profile_id || null
    if (editForm.notes !== undefined) payload.notes = editForm.notes || null
    updateBatch(payload as Partial<BatchDetail>)
  }

  function handleExport() {
    if (!batch) return
    batchesService.exportCsv(batch.id).then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `lote-${batch.id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 pt-10 pb-6 px-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div>
            {isLoading ? (
              <div className="h-5 w-48 bg-gray-200 animate-pulse rounded" />
            ) : (
              <>
                <h2 className="text-base font-semibold text-gray-900">{batch?.name}</h2>
                <p className="text-xs text-gray-400 mt-0.5">{batch?.style}</p>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {batch && !editing && (
              <>
                <button
                  onClick={handleExport}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  CSV
                </button>
                <button
                  onClick={startEditing}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Editar
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-4 bg-gray-100 animate-pulse rounded w-3/4" />
            ))}
          </div>
        ) : batch ? (
          <div className="p-6 space-y-6">
            {/* Edit form */}
            {editing ? (
              <form onSubmit={handleSaveEdit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Nome</label>
                    <input
                      value={editForm.name ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Estilo</label>
                    <input
                      value={editForm.style ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, style: e.target.value }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
                    <select
                      value={editForm.status ?? 'planned'}
                      onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value as BatchStatus }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
                    >
                      <option value="planned">Planejado</option>
                      <option value="active">Em Fermentação</option>
                      <option value="completed">Concluído</option>
                      <option value="cancelled">Cancelado</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Panela (ID)</label>
                    <input
                      value={editForm.fermenter_id ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, fermenter_id: e.target.value }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                      placeholder="ex: 1, 2..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Gravidade Original (OG)</label>
                    <input
                      type="number"
                      step="0.001"
                      value={editForm.original_gravity ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, original_gravity: e.target.value ? parseFloat(e.target.value) : undefined }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                      placeholder="ex: 1.050"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Gravidade Final (FG)</label>
                    <input
                      type="number"
                      step="0.001"
                      value={editForm.final_gravity ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, final_gravity: e.target.value ? parseFloat(e.target.value) : undefined }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                      placeholder="ex: 1.010"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Volume (L)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={editForm.volume_liters ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, volume_liters: e.target.value ? parseFloat(e.target.value) : undefined }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Perfil de Levedura</label>
                    <select
                      value={editForm.yeast_profile_id ?? ''}
                      onChange={(e) => setEditForm((f) => ({ ...f, yeast_profile_id: e.target.value ? parseInt(e.target.value) : undefined }))}
                      className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
                    >
                      <option value="">— nenhum —</option>
                      {yeastProfiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Notas</label>
                  <textarea
                    value={editForm.notes ?? ''}
                    onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                    rows={3}
                    className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400 resize-none"
                  />
                </div>
                {editError && <p className="text-xs text-red-500">{editError}</p>}
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => { setEditing(false); setEditError(null) }}
                    className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={isUpdating}
                    className="text-sm px-4 py-2 rounded-lg text-white disabled:opacity-50 transition-colors"
                    style={{ backgroundColor: '#1D9E75' }}
                  >
                    {isUpdating ? 'Salvando...' : 'Salvar'}
                  </button>
                </div>
              </form>
            ) : (
              <>
                {/* Info Grid */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  <InfoRow label="Status">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[batch.status]}`}>
                      {STATUS_LABELS[batch.status]}
                    </span>
                  </InfoRow>
                  <InfoRow label="Panela">{batch.fermenter_id ? `Panela ${batch.fermenter_id}` : '—'}</InfoRow>
                  <InfoRow label="Levedura">{batch.yeast_profile?.name ?? '—'}</InfoRow>
                  <InfoRow label="Volume">{batch.volume_liters ? `${batch.volume_liters} L` : '—'}</InfoRow>
                  <InfoRow label="OG">{batch.original_gravity?.toFixed(3) ?? '—'}</InfoRow>
                  <InfoRow label="FG">{batch.final_gravity?.toFixed(3) ?? '—'}</InfoRow>
                  <InfoRow label="ABV">
                    {batch.abv !== null && batch.abv !== undefined ? (
                      <span className="font-semibold text-gray-800">{batch.abv.toFixed(2)}%</span>
                    ) : '—'}
                  </InfoRow>
                  <InfoRow label="Atenuação Aparente">
                    {batch.apparent_attenuation !== null && batch.apparent_attenuation !== undefined
                      ? `${batch.apparent_attenuation.toFixed(1)}%`
                      : '—'}
                  </InfoRow>
                  <InfoRow label="Início">{formatDate(batch.started_at)}</InfoRow>
                  <InfoRow label="Fim">{formatDate(batch.ended_at)}</InfoRow>
                </div>

                {batch.notes && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Notas</p>
                    <p className="text-sm text-gray-700 bg-gray-50 rounded-lg px-4 py-3">{batch.notes}</p>
                  </div>
                )}
              </>
            )}

            {/* Events Timeline */}
            {!editing && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                    Linha do Tempo ({batch.events.length} evento{batch.events.length !== 1 ? 's' : ''})
                  </p>
                  <button
                    onClick={() => setShowAddEvent((v) => !v)}
                    className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg text-white transition-colors"
                    style={{ backgroundColor: '#1D9E75' }}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                    </svg>
                    Evento
                  </button>
                </div>

                {showAddEvent && (
                  <AddEventForm batchId={batch.id} onDone={() => setShowAddEvent(false)} />
                )}

                {batch.events.length === 0 ? (
                  <p className="text-sm text-gray-400 py-4 text-center">Nenhum evento registrado.</p>
                ) : (
                  <ol className="relative border-l border-gray-200 ml-3 space-y-4 mt-4">
                    {batch.events.map((event) => (
                      <li key={event.id} className="ml-4">
                        <span className="absolute -left-1.5 mt-1 w-3 h-3 rounded-full border-2 border-white bg-gray-300" />
                        <p className="text-xs text-gray-400">{formatDate(event.occurred_at)}</p>
                        <p className="text-sm font-medium text-gray-800 capitalize">{event.event_type}</p>
                        <p className="text-sm text-gray-600">{event.description}</p>
                        {event.value !== null && event.value !== undefined && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            {event.value} {event.unit ?? ''}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <div className="text-sm text-gray-800 mt-0.5">{children}</div>
    </div>
  )
}
