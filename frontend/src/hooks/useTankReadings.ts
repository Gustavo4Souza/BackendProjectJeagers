import { useQuery } from '@tanstack/react-query'
import { readingsService } from '../services/readings'

type Period = '6h' | '24h' | '7d' | '30d'

export function useTankReadings(tankId: number, period: Period) {
  return useQuery({
    queryKey: ['readings', tankId, period],
    queryFn: () => readingsService.getByTank(tankId, period),
    staleTime: 60_000,
  })
}
