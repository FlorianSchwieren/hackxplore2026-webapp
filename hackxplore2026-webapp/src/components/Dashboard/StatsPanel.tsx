import { useNavigate } from 'react-router-dom'
import { ArrowRight, BarChart3 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNetworkStats } from '@/lib/queries/useStats'
import { useMapContext } from '@/context/MapContext'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import StatCard from './StatCard'
import WeatherWidget from './WeatherWidget'

const PEEK_HEIGHT = 220

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
        className="fixed bottom-0 left-0 right-0 z-20 bg-[rgba(10,10,10,0.95)] backdrop-blur-[20px] border-t border-white/[0.06] rounded-t-2xl overflow-y-auto panel-scroll"
        style={{ maxHeight: '85vh' }}
        initial={{ y: PEEK_HEIGHT }}
        animate={{ y: isStatsPanelOpen ? 0 : PEEK_HEIGHT }}
        drag="y"
        dragConstraints={{ top: 0, bottom: PEEK_HEIGHT }}
        onDragEnd={(_, info) => {
          if (info.offset.y > 60) {
            if (isStatsPanelOpen) toggleStatsPanel()
          } else {
            if (!isStatsPanelOpen) toggleStatsPanel()
          }
        }}
        transition={{ type: 'spring', damping: 30, stiffness: 250 }}
      >
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 bg-white/20 rounded-full" />
        </div>
        <PanelContent />
      </motion.div>
    </>
  )
}
