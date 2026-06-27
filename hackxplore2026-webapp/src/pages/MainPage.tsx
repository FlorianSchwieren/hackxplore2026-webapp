import Navbar from '@/components/common/Navbar'
import MapView from '@/components/Map/MapView'
import StatsPanel from '@/components/Dashboard/StatsPanel'
import TreeDetailPanel from '@/components/Detail/TreeDetailPanel'
import SensorDetailPanel from '@/components/Detail/SensorDetailPanel'

export default function MainPage() {
  return (
    <div className="relative w-full h-screen overflow-hidden bg-surface">
      <Navbar />

      {/* Full-screen map */}
      <div className="absolute inset-0 pt-14">
        <MapView />
      </div>

      {/* Stats panel (desktop: left sidebar / mobile: bottom drawer) */}
      <StatsPanel />

      {/* Entity detail panels */}
      <TreeDetailPanel />
      <SensorDetailPanel />
    </div>
  )
}
