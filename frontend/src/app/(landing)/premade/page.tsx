"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { ShoppingCart } from "lucide-react";
import Link from "next/link";
import { Footer } from "@/components/landing/Footer";

export default function PremadeStorePage() {
  const [premades, setPremades] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);
  const [activeCategory, setActiveCategory] = useState("All");

  // 1. Tarik Data Backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("https://api.squarecloudsmc.com/cms/premades");
        const data = await res.json();
        // Fallback default category
        const mappedData = (data.data || []).map((item: any) => ({
          ...item,
          category: item.category || "Worlds",
        }));
        setPremades(mappedData);
      } catch (error) {
        console.error("Gagal menarik data premade:", error);
      } finally {
        setLoading(false);
        setTimeout(() => setIsTransitioning(false), 800);
      }
    };
    fetchData();
  }, []);

  // CATATAN: useEffect penyembunyi navbar sudah DIHAPUS agar Navbar utama tetap tampil.

  const formatUrl = (url: string) => {
    if (!url) return "";
    return url.startsWith("http") ? url : `https://api.squarecloudsmc.com${url}`;
  };

  const categories = ["All", ...Array.from(new Set(premades.map((p) => p.category)))];
  const filteredPremades =
    activeCategory === "All" ? premades : premades.filter((p) => p.category === activeCategory);

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-slate-900 font-sans selection:bg-blue-200 flex flex-col">
      {/* =========================================
          CURTAIN TRANSITION (SPLASH SCREEN)
          ========================================= */}
      <AnimatePresence>
        {(loading || isTransitioning) && (
          <motion.div
            key="curtain"
            initial={{ y: 0 }}
            exit={{ y: "-100%" }}
            transition={{ duration: 1, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-0 z-[99999] bg-[#1a65d6] flex flex-col items-center justify-center"
          >
            <div className="overflow-hidden flex items-center gap-4 px-4">
              <motion.img
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.6 }}
                src="/logo.png"
                alt="Squareclouds"
                className="h-10 md:h-12 w-auto drop-shadow-md rounded-xl"
              />
              <motion.h1
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.6 }}
                className="text-3xl md:text-5xl font-black text-white tracking-tight"
              >
                {loading ? "Loading Assets..." : "Asset Vault."}
              </motion.h1>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Padding Top disesuaikan ke pt-28 md:pt-36 agar aman dari header navbar */}
      <main className="relative z-10 w-full flex-grow flex flex-col pt-28 md:pt-36 pb-24 px-6 md:px-12 max-w-[1600px] mx-auto">
        {/* =========================================
            HEADER (Clean Marketplace Style)
            ========================================= */}
        <section className="w-full mb-12 flex flex-col items-center text-center">
          <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 uppercase">
            The Asset Vault
          </h1>
          <p className="text-slate-500 font-medium text-base mt-4 max-w-xl">
            High-quality voxel architectures and server setups ready for deployment.
          </p>
        </section>

        {/* =========================================
            FILTER BAR (Diubah jadi statis rapi, tidak sticky/dynamic)
            ========================================= */}
        <div className="w-full flex justify-center mb-16">
          <div className="bg-white/90 backdrop-blur-xl p-1.5 rounded-full shadow-sm border border-slate-200 flex overflow-x-auto max-w-full no-scrollbar">
            {categories.map((cat, idx) => (
              <button
                key={idx}
                onClick={() => setActiveCategory(cat as string)}
                className={`relative px-6 py-2 rounded-full text-xs font-bold tracking-widest uppercase transition-colors whitespace-nowrap ${
                  activeCategory === cat ? "text-white" : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {activeCategory === cat && (
                  <motion.div
                    layoutId="active-pill"
                    className="absolute inset-0 bg-slate-900 rounded-full -z-10 shadow-sm"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* =========================================
            STORE GRID (3 Kolom Max agar kartu lebih lebar)
            ========================================= */}
        <section className="w-full">
          <motion.div
            layout
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-10"
          >
            <AnimatePresence>
              {filteredPremades.map((p, idx) => (
                <motion.div
                  layout
                  key={p.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.4, delay: idx * 0.05 }}
                  className="group bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl border border-slate-200 transition-all duration-300 flex flex-col h-full"
                >
                  {/* Image Container */}
                  <div className="w-full aspect-[16/10] bg-slate-100 overflow-hidden relative">
                    <img
                      src={formatUrl(p.image_url)}
                      alt={p.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
                    />

                    {/* Category Badge */}
                    <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-sm px-3 py-1.5 rounded-lg shadow-sm flex items-center">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-800">
                        {p.category}
                      </span>
                    </div>
                  </div>

                  {/* Info Area */}
                  <div className="p-6 flex-grow flex flex-col">
                    <div className="flex justify-between items-start gap-4 mb-3">
                      <h3 className="text-xl font-black text-slate-900 tracking-tight leading-snug group-hover:text-blue-600 transition-colors">
                        {p.title}
                      </h3>
                      {/* Price Tag */}
                      <span className="text-base font-black text-emerald-700 bg-emerald-50 border border-emerald-100 px-3 py-1 rounded-lg shrink-0">
                        ${p.price_usd}
                      </span>
                    </div>

                    {p.description && (
                      <p className="text-slate-500 text-sm font-medium line-clamp-2 leading-relaxed mb-8">
                        {p.description}
                      </p>
                    )}

                    {/* Action Button: BUY NOW + CART ICON */}
                    <div className="mt-auto pt-5 border-t border-slate-100">
                      <a
                        href={p.link || "#"}
                        target={p.link ? "_blank" : "_self"}
                        className="w-full bg-slate-50 hover:bg-blue-600 text-slate-700 hover:text-white border border-slate-200 hover:border-blue-600 py-3.5 rounded-xl flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-widest transition-all duration-300"
                      >
                        <ShoppingCart size={16} />
                        Buy Now
                      </a>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>

          {filteredPremades.length === 0 && (
            <div className="w-full py-32 flex flex-col items-center justify-center text-slate-400">
              <p className="text-sm font-bold uppercase tracking-widest">
                No assets found in this category.
              </p>
            </div>
          )}
        </section>
      </main>

      {/* Jarak ke footer diperbesar (mt-32 md:mt-40) */}
      <div className="w-full mt-32 md:mt-40">
        <Footer />
      </div>
    </div>
  );
}