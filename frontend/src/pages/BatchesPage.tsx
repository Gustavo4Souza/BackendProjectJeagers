import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { TopBar } from '../components/layout/TopBar'
import { BatchDetailModal } from '../components/batches/BatchDetailModal'
import { useAlerts } from '../hooks/useAlerts'
import { batchesService, yeastProfilesService, type CreateBatchPayload } from '../services/batches'
import type { Batch, BatchStatus, YeastProfile } from '../types'

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

function formatDate(dateStr: string | null) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

// ─── Create Batch Modal ───────────────────────────────────────────────────────

interface CreateBatchModalProps {
  yeastProfiles: YeastProfile[]
  onClose: () => void
}

function CreateBatchModal({ yeastProfiles, onClose }: CreateBatchModalProps) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<CreateBatchPayload>({
    name: '',
    style: '',
    status: 'planned',
    fermenter_id: '',
    yeast_profile_id: undefined,
    original_gravity: undefined,
    final_gravity: undefined,
    volume_liters: undefined,
    notes: '',
  })
  const [error, setError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation({
    mutationFn: (data: CreateBatchPayload) => batchesService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      onClose()
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erro ao criar lote')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Nome obrigatório'); return }
    if (!form.style.trim()) { setError('Estilo obrigatório'); return }
    setError(null)
    mutate({
      ...form,
      fermenter_id: form.fermenter_id || undefined,
      yeast_profile_id: form.yeast_profile_id || undefined,
      original_gravity: form.original_gravity || undefined,
      final_gravity: form.final_gravity || undefined,
      volume_liters: form.volume_liters || undefined,
      notes: form.notes || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-base font-semibold text-gray-900 mb-4">Novo Lote</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Nome *</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Ex: Lager Verão 2026"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Estilo *</label>
              <input
                value={form.style}
                onChange={(e) => setForm((f) => ({ ...f, style: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Ex: Munich Helles"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Panela (ID)</label>
              <input
                value={form.fermenter_id ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, fermenter_id: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 1, 2..."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Perfil de Levedura</label>
              <select
                value={form.yeast_profile_id ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, yeast_profile_id: e.target.value ? parseInt(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
              >
                <option value="">— nenhum —</option>
                {yeastProfiles.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">OG (Grav. Original)</label>
              <input
                type="number"
                step="0.001"
                value={form.original_gravity ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, original_gravity: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 1.050"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Volume (L)</label>
              <input
                type="number"
                step="0.5"
                value={form.volume_liters ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, volume_liters: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 50"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Notas</label>
            <textarea
              value={form.notes ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={2}
              className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400 resize-none"
              placeholder="Observações opcionais..."
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 text-sm px-4 py-2 rounded-lg text-white disabled:opacity-50 transition-colors"
              style={{ backgroundColor: '#1D9E75' }}
            >
              {isPending ? 'Criando...' : 'Criar Lote'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Batch Card ───────────────────────────────────────────────────────────────

interface BatchCardProps {
  batch: Batch
  onClick: () => void
}

function BatchCard({ batch, onClick }: BatchCardProps) {
  return (
    <div
      className="bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">{batch.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{batch.style}</p>
        </div>
        <span className={`ml-3 flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[batch.status]}`}>
          {STATUS_LABELS[batch.status]}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        <MetaItem label="Panela" value={batch.fermenter_id ? `Panela ${batch.fermenter_id}` : '—'} />
        <MetaItem label="Volume" value={batch.volume_liters ? `${batch.volume_liters} L` : '—'} />
        <MetaItem label="OG" value={batch.original_gravity?.toFixed(3) ?? '—'} />
        <MetaItem label="FG" value={batch.final_gravity?.toFixed(3) ?? '—'} />
        <MetaItem label="Início" value={formatDate(batch.started_at)} />
        <MetaItem label="Fim" value={formatDate(batch.ended_at)} />
      </div>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-gray-400">{label}: </span>
      <span className="text-xs text-gray-700">{value}</span>
    </div>
  )
}

// ─── BatchesPage ──────────────────────────────────────────────────────────────

type StatusFilter = BatchStatus | ''

const FILTER_OPTIONS: { label: string; value: StatusFilter }[] = [
  { label: 'Todos', value: '' },
  { label: 'Planejados', value: 'planned' },
  { label: 'Em Fermentação', value: 'active' },
  { label: 'Concluídos', value: 'completed' },
  { label: 'Cancelados', value: 'cancelled' },
]

export default function BatchesPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('')
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const { data: activeAlerts = [] } = useAlerts()

  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['batches', statusFilter],
    queryFn: () => batchesService.getAll(statusFilter ? { status: statusFilter } : undefined),
  })

  const { data: yeastProfiles = [] } = useQuery({
    queryKey: ['yeast_profiles'],
    queryFn: yeastProfilesService.getAll,
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar alertCount={activeAlerts.length} />

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Lotes de Fermentação</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              {batches.length} lote{batches.length !== 1 ? 's' : ''}
              {statusFilter ? ` · ${STATUS_LABELS[statusFilter]}` : ''}
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: '#1D9E75' }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Novo Lote
          </button>
        </div>

        {/* Filter Bar */}
        <div className="flex gap-2 flex-wrap">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium border transition-colors ${
                statusFilter === opt.value
                  ? 'text-white border-transparent'
                  : 'text-gray-500 border-gray-200 bg-white hover:bg-gray-50'
              }`}
              style={statusFilter === opt.value ? { backgroundColor: '#1D9E75', borderColor: '#1D9E75' } : {}}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 h-40 animate-pulse" />
            ))}
          </div>
        ) : batches.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 py-16 text-center">
            <svg className="w-10 h-10 text-gray-200 mx-auto mb-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-sm text-gray-400">Nenhum lote encontrado.</p>
            {statusFilter && (
              <button
                onClick={() => setStatusFilter('')}
                className="mt-2 text-xs underline text-gray-400 hover:text-gray-600"
              >
                Limpar filtro
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {batches.map((batch) => (
              <BatchCard
                key={batch.id}
                batch={batch}
                onClick={() => setSelectedBatchId(batch.id)}
              />
            ))}
          </div>
        )}
      </main>

      {showCreate && (
        <CreateBatchModal
          yeastProfiles={yeastProfiles}
          onClose={() => setShowCreate(false)}
        />
      )}

      {selectedBatchId !== null && (
        <BatchDetailModal
          batchId={selectedBatchId}
          yeastProfiles={yeastProfiles}
          onClose={() => setSelectedBatchId(null)}
        />
      )}
    </div>
  )
}
