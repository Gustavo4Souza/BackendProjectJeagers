import type { Tank } from '../../types'
import { TankCard } from './TankCard'
import { TankCardSkeleton } from '../base/LoadingSkeleton'

interface TankGridProps {
  tanks: Tank[] | undefined
  isLoading: boolean
  selectedTankId: number
  onSelectTank: (id: number) => void
  onConfigTank: (id: number) => void
}

export function TankGrid({ tanks, isLoading, selectedTankId, onSelectTank, onConfigTank }: TankGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <TankCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {tanks?.map((tank) => (
        <TankCard
          key={tank.id}
          tank={tank}
          isSelected={tank.id === selectedTankId}
          onSelect={() => onSelectTank(tank.id)}
          onConfig={() => onConfigTank(tank.id)}
        />
      ))}
    </div>
  )
}
