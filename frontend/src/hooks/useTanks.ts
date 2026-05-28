import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useCallback } from 'react'
import { tanksService } from '../services/tanks'
import { useWebSocket } from './useWebSocket'
import type { Reading, Tank } from '../types'

export function useTanks() {
  return useQuery({
    queryKey: ['tanks'],
    queryFn: tanksService.getAll,
    refetchInterval: 30_000,
  })
}

export function useTankWebSocket(tankId: number) {
  const queryClient = useQueryClient()

  const onReading = useCallback(
    (reading: Reading) => {
      queryClient.setQueryData<Tank[]>(['tanks'], (prev) => {
        if (!prev) return prev
        return prev.map((tank) =>
          tank.id === reading.tank_id
            ? {
                ...tank,
                current_temperature: reading.temperature,
                last_reading_at: reading.recorded_at,
              }
            : tank
        )
      })
    },
    [queryClient]
  )

  useWebSocket(tankId, onReading)
}

export function useUpdateTankConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number
      data: { name: string; temp_min: number; temp_max: number }
    }) => tanksService.updateConfig(id, data),
    onSuccess: (updatedTank) => {
      queryClient.setQueryData<Tank[]>(['tanks'], (prev) =>
        prev ? prev.map((t) => (t.id === updatedTank.id ? updatedTank : t)) : prev
      )
    },
  })
}
