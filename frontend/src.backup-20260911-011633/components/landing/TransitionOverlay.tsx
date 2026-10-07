"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function TransitionOverlay() {
  const [animating, setAnimating] = useState(false);
  const [phase, setPhase] = useState<"idle" | "white" | "blue">("idle");
  const [origin, setOrigin] = useState({ x: "50%", y: "50%" });
  const router = useRouter();

  useEffect(() => {
    const handleStartTransition = (e: any) => {
      const { path, x, y } = e.detail;
      // Ambil titik koordinat mouse saat card diklik
      setOrigin({ x: `${x}px`, y: `${y}px` });
      setAnimating(true);
      setPhase("white"); // 1. Mulai membesar dengan warna putih

      // 2. Setelah layar full putih (400ms), ubah warnanya jadi biru SC secara perlahan
      setTimeout(() => {
        setPhase("blue");
      }, 400);

      // 3. Setelah layar full biru (800ms), lakukan pindah halaman
      setTimeout(() => {
        router.push(path);
      }, 800);

      // 4. Hilangkan layer birunya (fade out) agar halaman barunya terlihat (1300ms)
      setTimeout(() => {
        setAnimating(false);
        setPhase("idle");
      }, 1300);
    };

    window.addEventListener("start-transition", handleStartTransition);
    return () => window.removeEventListener("start-transition", handleStartTransition);
  }, [router]);

  return (
    <AnimatePresence>
      {animating && (
        <motion.div
          className="fixed inset-0 z-[999999] pointer-events-none"
          // Animasi dimulai dari lingkaran sekecil 0px di posisi mouse, membesar menutupi layar
          initial={{ 
            clipPath: `circle(0px at ${origin.x} ${origin.y})`, 
            backgroundColor: "#ffffff" // Mulai dengan warna putih
          }}
          animate={{
            clipPath: `circle(3000px at ${origin.x} ${origin.y})`,
            backgroundColor: phase === "blue" ? "#2563eb" : "#ffffff" // Transisi ke biru (blue-600)
          }}
          exit={{ opacity: 0 }} // Menghilang perlahan (fade out)
          transition={{
            clipPath: { duration: 0.6, ease: [0.76, 0, 0.24, 1] },
            backgroundColor: { duration: 0.4, ease: "easeInOut" },
            opacity: { duration: 0.3 }
          }}
        />
      )}
    </AnimatePresence>
  );
}