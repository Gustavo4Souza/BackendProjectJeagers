import { useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { controlService } from '../services/control'
import { useGenericWebSocket } from './useGenericWebSocket'
import type { TankControl, ETAResult } from '../types'

export function useTankControl(tankId: number) {
  return useQuery({
    queryKey: ['control', tankId],
    queryFn: () => controlService.getControl(tankId),
    refetchInterval: 10_000,
    retry: false,
  })
}

export function useSetControl(tankId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (setpoint: number) => controlService.setControl(tankId, setpoint),
    onSuccess: (data) => {
      queryClient.setQueryData<TankControl>(['control', tankId], data)
      queryClient.invalidateQueries({ queryKey: ['eta', tankId] })
    },
  })
}

export function useTankETA(tankId: number) {
  return useQuery({
    queryKey: ['eta', tankId],
    queryFn: () => controlService.getETA(tankId),
    refetchInterval: 30_000,
    retry: false,
  })
}

export function useControlWebSocket() {
  const queryClient = useQueryClient()

  const onControlEvent = useCallback(
    (control: TankControl) => {
      queryClient.setQueryData<TankControl>(['control', control.tank_id], control)
      queryClient.invalidateQueries({ queryKey: ['eta', control.tank_id] })
    },
    [queryClient]
  )

  useGenericWebSocket<TankControl>('/ws/control', onControlEvent)
}

export type { ETAResult }
