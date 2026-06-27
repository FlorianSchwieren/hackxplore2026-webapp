import type {
  HumidityStatus,
  NetworkStats,
  Sensor,
  SensorReading,
  SensorStatus,
  Tree,
  WeatherDay,
  WeatherCondition,
} from '@/types'

type ApiTree = {
  id: string
  external_id: number
  name: string | null
  title: string
  artdeut: string | null
  artlat: string | null
  baumart_allgemein: string
  stadtteil: string
  lon: number
  lat: number
  status: string
  monitored: boolean
  moisture_pct: number | null
  health_state: string | null
  last_reading_at: string | null
  created_at?: string | null
  owner_ids?: string[]
}

type ApiTreeDetail = ApiTree & {
  sensor?: { id: string; device_eui: string; status: string; is_real: boolean; last_seen_at: string | null } | null
  partners?: Array<{ user_id: string; display_name: string; role: string; streak: number }>
}

type ApiSensor = {
  id: string
  device_eui: string
  tree_id: string
  status: string
  last_seen_at: string | null
  stadtteil: string
  lon: number
  lat: number
}

type ApiReading = {
  id?: number | null
  sensor_id?: string | null
  measured_at: string
  moisture_pct: number
  raw?: number | null
}

type ApiStatsOverview = {
  trees_total: number
  trees_monitored: number
  users_total: number
  partnerships_active: number
  health_distribution: Record<string, number>
  sensors: Record<string, number>
  city_health_score: number
  absences_active: number
}

type ApiStadtteil = {
  stadtteil: string
  trees: number
  monitored: number
  avg_health_score: number | null
  needs_water: number
}

type ApiWeather = {
  current?: { temperature_2m?: number; relative_humidity_2m?: number; precipitation?: number }
  daily?: Array<{ date: string; temp_max?: number; precip_mm?: number }>
}

export function healthToHumidityStatus(health: string | null | undefined): HumidityStatus {
  switch (health) {
    case 'critical':
      return 'dry'
    case 'thirsty':
      return 'low'
    case 'overwatered':
      return 'moist'
    case 'healthy':
    case 'thriving':
    default:
      return 'normal'
  }
}

export function sensorStatusToApp(status: string): SensorStatus {
  return status === 'working' ? 'active' : 'inactive'
}

export function mapTree(tree: ApiTree, detail?: ApiTreeDetail): Tree {
  const owner = detail?.partners?.find((p) => p.role === 'owner')
  return {
    id: tree.id,
    name: tree.title || tree.name || `Baum #${tree.external_id}`,
    tree_type: tree.artlat || tree.baumart_allgemein,
    common_name: tree.artdeut || tree.baumart_allgemein,
    age_years: 0,
    owner_username: owner?.display_name ?? null,
    current_humidity: tree.moisture_pct ?? 0,
    humidity_status: healthToHumidityStatus(tree.health_state),
    sensor_id: detail?.sensor?.id ?? (tree.monitored ? tree.id : null),
    lat: tree.lat,
    lng: tree.lon,
    district: tree.stadtteil,
    created_at: tree.created_at ?? tree.last_reading_at ?? new Date().toISOString(),
  }
}

export function mapSensor(sensor: ApiSensor): Sensor {
  return {
    id: sensor.id,
    name: sensor.stadtteil ? `Sensor · ${sensor.stadtteil}` : `Sensor #${sensor.id.slice(0, 8)}`,
    model_type: `#${sensor.id.slice(0, 8)}`,
    status: sensorStatusToApp(sensor.status),
    installed_at: sensor.last_seen_at ?? new Date().toISOString(),
    last_activity: sensor.last_seen_at ?? new Date().toISOString(),
    lat: sensor.lat,
    lng: sensor.lon,
    covered_tree_ids: [sensor.tree_id],
    battery_level: null,
    created_at: sensor.last_seen_at ?? new Date().toISOString(),
  }
}

export function mapReading(treeId: string, reading: ApiReading): SensorReading {
  return {
    id: String(reading.id ?? `${treeId}-${reading.measured_at}`),
    sensor_id: reading.sensor_id ?? '',
    tree_id: treeId,
    value: reading.moisture_pct,
    timestamp: reading.measured_at,
  }
}

function growHistory(
  finalValue: number,
  days = 30,
  startRatio = 0.8,
): Array<{ date: string; value: number }> {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date()
    date.setDate(date.getDate() - (days - 1 - i))
    const progress = i / (days - 1)
    const base = finalValue * startRatio + finalValue * (1 - startRatio) * progress
    const noise = base * 0.04 * (Math.sin(i * 1.7) * 0.5 + 0.5)
    return {
      date: date.toISOString().split('T')[0],
      value: Math.round(base + noise),
    }
  })
}

export function mapStatsOverview(stats: ApiStatsOverview): NetworkStats {
  const sensorTotal = Object.values(stats.sensors).reduce((a, b) => a + b, 0)
  return {
    daily_users: stats.users_total,
    daily_users_history: growHistory(stats.users_total, 30, 0.78),
    total_sensors: stats.trees_monitored,
    sensors_history: growHistory(sensorTotal, 30, 0.73),
    data_points: stats.partnerships_active,
    data_points_history: growHistory(stats.partnerships_active, 30, 0.82),
    data_points_monthly_delta_pct: 0,
    registered_trees: stats.trees_total,
    trees_history: growHistory(stats.trees_total, 30, 0.73),
  }
}

export function mapStadtteilCounts(rows: ApiStadtteil[]) {
  return rows.map((row) => ({
    district: row.stadtteil,
    sensor_count: row.monitored,
    tree_count: row.trees,
    needs_water: row.needs_water,
  }))
}

function inferCondition(precip: number): WeatherCondition {
  if (precip >= 5) return 'rainy'
  if (precip >= 1) return 'partly-cloudy'
  return 'sunny'
}

export function mapWeather(payload: ApiWeather): WeatherDay[] {
  const current = payload.current ?? {}
  const days = payload.daily ?? []
  if (days.length === 0) {
    return [
      {
        date: new Date().toISOString().slice(0, 10),
        condition: 'partly-cloudy',
        temp_high: current.temperature_2m ?? 20,
        temp_low: (current.temperature_2m ?? 20) - 5,
        precipitation_mm: current.precipitation ?? 0,
        humidity_pct: current.relative_humidity_2m ?? 50,
      },
    ]
  }
  return days.map((day) => ({
    date: day.date,
    condition: inferCondition(day.precip_mm ?? 0),
    temp_high: day.temp_max ?? 20,
    temp_low: (day.temp_max ?? 20) - 6,
    precipitation_mm: day.precip_mm ?? 0,
    humidity_pct: current.relative_humidity_2m ?? 50,
  }))
}

export type {
  ApiTree,
  ApiTreeDetail,
  ApiSensor,
  ApiReading,
  ApiStatsOverview,
  ApiStadtteil,
  ApiWeather,
}
