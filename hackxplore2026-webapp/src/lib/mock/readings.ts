import type { SensorReading } from '@/types'
import { mockTrees } from './trees'
import { mockSensors } from './sensors'

function generateReadings(
  sensorId: string,
  treeId: string,
  baseValue: number
): SensorReading[] {
  return Array.from({ length: 30 }, (_, i) => {
    const date = new Date()
    date.setDate(date.getDate() - (29 - i))
    date.setHours(9, 0, 0, 0)
    // Realistic drift: gradual trend + daily noise
    const trend = (i / 29) * (Math.random() > 0.5 ? 3 : -3)
    const noise = (Math.sin(i * 1.3) * 4 + Math.cos(i * 0.7) * 3)
    // Simulate a rain event around day 20
    const rainBoost = i >= 20 && i <= 22 ? 8 : 0
    const value = Math.max(3, Math.min(97, baseValue + trend + noise + rainBoost))
    return {
      id: `r-${sensorId}-${treeId}-${i}`,
      sensor_id: sensorId,
      tree_id: treeId,
      value: Math.round(value * 10) / 10,
      timestamp: date.toISOString(),
    }
  })
}

export const mockReadings: SensorReading[] = mockSensors.flatMap((sensor) =>
  sensor.covered_tree_ids.flatMap((treeId) => {
    const tree = mockTrees.find((t) => t.id === treeId)
    const baseValue = tree ? tree.current_humidity : 50
    return generateReadings(sensor.id, treeId, baseValue)
  })
)
