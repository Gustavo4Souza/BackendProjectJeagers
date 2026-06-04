import api from './api'
import type { User } from '../types'

export interface CreateUserPayload {
  username: string
  password: string
  role: 'admin' | 'operador' | 'viewer'
}

export interface UpdateUserPayload {
  role?: 'admin' | 'operador' | 'viewer'
}

export const usersService = {
  getAll: () => api.get<User[]>('/api/v1/users').then((r) => r.data),

  create: (data: CreateUserPayload) =>
    api.post<User>('/api/v1/users', data).then((r) => r.data),

  update: (id: number, data: UpdateUserPayload) =>
    api.patch<User>(`/api/v1/users/${id}`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/api/v1/users/${id}`),
}
