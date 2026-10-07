"use client";

import { motion } from "framer-motion";

export function ManifestoSection() {
  const heading = "Your vision lead us.";
  
  // Memecah kalimat menjadi array huruf (termasuk spasi) untuk efek mesin tik
  const letters = Array.from(heading);

  return (
    <section 
      id="manifesto" 
      className="w-full bg-white py-24 md:py-32 flex flex-col items-center justify-center px-6 relative z-10"
    >
      <div className="max-w-[850px] flex flex-col items-center text-center">
        
        {/* =========================================
            ANIMASI TYPEWRITER (MESIN TIK)
            ========================================= */}
        <motion.h2
          className="text-[#0a1128] font-black text-5xl md:text-6xl lg:text-[64px] tracking-tight mb-8"
          variants={{
            hidden: { opacity: 1 },
            visible: {
              opacity: 1,
              // Jeda antar huruf 0.05 detik
              transition: { staggerChildren: 0.05 },
            },
          }}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }} // WAJIB ADA: Memicu animasi HANYA SEKALI
        >
          {letters.map((char, index) => (
            <motion.span
              key={index}
              variants={{
                hidden: { opacity: 0 },
                visible: { opacity: 1 },
              }}
            >
              {char}
            </motion.span>
          ))}
        </motion.h2>

        {/* =========================================
            PARAGRAF MUNCUL SETELAH TYPEWRITER SELESAI
            ========================================= */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }} // WAJIB ADA: Memicu animasi HANYA SEKALI
          // Waktu Delay = (Total huruf * 0.05 detik) + jeda 0.2 detik
          transition={{ duration: 0.8, delay: letters.length * 0.05 + 0.2, ease: "easeOut" }}
          className="text-slate-500 font-medium text-lg md:text-[19px] leading-relaxed max-w-[800px]"
        >
          Established on July 6, 2022, Squareclouds is a creative collective uniting elite builders,
          3D modelers, and developers. Based in Medan, Indonesia, we blend engineering with artistry
          to build unforgettable interactive worlds that set new standards in digital entertainment.
        </motion.p>
        
      </div>
    </section>
  );
}