import api from './api'
import type { Alert } from '../types'

export interface AlertFilters {
  status?: 'active' | 'resolved'
  tank_id?: number
  period?: '24h' | '7d' | '30d'
}

export const alertsService = {
  getAll: (filters?: AlertFilters) =>
    api.get<Alert[]>('/api/v1/alerts', { params: filters }).then((r) => r.data),

  getActive: () =>
    api.get<Alert[]>('/api/v1/alerts', { params: { status: 'active' } }).then((r) => r.data),

  acknowledge: (id: number) =>
    api.patch<Alert>(`/api/v1/alerts/${id}/acknowledge`).then((r) => r.data),

  acknowledgeAll: () =>
    api.post<Alert[]>('/api/v1/alerts/acknowledge-all').then((r) => r.data),
}
