import type { NetworkStats, UserProfile, WeatherDay } from '@/types'

function growHistory(
  finalValue: number,
  days = 30,
  startRatio = 0.8
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

export const mockNetworkStats: NetworkStats = {
  daily_users: 1247,
  daily_users_history: growHistory(1247, 30, 0.78),
  total_sensors: 15,
  sensors_history: growHistory(15, 30, 0.73),
  data_points: 284930,
  data_points_history: growHistory(284930, 30, 0.82),
  data_points_monthly_delta_pct: 12.4,
  registered_trees: 30,
  trees_history: growHistory(30, 30, 0.73),
}

export const mockUsers: UserProfile[] = [
  { id: 'u1', username: 'TreeGuard_KA', assigned_trees_count: 5, avatar_url: null, joined_at: '2024-01-05T10:00:00Z' },
  { id: 'u2', username: 'GreenKarlsruhe', assigned_trees_count: 4, avatar_url: null, joined_at: '2024-01-12T10:00:00Z' },
  { id: 'u3', username: 'StadtgrünKA', assigned_trees_count: 3, avatar_url: null, joined_at: '2024-02-08T10:00:00Z' },
  { id: 'u4', username: 'NatureKA', assigned_trees_count: 3, avatar_url: null, joined_at: '2024-02-20T10:00:00Z' },
  { id: 'u5', username: 'BaumFreund', assigned_trees_count: 2, avatar_url: null, joined_at: '2024-03-01T10:00:00Z' },
  { id: 'u6', username: 'OakWatcher', assigned_trees_count: 2, avatar_url: null, joined_at: '2024-03-15T10:00:00Z' },
  { id: 'u7', username: 'KlimaHelfer', assigned_trees_count: 1, avatar_url: null, joined_at: '2024-04-02T10:00:00Z' },
  { id: 'u8', username: 'LindenLiebe', assigned_trees_count: 1, avatar_url: null, joined_at: '2024-04-18T10:00:00Z' },
  { id: 'u9', username: 'ForstKA', assigned_trees_count: 1, avatar_url: null, joined_at: '2024-05-01T10:00:00Z' },
  { id: 'u10', username: 'ParkPfleger', assigned_trees_count: 1, avatar_url: null, joined_at: '2024-05-20T10:00:00Z' },
]

const today = new Date()
const nextDay = (offset: number) => {
  const d = new Date(today)
  d.setDate(d.getDate() + offset)
  return d.toISOString().split('T')[0]
}

export const mockWeather: WeatherDay[] = [
  { date: nextDay(0), condition: 'partly-cloudy', temp_high: 24, temp_low: 16, precipitation_mm: 0, humidity_pct: 58 },
  { date: nextDay(1), condition: 'sunny',          temp_high: 27, temp_low: 17, precipitation_mm: 0, humidity_pct: 52 },
  { date: nextDay(2), condition: 'cloudy',         temp_high: 22, temp_low: 15, precipitation_mm: 2, humidity_pct: 68 },
  { date: nextDay(3), condition: 'rainy',          temp_high: 19, temp_low: 13, precipitation_mm: 12, humidity_pct: 80 },
  { date: nextDay(4), condition: 'partly-cloudy', temp_high: 21, temp_low: 14, precipitation_mm: 1, humidity_pct: 70 },
]

export const KARLSRUHE_DISTRICTS = [
  { name: 'Innenstadt-West', lat: 49.0078, lng: 8.3942 },
  { name: 'Innenstadt-Ost', lat: 49.0048, lng: 8.4024 },
  { name: 'Weststadt', lat: 48.9997, lng: 8.3814 },
  { name: 'Südstadt', lat: 48.992, lng: 8.3901 },
  { name: 'Oststadt', lat: 49.0035, lng: 8.4143 },
  { name: 'Mühlburg', lat: 48.9998, lng: 8.3571 },
  { name: 'Nordstadt', lat: 49.015, lng: 8.3992 },
  { name: 'Nordweststadt', lat: 49.018, lng: 8.3756 },
  { name: 'Rintheim', lat: 49.0028, lng: 8.4312 },
  { name: 'Weiherfeld-Dammerstock', lat: 48.9851, lng: 8.3889 },
  { name: 'Rüppurr', lat: 48.9741, lng: 8.3901 },
  { name: 'Beiertheim-Bulach', lat: 48.9878, lng: 8.3745 },
  { name: 'Grünwinkel', lat: 48.9921, lng: 8.3598 },
  { name: 'Knielingen', lat: 49.0212, lng: 8.3478 },
]

export const mockDistrictSensorCounts = [
  { district: 'Innenstadt-West', sensor_count: 4 },
  { district: 'Oststadt', sensor_count: 3 },
  { district: 'Weststadt', sensor_count: 3 },
  { district: 'Südstadt', sensor_count: 3 },
  { district: 'Mühlburg', sensor_count: 2 },
  { district: 'Innenstadt-Ost', sensor_count: 2 },
  { district: 'Nordstadt', sensor_count: 1 },
  { district: 'Rintheim', sensor_count: 0 },
]
