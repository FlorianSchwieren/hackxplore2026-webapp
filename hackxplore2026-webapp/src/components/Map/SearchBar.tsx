import { useDeferredValue, useMemo, useRef, useState } from 'react'
import { Search, TreePine, Radio, MapPin } from 'lucide-react'
import { useMapContext } from '@/context/MapContext'
import { useTrees } from '@/lib/queries/useTrees'
import { useSensors } from '@/lib/queries/useSensors'
import { KARLSRUHE_DISTRICTS } from '@/lib/mock/stats'

type ResultType = 'tree' | 'sensor' | 'district'
interface SearchResult {
  type: ResultType
  id: string
  label: string
  sublabel: string
  lat: number
  lng: number
}

interface SearchBarProps {
  onSelect?: () => void
}

const TYPE_ICONS: Record<ResultType, typeof TreePine> = {
  tree: TreePine,
  sensor: Radio,
  district: MapPin,
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [focused, setFocused] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const deferredQuery = useDeferredValue(query)

  const { flyTo, selectTree, selectSensor } = useMapContext()
  const { data: trees } = useTrees()
  const { data: sensors } = useSensors()

  const allItems = useMemo<SearchResult[]>(
    () => [
      ...(trees ?? []).map((t) => ({
        type: 'tree' as const,
        id: t.id,
        label: t.name,
        sublabel: `${t.common_name} · ${t.district}`,
        lat: t.lat,
        lng: t.lng,
      })),
      ...(sensors ?? []).map((s) => ({
        type: 'sensor' as const,
        id: s.id,
        label: s.name,
        sublabel: s.model_type,
        lat: s.lat,
        lng: s.lng,
      })),
      ...KARLSRUHE_DISTRICTS.map((d) => ({
        type: 'district' as const,
        id: d.name,
        label: d.name,
        sublabel: 'Stadtteil · Karlsruhe',
        lat: d.lat,
        lng: d.lng,
      })),
    ],
    [trees, sensors]
  )

  const results = useMemo(() => {
    if (!deferredQuery.trim()) return []
    return allItems
      .filter((item) => item.label.toLowerCase().includes(deferredQuery.toLowerCase()))
      .slice(0, 8)
  }, [allItems, deferredQuery])

  const showDropdown = focused && results.length > 0

  function handleSelect(item: SearchResult) {
    flyTo(item.lat, item.lng, item.type === 'district' ? 14 : 16)
    if (item.type === 'tree') selectTree(item.id)
    if (item.type === 'sensor') selectSensor(item.id)
    setQuery('')
    setActiveIdx(-1)
    inputRef.current?.blur()
    onSelect?.()
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, results.length - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, -1)) }
    if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); handleSelect(results[activeIdx]) }
    if (e.key === 'Escape') { setQuery(''); inputRef.current?.blur() }
  }

  return (
    <div className="relative">
      <div className="relative flex items-center">
        <Search className="absolute left-3 w-4 h-4 text-gray-500 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setActiveIdx(-1) }}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          onKeyDown={handleKeyDown}
          placeholder="Search trees, sensors, districts…"
          className="w-full pl-9 pr-3 py-2 bg-white/[0.06] border border-white/[0.1] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-accent-teal/50 focus:border-accent-teal/50 transition-all"
        />
      </div>

      {showDropdown && (
        <div className="absolute top-full mt-1 left-0 right-0 bg-[rgba(10,10,10,0.97)] backdrop-blur-[20px] border border-white/[0.08] rounded-xl shadow-glass max-h-64 overflow-y-auto z-50">
          {results.map((item, idx) => {
            const Icon = TYPE_ICONS[item.type]
            return (
              <button
                key={`${item.type}-${item.id}`}
                onMouseDown={() => handleSelect(item)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  idx === activeIdx ? 'bg-white/[0.08]' : 'hover:bg-white/[0.04]'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0 text-gray-500" />
                <div className="min-w-0">
                  <p className="text-sm text-white truncate">{item.label}</p>
                  <p className="text-xs text-gray-500 truncate">{item.sublabel}</p>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
