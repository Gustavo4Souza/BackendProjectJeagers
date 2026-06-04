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
  alert_type: 'above_max' | 'below_min' | null
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

export type ControlMode = 'cooling' | 'heating' | 'idle'

export interface TankControl {
  tank_id: number
  setpoint: number
  mode: ControlMode
  updated_at: string
  updated_by: number | null
}

export interface ETAResult {
  eta_minutes: number | null
  rate_per_minute: number | null
  current_temp: number | null
  setpoint: number
  sufficient_data: boolean
}

export interface User {
  id: number
  username: string
  role: 'admin' | 'operador' | 'viewer'
}

export interface YeastProfile {
  id: number
  name: string
  strain: string | null
  attenuation_min: number | null
  attenuation_max: number | null
  temperature_min_c: number | null
  temperature_max_c: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export type BatchStatus = 'planned' | 'active' | 'completed' | 'cancelled'

export interface BatchEvent {
  id: number
  batch_id: number
  event_type: string
  description: string
  value: number | null
  unit: string | null
  occurred_at: string
  created_at: string
}

export interface Batch {
  id: number
  name: string
  style: string
  status: BatchStatus
  fermenter_id: string | null
  yeast_profile_id: number | null
  original_gravity: number | null
  final_gravity: number | null
  volume_liters: number | null
  started_at: string | null
  ended_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface BatchDetail extends Batch {
  abv: number | null
  apparent_attenuation: number | null
  yeast_profile: YeastProfile | null
  events: BatchEvent[]
}
