import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useCallback } from 'react'
import { alertsService, type AlertFilters } from '../services/alerts'
import { useGenericWebSocket } from './useGenericWebSocket'

export function useAlerts(filters?: AlertFilters) {
  return useQuery({
    queryKey: ['alerts', filters ?? { status: 'active' }],
    queryFn: () => alertsService.getAll(filters ?? { status: 'active' }),
    refetchInterval: 10_000,
  })
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (alertId: number) => alertsService.acknowledge(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useAcknowledgeAllAlerts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => alertsService.acknowledgeAll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useAlertsWebSocket() {
  const queryClient = useQueryClient()

  const onAlert = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['alerts'] })
  }, [queryClient])

  useGenericWebSocket('/ws/alerts', onAlert)
}
