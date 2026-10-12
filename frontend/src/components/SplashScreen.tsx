import { motion } from 'motion/react'

export function SplashScreen() {
  return (
    <motion.div
      style={wrapper}
      exit={{ transition: { when: 'afterChildren' } }}
    >
      {/* Arka plan — önce solar */}
      <motion.div
        style={bg}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.75, ease: 'easeInOut' }}
      />

      {/* Sembol — arka plan kaybolduktan sonra solar */}
      <motion.div
        style={logoWrap}
        initial={{ opacity: 0, scale: 0.75 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.85 }}
        transition={{
          opacity:  { duration: 0.5, delay: 0.65 },
          scale:    { duration: 0.5, delay: 0.65, ease: 'easeInOut' },
          default:  { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] },
        }}
      >
        <img
          src="/favicon.svg"
          alt="Atılım Asistan"
          width={120}
          height={120}
          style={{ borderRadius: 24 }}
        />
      </motion.div>
    </motion.div>
  )
}

const wrapper: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 9999,
}

const bg: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: '#283480',
}

const logoWrap: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}
