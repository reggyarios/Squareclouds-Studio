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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
          
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
              <div className="product-card product-card--axe relative bg-white rounded-[32px] shadow-sm p-8 flex flex-col items-center justify-center min-h-[360px] md:min-h-0 md:h-[320px] overflow-hidden cursor-pointer">
                <div className="product-card__wash absolute inset-0 bg-gradient-to-b from-transparent to-[#302216]/10 pointer-events-none"></div>

                <div className="product-card__art relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 drop-shadow-sm">
                  <div
                    className="product-card__silhouette absolute inset-0 bg-[#302216]"
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
                    className="product-card__image absolute inset-0 w-full h-full object-contain"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#302216] text-center">
                  Commission
                </h3>

                <div className="product-card__description relative z-10 overflow-hidden flex flex-col items-center text-center">
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
              <div className="product-card product-card--emerald relative bg-white rounded-[32px] shadow-sm p-8 flex flex-col items-center justify-center min-h-[360px] md:min-h-0 md:h-[320px] overflow-hidden cursor-pointer">
                <div className="product-card__wash absolute inset-0 bg-gradient-to-b from-transparent to-[#024e01]/10 pointer-events-none"></div>

                <div className="product-card__art relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 drop-shadow-sm">
                  <div
                    className="product-card__silhouette absolute inset-0 bg-[#024e01]"
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
                    className="product-card__image absolute inset-0 w-full h-full object-contain"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#024e01] text-center">
                  Marketplace
                </h3>

                <div className="product-card__description relative z-10 overflow-hidden flex flex-col items-center text-center">
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
              <div className="product-card product-card--chest relative bg-white rounded-[32px] shadow-sm p-8 flex flex-col items-center justify-center min-h-[360px] md:min-h-0 md:h-[320px] overflow-hidden cursor-pointer">
                <div className="product-card__wash absolute inset-0 bg-gradient-to-b from-transparent to-[#134e4a]/14 pointer-events-none"></div>

                <div className="product-card__art relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 drop-shadow-sm">
                  <div
                    className="product-card__silhouette absolute inset-0 bg-[#111827]"
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
                    className="product-card__image absolute inset-0 w-full h-full object-contain"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#134e4a] text-center">
                  Premade Assets
                </h3>

                <div className="product-card__description relative z-10 overflow-hidden flex flex-col items-center text-center">
                  <p className="text-slate-500 text-sm font-medium leading-relaxed">
                    Ready-to-use premium voxel assets, structures, and beautifully detailed level
                    designs.
                  </p>
                </div>
              </div>
            </a>
          </motion.div>

          {/* 4. MINECRAFT JAVA SERVER */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <a
              href="/minecraft-server"
              onClick={(e) => triggerTransition(e, "/minecraft-server")}
              className="block w-full h-full select-none"
            >
              <div className="product-card product-card--server relative bg-white rounded-[32px] shadow-sm p-8 flex flex-col items-center justify-center min-h-[360px] md:min-h-0 md:h-[320px] overflow-hidden cursor-pointer">
                <div className="product-card__wash absolute inset-0 bg-gradient-to-b from-transparent to-[#4ea8de]/15 pointer-events-none" />

                <div className="product-card__art relative z-10 w-24 h-24 md:w-28 md:h-28 mb-5 drop-shadow-sm">
                  <div
                    className="product-card__silhouette absolute inset-0 bg-[#4ea8de]"
                    style={{
                      maskImage: "url('/nether-star.webp')",
                      WebkitMaskImage: "url('/nether-star.webp')",
                      maskSize: "contain",
                      WebkitMaskSize: "contain",
                      maskPosition: "center",
                      WebkitMaskPosition: "center",
                      maskRepeat: "no-repeat",
                      WebkitMaskRepeat: "no-repeat",
                    }}
                  />
                  <img
                    src="/nether-star.webp"
                    alt="Minecraft Server"
                    className="w-full h-full object-contain"
                  />
                </div>

                <h3 className="relative z-10 text-xl md:text-2xl font-black text-[#328dcc] text-center">
                  Minecraft Server
                </h3>

                <div className="product-card__description relative z-10 overflow-hidden flex flex-col items-center text-center">
                  <p className="text-slate-500 text-sm font-medium leading-relaxed">
                    A Squareclouds community server for builders.
                  </p>
                </div>
              </div>
            </a>
          </motion.div>
          
        </div>
      </div>
      <style jsx global>{`
        .product-card__wash {
          opacity: 0;
          transition: opacity 700ms ease;
        }

        .product-card__art,
        .product-card__silhouette,
        .product-card__image,
        .product-card__description {
          transition: all 500ms ease;
        }

        .product-card__silhouette { opacity: 0; }
        .product-card__image { opacity: 1; }
        .product-card__description {
          max-height: none;
          margin-top: 0.75rem;
          opacity: 1;
        }

        @media (min-width: 1024px) and (hover: hover) and (pointer: fine) {
          .product-card__silhouette { opacity: 1; }
          .product-card__image { opacity: 0; }

          .product-card__description {
            max-height: 0;
            margin-top: 0;
            opacity: 0;
          }

          .product-card:hover {
            transform: translateY(-0.75rem) scale(1.02);
          }

          .product-card:active {
            transform: translateY(0.25rem) scale(0.93);
          }

          .product-card--axe:hover {
            box-shadow: inset 0 0 30px rgba(48, 34, 22, 0.08), 0 20px 40px rgba(48, 34, 22, 0.12);
          }

          .product-card--emerald:hover {
            box-shadow: inset 0 0 30px rgba(2, 78, 1, 0.08), 0 20px 40px rgba(2, 78, 1, 0.12);
          }

          .product-card--chest:hover {
            box-shadow: inset 0 0 30px rgba(19, 78, 74, 0.1), 0 20px 40px rgba(15, 23, 42, 0.16);
          }

          .product-card--server:hover {
            box-shadow: inset 0 0 30px rgba(78, 168, 222, 0.12), 0 20px 40px rgba(78, 168, 222, 0.18);
          }

          .product-card:hover .product-card__wash { opacity: 1; }
          .product-card:hover .product-card__art {
            transform: translateY(-0.5rem) scale(1.1);
          }
          .product-card:hover .product-card__art:not(:has(.product-card__image)) {
            filter: drop-shadow(0 20px 12px rgb(15 23 42 / 0.2));
          }
          .product-card:hover .product-card__silhouette { opacity: 0; }
          .product-card:hover .product-card__image { opacity: 1; }
          .product-card:hover .product-card__description {
            max-height: 150px;
            margin-top: 0.75rem;
            opacity: 1;
          }
        }
      `}</style>
    </section>
  );
}