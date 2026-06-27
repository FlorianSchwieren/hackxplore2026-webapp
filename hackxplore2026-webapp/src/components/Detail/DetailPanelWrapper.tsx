import { AnimatePresence, motion } from 'framer-motion'
import { useMediaQuery } from '@/hooks/useMediaQuery'

interface DetailPanelWrapperProps {
  isOpen: boolean
  children: React.ReactNode
}

export default function DetailPanelWrapper({ isOpen, children }: DetailPanelWrapperProps) {
  const isMobile = useMediaQuery('(max-width: 768px)')

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={
            isMobile
              ? 'fixed bottom-0 left-0 right-0 h-[85vh] z-50 bg-[rgba(10,10,10,0.97)] backdrop-blur-[20px] border-t border-white/[0.08] rounded-t-2xl flex flex-col overflow-hidden'
              : 'fixed top-14 right-0 w-[380px] h-[calc(100vh-56px)] z-30 bg-[rgba(10,10,10,0.92)] backdrop-blur-[20px] border-l border-white/[0.06] overflow-y-auto panel-scroll'
          }
          initial={isMobile ? { y: '100%' } : { x: '100%' }}
          animate={isMobile ? { y: 0 } : { x: 0 }}
          exit={isMobile ? { y: '100%' } : { x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        >
          {isMobile ? (
            <div className="overflow-y-auto panel-scroll flex-1">
              {children}
            </div>
          ) : children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
