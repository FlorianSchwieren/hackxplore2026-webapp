import { useNavigate } from 'react-router-dom'
import { ArrowRight, BarChart3, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNetworkStats } from '@/lib/queries/useStats'
import { useMapContext } from '@/context/MapContext'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import StatCard from './StatCard'
import WeatherWidget from './WeatherWidget'

function PanelContent() {
  const navigate = useNavigate()
  const { data: stats } = useNetworkStats()

  return (
    <>
      <div className="px-4 pt-4 pb-2">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Network Overview</p>
        <div className="flex flex-col gap-3">
          <StatCard
            label="Daily Users"
            value={stats?.daily_users ?? 0}
            history={stats?.daily_users_history}
          />
          <StatCard
            label="Total Sensors"
            value={stats?.total_sensors ?? 0}
            history={stats?.sensors_history}
            color="#06b6d4"
          />
          <StatCard
            label="Data Points"
            value={stats?.data_points ?? 0}
            delta={`${stats?.data_points_monthly_delta_pct ?? 0}% this month`}
            history={stats?.data_points_history}
          />
          <StatCard
            label="Registered Trees"
            value={stats?.registered_trees ?? 0}
            history={stats?.trees_history}
          />
        </div>
      </div>

      <div className="px-4 py-3">
        <button
          onClick={() => navigate('/stats')}
          className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-accent-green border border-accent-green/30 hover:bg-accent-green/10 rounded-xl transition-colors"
        >
          More Network Stats <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      <WeatherWidget />
    </>
  )
}

export default function StatsPanel() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const { isStatsPanelOpen, toggleStatsPanel } = useMapContext()

  if (!isMobile) {
    return (
      <aside className="fixed left-0 top-14 bottom-0 w-80 z-30 bg-[rgba(10,10,10,0.85)] backdrop-blur-[16px] border-r border-white/[0.06] overflow-y-auto panel-scroll">
        <PanelContent />
      </aside>
    )
  }

  // Mobile: bottom drawer
  return (
    <>
      {/* FAB toggle */}
      <button
        onClick={toggleStatsPanel}
        className="fixed bottom-6 right-4 z-30 w-12 h-12 rounded-full bg-accent-teal flex items-center justify-center shadow-glow-teal"
        aria-label="Toggle stats"
      >
        <BarChart3 className="w-5 h-5 text-white" />
      </button>

      {/* Drawer */}
      <motion.div
        className="fixed bottom-0 left-0 right-0 z-20 bg-[rgba(10,10,10,0.95)] backdrop-blur-[20px] border-t border-white/[0.06] rounded-t-2xl flex flex-col"
        style={{ maxHeight: '85vh', height: '85vh' }}
        initial={{ y: '100%' }}
        animate={{ y: isStatsPanelOpen ? 0 : '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 250 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] shrink-0">
          <p className="text-sm font-semibold text-white">Network Overview</p>
          <button
            onClick={toggleStatsPanel}
            className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors"
            aria-label="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-y-auto panel-scroll flex-1">
          <PanelContent />
        </div>
      </motion.div>
    </>
  )
}
