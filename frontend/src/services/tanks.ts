import api from './api'
import type { Tank } from '../types'

export const tanksService = {
  getAll: () => api.get<Tank[]>('/api/v1/tanks').then((r) => r.data),

  updateConfig: (id: number, data: { name: string; temp_min: number; temp_max: number }) =>
    api.patch<Tank>(`/api/v1/tanks/${id}/config`, data).then((r) => r.data),
}
