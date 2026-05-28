import api from './api'
import type { Alert } from '../types'

export const alertsService = {
  getActive: () =>
    api.get<Alert[]>('/api/v1/alerts', { params: { status: 'active' } }).then((r) => r.data),

  acknowledge: (id: number) =>
    api.patch(`/api/v1/alerts/${id}/acknowledge`).then((r) => r.data),
}
