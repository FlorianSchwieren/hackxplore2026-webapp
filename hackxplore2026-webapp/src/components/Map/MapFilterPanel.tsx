import { useState } from 'react'
import { SlidersHorizontal, X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMapContext } from '@/context/MapContext'

const STATUS_DOTS: Record<string, string> = {
  dry: '#ef4444',
  low: '#f97316',
  normal: '#22c55e',
  moist: '#06b6d4',
  active: '#06b6d4',
  inactive: '#6b7280',
}

const STATUS_LABELS: Record<string, string> = {
  dry: 'Dry',
  low: 'Low',
  normal: 'Normal',
  moist: 'Moist',
  active: 'Active',
  inactive: 'Inactive',
}

export default function MapFilterPanel() {
  const [open, setOpen] = useState(false)
  const { filters, toggleFilter, resetFilters } = useMapContext()

  return (
    <div className="absolute top-20 right-4 z-20">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[rgba(10,10,10,0.85)] backdrop-blur-[16px] border border-white/[0.08] text-sm text-gray-300 hover:text-white hover:border-white/20 transition-all shadow-glass"
        aria-label="Toggle filters"
      >
        <SlidersHorizontal className="w-4 h-4" />
        <span className="hidden sm:inline">Filter</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-2 right-0 w-56 bg-[rgba(10,10,10,0.95)] backdrop-blur-[20px] border border-white/[0.08] rounded-2xl shadow-glass overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Filter</span>
              <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-white transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Sensors */}
            <div className="px-4 py-3 border-b border-white/[0.06]">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Sensors</p>
              {(['active', 'inactive'] as const).map((key) => (
                <label key={key} className="flex items-center gap-2 py-1 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={filters.sensorStatus[key]}
                    onChange={() => toggleFilter('sensorStatus', key)}
                    className="sr-only"
                  />
                  <div
                    className={`w-4 h-4 rounded flex items-center justify-center border transition-colors ${
                      filters.sensorStatus[key]
                        ? 'border-transparent'
                        : 'border-white/20 bg-transparent'
                    }`}
                    style={filters.sensorStatus[key] ? { backgroundColor: STATUS_DOTS[key] } : {}}
                  >
                    {filters.sensorStatus[key] && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STATUS_DOTS[key] }} />
                    <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                      {STATUS_LABELS[key]}
                    </span>
                  </div>
                </label>
              ))}
            </div>

            {/* Tree Status */}
            <div className="px-4 py-3 border-b border-white/[0.06]">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Tree Status</p>
              {(['dry', 'low', 'normal', 'moist'] as const).map((key) => (
                <label key={key} className="flex items-center gap-2 py-1 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={filters.treeStatus[key]}
                    onChange={() => toggleFilter('treeStatus', key)}
                    className="sr-only"
                  />
                  <div
                    className={`w-4 h-4 rounded flex items-center justify-center border transition-colors ${
                      filters.treeStatus[key]
                        ? 'border-transparent'
                        : 'border-white/20 bg-transparent'
                    }`}
                    style={filters.treeStatus[key] ? { backgroundColor: STATUS_DOTS[key] } : {}}
                  >
                    {filters.treeStatus[key] && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STATUS_DOTS[key] }} />
                    <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                      {STATUS_LABELS[key]}
                    </span>
                  </div>
                </label>
              ))}
            </div>

            {/* Reset */}
            <div className="px-4 py-3">
              <button
                onClick={() => { resetFilters(); setOpen(false) }}
                className="w-full py-1.5 text-xs text-gray-400 hover:text-white border border-white/[0.08] hover:border-white/20 rounded-lg transition-colors"
              >
                Reset Filters
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
