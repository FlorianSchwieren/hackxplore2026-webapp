import { Sun, Cloud, CloudSun, CloudRain, CloudLightning } from 'lucide-react'
import { format } from 'date-fns'
import { mockWeather } from '@/lib/mock/stats'
import type { WeatherCondition } from '@/types'

const WEATHER_ICONS: Record<WeatherCondition, typeof Sun> = {
  sunny: Sun,
  cloudy: Cloud,
  'partly-cloudy': CloudSun,
  rainy: CloudRain,
  stormy: CloudLightning,
}

const WEATHER_COLORS: Record<WeatherCondition, string> = {
  sunny: '#fbbf24',
  cloudy: '#9ca3af',
  'partly-cloudy': '#d1d5db',
  rainy: '#60a5fa',
  stormy: '#a78bfa',
}

export default function WeatherWidget() {
  const today = mockWeather[0]
  const TodayIcon = WEATHER_ICONS[today.condition]
  const todayColor = WEATHER_COLORS[today.condition]

  const rainDay = mockWeather.slice(1).find((d) => d.precipitation_mm > 5)
  const impactText = rainDay
    ? `Rain on ${format(new Date(rainDay.date), 'EEEE')} may reduce watering needs by ~30%.`
    : 'No significant rain expected. Monitor dry trees closely.'

  return (
    <div className="px-4 pb-4">
      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Weather · Karlsruhe</p>

        {/* Current */}
        <div className="flex items-center gap-3 mb-3">
          <TodayIcon className="w-8 h-8 shrink-0" style={{ color: todayColor }} />
          <div>
            <p className="text-2xl font-bold text-white">{today.temp_high}°C</p>
            <p className="text-xs text-gray-400 capitalize">{today.condition.replace('-', ' ')} · {today.humidity_pct}% humidity</p>
          </div>
        </div>

        {/* 5-day forecast */}
        <div className="flex justify-between mb-3">
          {mockWeather.map((day) => {
            const Icon = WEATHER_ICONS[day.condition]
            const color = WEATHER_COLORS[day.condition]
            return (
              <div key={day.date} className="flex flex-col items-center gap-1">
                <p className="text-xs text-gray-500">{format(new Date(day.date), 'EEE')}</p>
                <Icon className="w-4 h-4" style={{ color }} />
                <p className="text-xs text-white font-medium">{day.temp_high}°</p>
                {day.precipitation_mm > 0 && (
                  <p className="text-xs text-blue-400">{day.precipitation_mm}mm</p>
                )}
              </div>
            )
          })}
        </div>

        {/* Impact */}
        <div className="pt-3 border-t border-white/[0.06]">
          <p className="text-xs text-gray-400 leading-relaxed">{impactText}</p>
        </div>
      </div>
    </div>
  )
}
