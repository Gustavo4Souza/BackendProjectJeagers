export type TankStatus = 'normal' | 'warning' | 'alert' | 'offline'

export interface Tank {
  id: number
  name: string
  location: string
  temp_min: number
  temp_max: number
  status: 'active' | 'inactive' | 'maintenance'
  current_temperature: number | null
  last_reading_at: string | null
}

export interface Reading {
  id: number
  tank_id: number
  temperature: number
  recorded_at: string
}

export interface Alert {
  id: number
  tank_id: number
  tank_name: string
  temperature: number
  type: 'above_max' | 'below_min'
  fired_at: string
  resolved_at: string | null
  acknowledged_by: number | null
}

export interface TankStatusData {
  tank_id: number
  current_temperature: number | null
  last_reading_at: string | null
  active_alerts: Alert[]
}
