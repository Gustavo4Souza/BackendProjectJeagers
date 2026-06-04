import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTanks, useUpdateTankConfig } from '../hooks/useTanks'
import { useAlerts } from '../hooks/useAlerts'
import { usersService, type CreateUserPayload } from '../services/users'
import { yeastProfilesService, type CreateYeastProfilePayload } from '../services/batches'
import { TopBar } from '../components/layout/TopBar'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import type { Tank, User, YeastProfile } from '../types'

type Section = 'panelas' | 'usuarios' | 'leveduras' | 'sistema'

const ROLE_LABELS: Record<User['role'], string> = {
  admin: 'Admin',
  operador: 'Operador',
  viewer: 'Viewer',
}

const ROLE_COLORS: Record<User['role'], string> = {
  admin: 'bg-purple-100 text-purple-700',
  operador: 'bg-blue-100 text-blue-700',
  viewer: 'bg-gray-100 text-gray-600',
}

// ─── Panelas Section ──────────────────────────────────────────────────────────

interface TankRowProps {
  tank: Tank
}

function TankRow({ tank }: TankRowProps) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(tank.name)
  const [tempMin, setTempMin] = useState(String(tank.temp_min))
  const [tempMax, setTempMax] = useState(String(tank.temp_max))
  const [error, setError] = useState<string | null>(null)

  const { mutate: updateConfig, isPending } = useUpdateTankConfig()

  function handleSave() {
    const min = parseFloat(tempMin)
    const max = parseFloat(tempMax)
    if (isNaN(min) || isNaN(max)) { setError('Valores inválidos'); return }
    if (min >= max) { setError('Mín deve ser menor que Máx'); return }
    setError(null)
    updateConfig(
      { id: tank.id, data: { name: name.trim() || tank.name, temp_min: min, temp_max: max } },
      {
        onSuccess: () => setEditing(false),
        onError: () => setError('Erro ao salvar. Tente novamente.'),
      }
    )
  }

  function handleCancel() {
    setName(tank.name)
    setTempMin(String(tank.temp_min))
    setTempMax(String(tank.temp_max))
    setError(null)
    setEditing(false)
  }

  return (
    <tr className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 text-sm text-gray-500 w-10">{tank.id}</td>
      <td className="px-4 py-3">
        {editing ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-green-400"
            maxLength={100}
          />
        ) : (
          <span className="text-sm font-medium text-gray-800">{tank.name}</span>
        )}
      </td>
      <td className="px-4 py-3 w-28">
        {editing ? (
          <input
            type="number"
            step="0.5"
            value={tempMin}
            onChange={(e) => setTempMin(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-green-400"
          />
        ) : (
          <span className="text-sm text-gray-700">{tank.temp_min}°C</span>
        )}
      </td>
      <td className="px-4 py-3 w-28">
        {editing ? (
          <input
            type="number"
            step="0.5"
            value={tempMax}
            onChange={(e) => setTempMax(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-green-400"
          />
        ) : (
          <span className="text-sm text-gray-700">{tank.temp_max}°C</span>
        )}
      </td>
      <td className="px-4 py-3 text-right w-40">
        {error && <p className="text-xs text-red-500 mb-1">{error}</p>}
        {editing ? (
          <div className="flex gap-2 justify-end">
            <button
              onClick={handleCancel}
              className="text-xs px-3 py-1.5 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={isPending}
              className="text-xs px-3 py-1.5 rounded-md text-white disabled:opacity-50 transition-colors"
              style={{ backgroundColor: '#1D9E75' }}
            >
              {isPending ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="text-xs px-3 py-1.5 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Editar
          </button>
        )}
      </td>
    </tr>
  )
}

// ─── Usuários Section ─────────────────────────────────────────────────────────

function NewUserModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<CreateUserPayload>({ username: '', password: '', role: 'viewer' })
  const [error, setError] = useState<string | null>(null)

  const { mutate: createUser, isPending } = useMutation({
    mutationFn: (data: CreateUserPayload) => usersService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erro ao criar usuário')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.username.trim() || !form.password.trim()) {
      setError('Preencha todos os campos')
      return
    }
    setError(null)
    createUser(form)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-gray-900 mb-4">Novo Usuário</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Usuário</label>
            <input
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
              placeholder="nome_usuario"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Senha</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Função</label>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as User['role'] }))}
              className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="viewer">Viewer — somente leitura</option>
              <option value="operador">Operador — leitura + controle</option>
              <option value="admin">Admin — acesso total</option>
            </select>
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-2 pt-2">
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
              {isPending ? 'Criando...' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function UsersSection() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [showNewModal, setShowNewModal] = useState(false)
  const [changingRoleId, setChangingRoleId] = useState<number | null>(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: usersService.getAll,
  })

  const { mutate: updateUser } = useMutation({
    mutationFn: ({ id, role }: { id: number; role: User['role'] }) =>
      usersService.update(id, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setChangingRoleId(null)
    },
  })

  const { mutate: deleteUser } = useMutation({
    mutationFn: (id: number) => usersService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  if (isLoading) {
    return <div className="p-6 text-sm text-gray-400">Carregando usuários...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-800">Usuários</h3>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-white transition-colors"
          style={{ backgroundColor: '#1D9E75' }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Novo usuário
        </button>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-50 bg-gray-50">
            <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Usuário</th>
            <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Função</th>
            <th className="px-4 py-3 w-28" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {users.map((u) => (
            <tr key={u.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3">
                <span className="text-sm font-medium text-gray-800">{u.username}</span>
                {u.username === currentUser?.sub && (
                  <span className="ml-2 text-xs text-gray-400">(você)</span>
                )}
              </td>
              <td className="px-4 py-3">
                {changingRoleId === u.id ? (
                  <select
                    defaultValue={u.role}
                    autoFocus
                    onChange={(e) => updateUser({ id: u.id, role: e.target.value as User['role'] })}
                    onBlur={() => setChangingRoleId(null)}
                    className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="operador">Operador</option>
                    <option value="admin">Admin</option>
                  </select>
                ) : (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer ${ROLE_COLORS[u.role]}`}
                    onClick={() => setChangingRoleId(u.id)}
                    title="Clique para alterar"
                  >
                    {ROLE_LABELS[u.role]}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {u.username !== currentUser?.sub && (
                  <button
                    onClick={() => {
                      if (confirm(`Remover o usuário "${u.username}"?`)) deleteUser(u.id)
                    }}
                    className="text-xs px-2.5 py-1 rounded-md border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                  >
                    Remover
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showNewModal && <NewUserModal onClose={() => setShowNewModal(false)} />}
    </div>
  )
}

// ─── Sistema Section ──────────────────────────────────────────────────────────

function SistemaSection() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<{ status: string; version: string }>('/health').then((r) => r.data),
    refetchInterval: 30_000,
  })

  return (
    <div className="divide-y divide-gray-50">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-800">Sistema</h3>
      </div>
      <div className="px-4 py-4 space-y-3">
        {isLoading ? (
          <p className="text-sm text-gray-400">Verificando status...</p>
        ) : error ? (
          <p className="text-sm text-red-500">Erro ao conectar com o backend</p>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600 w-32">Status da API</span>
              <span className="flex items-center gap-1.5 text-sm font-medium text-green-600">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                {health?.status === 'ok' ? 'Online' : health?.status}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600 w-32">Versão da API</span>
              <span className="text-sm font-mono text-gray-800">{health?.version ?? '—'}</span>
            </div>
          </>
        )}
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-32">Plataforma</span>
          <span className="text-sm text-gray-800">Docker Compose (local)</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-32">Banco de dados</span>
          <span className="text-sm text-gray-800">PostgreSQL + TimescaleDB</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-32">Cache / Pub-Sub</span>
          <span className="text-sm text-gray-800">Redis 7</span>
        </div>
      </div>
    </div>
  )
}

// ─── Leveduras Section ────────────────────────────────────────────────────────

interface YeastProfileModalProps {
  profile?: YeastProfile
  onClose: () => void
}

function YeastProfileModal({ profile, onClose }: YeastProfileModalProps) {
  const queryClient = useQueryClient()
  const isEdit = !!profile
  const [form, setForm] = useState<CreateYeastProfilePayload>({
    name: profile?.name ?? '',
    strain: profile?.strain ?? '',
    attenuation_min: profile?.attenuation_min ?? undefined,
    attenuation_max: profile?.attenuation_max ?? undefined,
    temperature_min_c: profile?.temperature_min_c ?? undefined,
    temperature_max_c: profile?.temperature_max_c ?? undefined,
    notes: profile?.notes ?? '',
  })
  const [error, setError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation({
    mutationFn: (data: CreateYeastProfilePayload) =>
      isEdit
        ? yeastProfilesService.update(profile!.id, data)
        : yeastProfilesService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['yeast_profiles'] })
      onClose()
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erro ao salvar perfil')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Nome obrigatório'); return }
    setError(null)
    mutate({
      ...form,
      strain: form.strain || null,
      notes: form.notes || null,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-gray-900 mb-4">
          {isEdit ? 'Editar Perfil' : 'Novo Perfil de Levedura'}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Nome *</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Ex: SafLager W-34/70"
                autoFocus
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Cepa</label>
              <input
                value={form.strain ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, strain: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Ex: Fermentis W-34/70"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Temp. Mín (°C)</label>
              <input
                type="number"
                step="0.5"
                value={form.temperature_min_c ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, temperature_min_c: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 8"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Temp. Máx (°C)</label>
              <input
                type="number"
                step="0.5"
                value={form.temperature_max_c ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, temperature_max_c: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 15"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Atenuação Mín (%)</label>
              <input
                type="number"
                step="1"
                value={form.attenuation_min ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, attenuation_min: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 73"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Atenuação Máx (%)</label>
              <input
                type="number"
                step="1"
                value={form.attenuation_max ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, attenuation_max: e.target.value ? parseFloat(e.target.value) : undefined }))}
                className="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="ex: 80"
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
              {isPending ? 'Salvando...' : isEdit ? 'Salvar' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function LevedurasSection() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingProfile, setEditingProfile] = useState<YeastProfile | undefined>()

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ['yeast_profiles'],
    queryFn: yeastProfilesService.getAll,
  })

  const { mutate: deleteProfile } = useMutation({
    mutationFn: (id: number) => yeastProfilesService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['yeast_profiles'] }),
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(msg ?? 'Erro ao remover perfil')
    },
  })

  if (isLoading) return <div className="p-6 text-sm text-gray-400">Carregando perfis...</div>

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Perfis de Levedura</h3>
          <p className="text-xs text-gray-400 mt-0.5">Gerencie as leveduras usadas nos lotes.</p>
        </div>
        <button
          onClick={() => { setEditingProfile(undefined); setShowModal(true) }}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-white transition-colors"
          style={{ backgroundColor: '#1D9E75' }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Novo perfil
        </button>
      </div>

      {profiles.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">Nenhum perfil cadastrado.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-50 bg-gray-50">
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Nome</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Cepa</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-32">Temp (°C)</th>
                <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-32">Atenuação (%)</th>
                <th className="px-4 py-3 w-28" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {profiles.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium text-gray-800">{p.name}</span>
                    {p.notes && <p className="text-xs text-gray-400 truncate max-w-xs">{p.notes}</p>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{p.strain ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {p.temperature_min_c !== null && p.temperature_max_c !== null
                      ? `${p.temperature_min_c}–${p.temperature_max_c}`
                      : p.temperature_min_c ?? p.temperature_max_c ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {p.attenuation_min !== null && p.attenuation_max !== null
                      ? `${p.attenuation_min}–${p.attenuation_max}`
                      : p.attenuation_min ?? p.attenuation_max ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => { setEditingProfile(p); setShowModal(true) }}
                        className="text-xs px-2.5 py-1 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Remover o perfil "${p.name}"?`)) deleteProfile(p.id)
                        }}
                        className="text-xs px-2.5 py-1 rounded-md border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                      >
                        Remover
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <YeastProfileModal
          profile={editingProfile}
          onClose={() => { setShowModal(false); setEditingProfile(undefined) }}
        />
      )}
    </div>
  )
}

// ─── ConfigPage ───────────────────────────────────────────────────────────────

export default function ConfigPage() {
  const [activeSection, setActiveSection] = useState<Section>('panelas')
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const { data: tanks = [], isLoading: tanksLoading } = useTanks()
  const { data: activeAlerts = [] } = useAlerts()

  const SECTIONS: { key: Section; label: string; adminOnly?: boolean }[] = [
    { key: 'panelas', label: 'Panelas' },
    { key: 'leveduras', label: 'Leveduras' },
    { key: 'usuarios', label: 'Usuários', adminOnly: true },
    { key: 'sistema', label: 'Sistema' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <TopBar alertCount={activeAlerts.length} />

      <main className="max-w-screen-xl mx-auto px-6 py-6 space-y-5">
        <h1 className="text-lg font-semibold text-gray-900">Configurações</h1>

        <div className="flex gap-6 items-start">
          {/* Sidebar */}
          <nav className="w-44 flex-shrink-0 bg-white rounded-xl border border-gray-200 overflow-hidden">
            {SECTIONS.filter((s) => !s.adminOnly || isAdmin).map((section) => (
              <button
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                className={`w-full text-left text-sm px-4 py-3 border-b border-gray-50 last:border-0 transition-colors ${
                  activeSection === section.key
                    ? 'text-gray-900 font-medium bg-gray-50'
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                {section.label}
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
            {activeSection === 'panelas' && (
              <>
                <div className="px-4 py-3 border-b border-gray-100">
                  <h3 className="text-sm font-semibold text-gray-800">Panelas</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Edite nome e faixas de temperatura de cada panela.
                  </p>
                </div>
                {tanksLoading ? (
                  <div className="p-6 text-sm text-gray-400">Carregando...</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-50 bg-gray-50">
                          <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-10">#</th>
                          <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Nome</th>
                          <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-28">Mín (°C)</th>
                          <th className="text-left text-xs font-medium text-gray-500 px-4 py-3 w-28">Máx (°C)</th>
                          <th className="px-4 py-3 w-40" />
                        </tr>
                      </thead>
                      <tbody>
                        {tanks.map((tank) => (
                          <TankRow key={tank.id} tank={tank} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}

            {activeSection === 'leveduras' && <LevedurasSection />}

            {activeSection === 'usuarios' && isAdmin && <UsersSection />}

            {activeSection === 'sistema' && <SistemaSection />}
          </div>
        </div>
      </main>
    </div>
  )
}
