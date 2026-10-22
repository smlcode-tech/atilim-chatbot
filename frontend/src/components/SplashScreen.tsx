import { motion, useIsPresent } from 'motion/react'
import { assistant } from '../config/assistant'

export function SplashScreen() {
  // Çıkış başlayınca alttaki sayfa görünür olur; solmakta olan katman tıklamaları yutmamalı.
  const isPresent = useIsPresent()

  return (
    <motion.div
      style={{ ...wrapper, pointerEvents: isPresent ? 'auto' : 'none' }}
      exit={{ transition: { when: 'afterChildren' } }}
    >
      {/* Arka plan — logodan sonra, yavaşça solarak hazır sayfayı açar */}
      <motion.div
        style={bg}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.75, ease: 'easeInOut' }}
      />

      {/* Sembol — girişte gecikmeyle belirir; çıkışta gecikmesiz, arka plandan önce solar.
          Girişteki gecikme çıkışa da uygulansa logo, arka plan gittikten sonra sayfanın
          üstünde tek başına kalırdı. */}
      <motion.div
        style={logoWrap}
        initial={{ opacity: 0, scale: 0.75 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.85, transition: { duration: 0.35, ease: 'easeIn' } }}
        transition={{
          opacity:  { duration: 0.5, delay: 0.65 },
          scale:    { duration: 0.5, delay: 0.65, ease: 'easeInOut' },
          default:  { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] },
        }}
      >
        <img
          src="/favicon.svg"
          alt={assistant.name}
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
