import { motion } from 'framer-motion'

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-screen bg-surface">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full"
      />
    </div>
  )
}

export function InlineLoader() {
  return (
    <div className="w-5 h-5 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
  )
}
