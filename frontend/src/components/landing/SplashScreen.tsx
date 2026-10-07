"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface SplashScreenProps {
  onFinish?: () => void;
}

export function SplashScreen({ onFinish }: SplashScreenProps) {
  const [isVisible, setIsVisible] = useState<boolean>(true);

  // Fungsi ini otomatis terpanggil saat detik terakhir video selesai diputar
  const handleVideoEnd = () => {
    setIsVisible(false);
    if (onFinish) onFinish();
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="splash-overlay"
          initial={{ y: 0 }}
          exit={{ y: "-100%" }} // Efek tirai terbuka ke atas tetap dipertahankan
          transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
          // bg hijau disesuaikan agar menyatu dengan background video jika layarnya ultrawide
          className="fixed inset-0 z-[999999] bg-[#009b00] flex items-center justify-center overflow-hidden"
        >
          <video
            src="/sc_animation.mp4"
            autoPlay
            muted       // Wajib muted agar browser mengizinkan autoplay
            playsInline // Wajib untuk iOS/Safari mobile
            onEnded={handleVideoEnd}
            className="w-full h-full object-cover pointer-events-none"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}