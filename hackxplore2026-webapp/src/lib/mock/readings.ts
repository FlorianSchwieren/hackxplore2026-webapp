import type { SensorReading } from '@/types'
import { mockTrees } from './trees'
import { mockSensors } from './sensors'

function hashStr(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  }
  return h >>> 0
}

function makePrng(seed: number) {
  let s = seed
  return () => {
    s = (s + 0x6d2b79f5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const DISTRIBUTIONS = ['declining', 'recovering', 'stable', 'volatile', 'stepped'] as const
type Distribution = (typeof DISTRIBUTIONS)[number]

function shapeValues(dist: Distribution, currentValue: number, rand: () => number, N: number): number[] {
  const raw: number[] = []

  if (dist === 'declining') {
    const startOffset = 22 + rand() * 18
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1)
      raw.push(currentValue + startOffset * (1 - t) + (rand() - 0.5) * 6)
    }
  } else if (dist === 'recovering') {
    const startOffset = 12 + rand() * 14
    const rainDay = 16 + Math.floor(rand() * 6)
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1)
      const base = currentValue - startOffset * (1 - t)
      const rain = i >= rainDay && i <= rainDay + 2 ? 14 + rand() * 8 : 0
      raw.push(base + rain + (rand() - 0.5) * 5)
    }
  } else if (dist === 'stable') {
    const phase = rand() * Math.PI * 2
    for (let i = 0; i < N; i++) {
      const wave = Math.sin(i * 0.7 + phase) * 7 + Math.cos(i * 0.35 + phase) * 4
      raw.push(currentValue + wave + (rand() - 0.5) * 3)
    }
  } else if (dist === 'volatile') {
    for (let i = 0; i < N; i++) {
      const swing = (rand() - 0.5) * 26
      const wave = Math.sin(i * 1.1) * 9
      raw.push(currentValue + swing + wave)
    }
  } else {
    // stepped: flat for first half, then a step, settling at current
    const stepDay = 11 + Math.floor(rand() * 7)
    const dir = rand() > 0.5 ? 1 : -1
    const stepSize = dir * (12 + rand() * 14)
    for (let i = 0; i < N; i++) {
      const base = i < stepDay ? currentValue - stepSize : currentValue
      raw.push(base + (rand() - 0.5) * 5)
    }
  }

  // Smoothly land the last 3 points on currentValue
  raw[N - 3] = raw[N - 3] * 0.65 + currentValue * 0.35
  raw[N - 2] = raw[N - 2] * 0.35 + currentValue * 0.65
  raw[N - 1] = currentValue

  return raw.map((v) => Math.round(Math.max(3, Math.min(97, v)) * 10) / 10)
}

function generateReadings(sensorId: string, treeId: string, currentValue: number): SensorReading[] {
  const seed = hashStr(treeId + sensorId)
  const rand = makePrng(seed)
  const dist = DISTRIBUTIONS[seed % DISTRIBUTIONS.length]
  const N = 30

  const values = shapeValues(dist, currentValue, rand, N)

  return values.map((value, i) => {
    const date = new Date()
    date.setDate(date.getDate() - (N - 1 - i))
    date.setHours(9, 0, 0, 0)
    return {
      id: `r-${sensorId}-${treeId}-${i}`,
      sensor_id: sensorId,
      tree_id: treeId,
      value,
      timestamp: date.toISOString(),
    }
  })
}

export const mockReadings: SensorReading[] = mockSensors.flatMap((sensor) =>
  sensor.covered_tree_ids.flatMap((treeId) => {
    const tree = mockTrees.find((t) => t.id === treeId)
    return generateReadings(sensor.id, treeId, tree?.current_humidity ?? 50)
  }),
)
