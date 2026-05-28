import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useCallback } from 'react'
import { alertsService } from '../services/alerts'
import { useGenericWebSocket } from './useGenericWebSocket'
import type { Alert } from '../types'

export function useAlerts() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: alertsService.getActive,
    refetchInterval: 10_000,
  })
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (alertId: number) => alertsService.acknowledge(alertId),
    onSuccess: (_, alertId) => {
      queryClient.setQueryData<Alert[]>(['alerts'], (prev) =>
        prev ? prev.filter((a) => a.id !== alertId) : prev
      )
    },
  })
}

export function useAlertsWebSocket() {
  const queryClient = useQueryClient()

  const onAlert = useCallback(
    (alert: Alert) => {
      queryClient.setQueryData<Alert[]>(['alerts'], (prev) => {
        if (!prev) return [alert]
        if (prev.some((a) => a.id === alert.id)) return prev
        return [alert, ...prev]
      })
    },
    [queryClient]
  )

  useGenericWebSocket<Alert>('/ws/alerts', onAlert)
}
