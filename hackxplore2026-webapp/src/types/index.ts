export type HumidityStatus = 'dry' | 'low' | 'normal' | 'moist'
export type SensorStatus = 'active' | 'inactive'
export type WeatherCondition = 'sunny' | 'cloudy' | 'partly-cloudy' | 'rainy' | 'stormy'

export interface Tree {
  id: string
  name: string
  tree_type: string
  common_name: string
  age_years: number
  owner_username: string | null
  current_humidity: number
  humidity_status: HumidityStatus
  sensor_id: string | null
  lat: number
  lng: number
  district: string
  created_at: string
}

export interface Sensor {
  id: string
  name: string
  model_type: string
  status: SensorStatus
  installed_at: string
  last_activity: string
  lat: number
  lng: number
  covered_tree_ids: string[]
  battery_level: number | null
  created_at: string
}

export interface SensorReading {
  id: string
  sensor_id: string
  tree_id: string
  value: number
  timestamp: string
}

export interface UserProfile {
  id: string
  username: string
  assigned_trees_count: number
  avatar_url: string | null
  joined_at: string
}

export interface WeatherDay {
  date: string
  condition: WeatherCondition
  temp_high: number
  temp_low: number
  precipitation_mm: number
  humidity_pct: number
}

export interface NetworkStats {
  daily_users: number
  daily_users_history: Array<{ date: string; value: number }>
  total_sensors: number
  sensors_history: Array<{ date: string; value: number }>
  data_points: number
  data_points_history: Array<{ date: string; value: number }>
  data_points_monthly_delta_pct: number
  registered_trees: number
  trees_history: Array<{ date: string; value: number }>
}

export interface SelectedEntity {
  type: 'tree' | 'sensor' | null
  id: string | null
}

export interface MapFilters {
  sensorStatus: {
    active: boolean
    inactive: boolean
  }
  treeStatus: {
    dry: boolean
    low: boolean
    normal: boolean
    moist: boolean
  }
}

export interface KarlsruheDistrict {
  name: string
  lat: number
  lng: number
}
