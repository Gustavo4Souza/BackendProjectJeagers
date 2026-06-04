import api from './api'
import type { Batch, BatchDetail, BatchEvent, BatchStatus, YeastProfile } from '../types'

export interface CreateBatchPayload {
  name: string
  style: string
  status?: BatchStatus
  fermenter_id?: string
  yeast_profile_id?: number | null
  original_gravity?: number | null
  final_gravity?: number | null
  volume_liters?: number | null
  started_at?: string | null
  ended_at?: string | null
  notes?: string | null
}

export interface CreateBatchEventPayload {
  event_type: string
  description: string
  value?: number | null
  unit?: string | null
  occurred_at?: string
}

export interface CreateYeastProfilePayload {
  name: string
  strain?: string | null
  attenuation_min?: number | null
  attenuation_max?: number | null
  temperature_min_c?: number | null
  temperature_max_c?: number | null
  notes?: string | null
}

export const batchesService = {
  getAll: (params?: { status?: BatchStatus | ''; style?: string }) =>
    api.get<Batch[]>('/api/v1/batches', { params }).then((r) => r.data),

  getById: (id: number) =>
    api.get<BatchDetail>(`/api/v1/batches/${id}`).then((r) => r.data),

  create: (data: CreateBatchPayload) =>
    api.post<Batch>('/api/v1/batches', data).then((r) => r.data),

  update: (id: number, data: Partial<CreateBatchPayload>) =>
    api.patch<BatchDetail>(`/api/v1/batches/${id}`, data).then((r) => r.data),

  addEvent: (batchId: number, data: CreateBatchEventPayload) =>
    api.patch<BatchEvent>(`/api/v1/batches/${batchId}/events`, data).then((r) => r.data),

  exportCsv: (id: number) =>
    api.get(`/api/v1/batches/${id}/export`, {
      params: { format: 'csv' },
      responseType: 'blob',
    }).then((r) => r.data as Blob),
}

export const yeastProfilesService = {
  getAll: () =>
    api.get<YeastProfile[]>('/api/v1/yeast_profiles').then((r) => r.data),

  getById: (id: number) =>
    api.get<YeastProfile>(`/api/v1/yeast_profiles/${id}`).then((r) => r.data),

  create: (data: CreateYeastProfilePayload) =>
    api.post<YeastProfile>('/api/v1/yeast_profiles', data).then((r) => r.data),

  update: (id: number, data: Partial<CreateYeastProfilePayload>) =>
    api.patch<YeastProfile>(`/api/v1/yeast_profiles/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/api/v1/yeast_profiles/${id}`),
}
