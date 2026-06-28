import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import SearchBar from '@/components/Map/SearchBar'

export default function Navbar() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false)

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-40 h-14 flex items-center px-4 gap-4 bg-[rgba(10,10,10,0.85)] backdrop-blur-[16px] border-b border-white/[0.06]">
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <img src="/logo.png" alt="CommuniTree logo" className="w-7 h-7 object-contain" />
          <span className="text-sm font-semibold text-white hidden sm:block">CommuniTree</span>
        </div>

        {/* Nav tabs */}
        <div className="flex items-center gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isActive
                  ? 'text-accent-green bg-accent-green/10 font-medium'
                  : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
              }`
            }
          >
            Map
          </NavLink>
          <NavLink
            to="/stats"
            className={({ isActive }) =>
              `px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isActive
                  ? 'text-accent-green bg-accent-green/10 font-medium'
                  : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
              }`
            }
          >
            Statistics
          </NavLink>
          <NavLink
            to="/forecast"
            className={({ isActive }) =>
              `px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isActive
                  ? 'text-accent-green bg-accent-green/10 font-medium'
                  : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
              }`
            }
          >
            Forecast
          </NavLink>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Desktop search */}
        {!isMobile && (
          <div className="w-64">
            <SearchBar />
          </div>
        )}

        {/* Mobile search toggle */}
        {isMobile && (
          <button
            onClick={() => setMobileSearchOpen((v) => !v)}
            className="p-2 text-gray-400 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors"
            aria-label="Toggle search"
          >
            {mobileSearchOpen ? <X className="w-5 h-5" /> : <Search className="w-5 h-5" />}
          </button>
        )}
      </nav>

      {/* Mobile search bar — slides down below navbar */}
      <AnimatePresence>
        {isMobile && mobileSearchOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="fixed top-14 left-0 right-0 z-39 px-4 py-2 bg-[rgba(10,10,10,0.95)] backdrop-blur-[16px] border-b border-white/[0.06]"
          >
            <SearchBar onSelect={() => setMobileSearchOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
