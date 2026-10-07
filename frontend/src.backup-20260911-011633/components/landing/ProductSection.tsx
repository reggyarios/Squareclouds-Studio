"use client";

import { motion } from "framer-motion";

export function ProductSection() {
  // Fungsi Pemicu Transisi Zoom Card
  const triggerTransition = (e: React.MouseEvent, path: string) => {
    e.preventDefault();
    const event = new CustomEvent("start-transition", {
      detail: { 
        path, 
        x: e.clientX, 
        y: e.clientY 
      },
    });
    window.dispatchEvent(event);
  };

  return (
    <section className="py-24 bg-white relative z-10">
      <div className="max-w-[1200px] mx-auto px-6 md:px-12 relative z-10">
        
        {/* HEADER SECTION */}
        <div className="flex flex-col items-center text-center mb-16 md:mb-20">
          <div className="flex gap-3 md:gap-4 mb-8 md:mb-10">
            <div className="w-5 h-5 md:w-6 md:h-6 rounded-md bg-gradient-to-tr from-cyan-400/40 to-blue-500/40 rotate-45"></div>
            <div className="w-5 h-5 md:w-6 md:h-6 rounded-md bg-gradient-to-tr from-cyan-400/40 to-blue-500/40 rotate-45"></div>
            <div className="w-5 h-5 md:w-6 md:h-6 rounded-md bg-gradient-to-tr from-cyan-400/40 to-blue-500/40 rotate-45"></div>
          </div>

          <h2 
            id="product" 
            className="scroll-mt-32 font-extrabold text-3xl md:text-4xl lg:text-[40px] text-slate-900 tracking-tight mb-4"
          >
            Products & Services
          </h2>
          <p className="text-slate-500 font-medium max-w-2xl mx-auto text-lg">
            Discover our products & services that empower your creative journey
          </p>
        </div>

        {/* CARDS GRID */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* 1. COMMISSION (WOODEN AXE) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <a 
              href="/commission" 
              onClick={(e) => triggerTransition(e, "/commission")}
              className="block w-full h-full select-none"
            >
              {/* Tanpa hover:border, hanya menggunakan in-shadow dan drop shadow yang bersih */}
              <div className="group relative bg-white rounded-[32px] border border-gray-200/60 shadow-sm hover:shadow-[inset_0_0_30px_rgba(48,34,22,0.08),0_20px_40px_rgba(48,34,22,0.12)] hover:-translate-y-3 hover:scale-[1.02] active:scale-[0.93] active:translate-y-1 active:shadow-inner active:duration-75 transition-all duration-300 p-8 flex flex-col items-center justify-center h-[280px] md:h-[320px] overflow-hidden cursor-pointer">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#302216]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>

                <div className="relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 transition-all duration-500 group-hover:-translate-y-2 group-hover:scale-110 group-active:scale-95 drop-shadow-sm group-hover:drop-shadow-xl">
                  <div
                    className="absolute inset-0 bg-[#302216] transition-opacity duration-500 opacity-100 group-hover:opacity-0"
                    style={{
                      maskImage: "url('/Wooden_Axe.png')",
                      WebkitMaskImage: "url('/Wooden_Axe.png')",
                      maskSize: "contain",
                      WebkitMaskSize: "contain",
                      maskPosition: "center",
                      WebkitMaskPosition: "center",
                      maskRepeat: "no-repeat",
                      WebkitMaskRepeat: "no-repeat",
                    }}
                  />
                  <img
                    src="/Wooden_Axe.png"
                    alt="Commission"
                    className="absolute inset-0 w-full h-full object-contain transition-opacity duration-500 opacity-0 group-hover:opacity-100"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#302216] text-center">
                  Commission
                </h3>

                <div className="relative z-10 overflow-hidden opacity-0 max-h-0 group-hover:max-h-[150px] group-hover:opacity-100 group-hover:mt-3 transition-all duration-700 flex flex-col items-center text-center">
                  <p className="text-slate-500 text-sm font-medium leading-relaxed">
                    Custom environments, game design, and 3D modeling tailored to your specific
                    vision.
                  </p>
                </div>
              </div>
            </a>
          </motion.div>

          {/* 2. MARKETPLACE (EMERALD) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <a 
              href="/marketplace" 
              onClick={(e) => triggerTransition(e, "/marketplace")}
              className="block w-full h-full select-none"
            >
              <div className="group relative bg-white rounded-[32px] border border-gray-200/60 shadow-sm hover:shadow-[inset_0_0_30px_rgba(2,78,1,0.08),0_20px_40px_rgba(2,78,1,0.12)] hover:-translate-y-3 hover:scale-[1.02] active:scale-[0.93] active:translate-y-1 active:shadow-inner active:duration-75 transition-all duration-300 p-8 flex flex-col items-center justify-center h-[280px] md:h-[320px] overflow-hidden cursor-pointer">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#024e01]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>

                <div className="relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 transition-all duration-500 group-hover:-translate-y-2 group-hover:scale-110 group-active:scale-95 drop-shadow-sm group-hover:drop-shadow-xl">
                  <div
                    className="absolute inset-0 bg-[#024e01] transition-opacity duration-500 opacity-100 group-hover:opacity-0"
                    style={{
                      maskImage: "url('/emerald.png')",
                      WebkitMaskImage: "url('/emerald.png')",
                      maskSize: "contain",
                      WebkitMaskSize: "contain",
                      maskPosition: "center",
                      WebkitMaskPosition: "center",
                      maskRepeat: "no-repeat",
                      WebkitMaskRepeat: "no-repeat",
                    }}
                  />
                  <img
                    src="/emerald.png"
                    alt="Marketplace"
                    className="absolute inset-0 w-full h-full object-contain transition-opacity duration-500 opacity-0 group-hover:opacity-100"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#024e01] text-center">
                  Marketplace
                </h3>

                <div className="relative z-10 overflow-hidden opacity-0 max-h-0 group-hover:max-h-[150px] group-hover:opacity-100 group-hover:mt-3 transition-all duration-700 flex flex-col items-center text-center">
                  <p className="text-slate-500 text-sm font-medium leading-relaxed">
                    High-quality official marketplace content crafted for millions of global
                    players.
                  </p>
                </div>
              </div>
            </a>
          </motion.div>

          {/* 3. PREMADE ASSETS (CHEST) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <a 
              href="/premade" 
              onClick={(e) => triggerTransition(e, "/premade")}
              className="block w-full h-full select-none"
            >
              <div className="group relative bg-white rounded-[32px] border border-gray-200/60 shadow-sm hover:shadow-[inset_0_0_30px_rgba(26,23,3,0.08),0_20px_40px_rgba(26,23,3,0.12)] hover:-translate-y-3 hover:scale-[1.02] active:scale-[0.93] active:translate-y-1 active:shadow-inner active:duration-75 transition-all duration-300 p-8 flex flex-col items-center justify-center h-[280px] md:h-[320px] overflow-hidden cursor-pointer">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#1a1703]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>

                <div className="relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 transition-all duration-500 group-hover:-translate-y-2 group-hover:scale-110 group-active:scale-95 drop-shadow-sm group-hover:drop-shadow-xl">
                  <div
                    className="absolute inset-0 bg-[#1a1703] transition-opacity duration-500 opacity-100 group-hover:opacity-0"
                    style={{
                      maskImage: "url('/Chest.webp')",
                      WebkitMaskImage: "url('/Chest.webp')",
                      maskSize: "contain",
                      WebkitMaskSize: "contain",
                      maskPosition: "center",
                      WebkitMaskPosition: "center",
                      maskRepeat: "no-repeat",
                      WebkitMaskRepeat: "no-repeat",
                    }}
                  />
                  <img
                    src="/Chest.webp"
                    alt="Premade Assets"
                    className="absolute inset-0 w-full h-full object-contain transition-opacity duration-500 opacity-0 group-hover:opacity-100"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#1a1703] text-center">
                  Premade Assets
                </h3>

                <div className="relative z-10 overflow-hidden opacity-0 max-h-0 group-hover:max-h-[150px] group-hover:opacity-100 group-hover:mt-3 transition-all duration-700 flex flex-col items-center text-center">
                  <p className="text-slate-500 text-sm font-medium leading-relaxed">
                    Ready-to-use premium voxel assets, structures, and beautifully detailed level
                    designs.
                  </p>
                </div>
              </div>
            </a>
          </motion.div>
          
        </div>
      </div>
    </section>
  );
}