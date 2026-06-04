import api from './api'
import type { Reading } from '../types'

export const readingsService = {
  getByTank: (id: number, period: '6h' | '24h' | '7d' | '30d') =>
    api
      .get<Reading[]>(`/api/v1/tanks/${id}/readings`, { params: { period } })
      .then((r) => r.data),

  exportCSV: (id: number, period: '6h' | '24h' | '7d' | '30d') =>
    api
      .get(`/api/v1/tanks/${id}/readings/export`, {
        params: { period },
        responseType: 'blob',
      })
      .then((r) => r.data as Blob),
}
