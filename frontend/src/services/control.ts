import api from './api'
import type { TankControl, ETAResult } from '../types'

export const controlService = {
  getControl: (tankId: number) =>
    api.get<TankControl>(`/api/v1/tanks/${tankId}/control`).then((r) => r.data),

  setControl: (tankId: number, setpoint: number) =>
    api.post<TankControl>(`/api/v1/tanks/${tankId}/control`, { setpoint }).then((r) => r.data),

  getETA: (tankId: number) =>
    api.get<ETAResult>(`/api/v1/tanks/${tankId}/eta`).then((r) => r.data),
}
