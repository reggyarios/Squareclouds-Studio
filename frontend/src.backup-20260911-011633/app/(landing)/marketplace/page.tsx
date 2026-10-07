"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Star,
  Shirt,
  Globe,
  Puzzle,
  Layers,
  Sparkles,
  Filter,
  ChevronDown,
  ShoppingCart,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Footer } from "@/components/landing/Footer";

// --- Helper Icon berdasarkan Kategori ---
const getCategoryIcon = (type: string) => {
  const t = type.toLowerCase();
  if (t.includes("skin")) return <Shirt size={16} />;
  if (t.includes("world") || t.includes("spawn") || t.includes("map")) return <Globe size={16} />;
  if (t.includes("add-on") || t.includes("addon")) return <Puzzle size={16} />;
  return <Layers size={16} />;
};

export default function MarketplacePage() {
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);

  // --- Fitur Search, Filter, & Pagination ---
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 12;

  const filterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("https://squarecloudsmc.com/cms/marketplaces");
        const data = await res.json();
        if (data.data) {
          const sortedData = [...data.data].reverse();
          setMarketplaces(sortedData);
        }
      } catch (error) {
        console.error("Gagal menarik data marketplace:", error);
      } finally {
        setLoading(false);
        setTimeout(() => setIsTransitioning(false), 800);
      }
    };
    fetchData();
  }, []);

  // Menyembunyikan SEMUA Global Navbar & Header secara agresif

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, activeCategory]);

  const formatUrl = (url: string) => {
    if (!url) return "";
    return url.startsWith("http") ? url : `https://squarecloudsmc.com${url}`;
  };

  const uniqueCategories = Array.from(new Set(marketplaces.map((item) => item.content_type)));

  const topFeatured = marketplaces.length > 0 ? marketplaces[0] : null;
  const topList = marketplaces.slice(1, 5);

  const filteredGridData = marketplaces.filter((item) => {
    const matchSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCategory = activeCategory === "All" || item.content_type === activeCategory;
    return matchSearch && matchCategory;
  });

  const totalPages = Math.ceil(filteredGridData.length / ITEMS_PER_PAGE);
  const paginatedData = filteredGridData.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-slate-900 flex flex-col font-sans selection:bg-blue-200">
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
                {loading ? "Loading Catalog..." : "Marketplace."}
              </motion.h1>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="pt-16 md:pt-24 px-6 md:px-12 max-w-[1400px] mx-auto flex flex-col gap-16">
        {marketplaces.length > 0 && (
          <section className="w-full">
            <h2 className="text-xl font-black text-slate-400 tracking-widest mb-6 uppercase">
              Latest Releases
            </h2>

            <div className="flex flex-col lg:flex-row gap-5 h-auto lg:h-[480px]">
              {/* FEATURED ITEM */}
              {topFeatured && (
                <a
                  href={topFeatured.link || "#"}
                  target={topFeatured.link ? "_blank" : "_self"}
                  className="w-full lg:w-2/3 h-[300px] lg:h-full bg-white rounded-2xl flex flex-col group cursor-pointer border border-slate-200 hover:border-blue-500 hover:shadow-xl hover:shadow-blue-500/5 transition-all overflow-hidden"
                >
                  <div className="w-full flex-grow overflow-hidden bg-slate-100">
                    <img
                      src={formatUrl(topFeatured.image_url)}
                      alt={topFeatured.title}
                      className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-700"
                    />
                  </div>
                  <div className="p-6 flex justify-between items-center h-[25%] border-t border-slate-100 bg-white">
                    <div>
                      <h3 className="text-2xl font-black text-slate-900 mb-1 group-hover:text-blue-600 transition-colors line-clamp-1">
                        {topFeatured.title}
                      </h3>
                      <p className="text-blue-600 text-xs font-bold uppercase tracking-widest">
                        {topFeatured.content_type}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 font-black text-lg text-slate-900 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
                      <img src="/minecoin.png" alt="Minecoin" className="w-5 h-5 object-contain" />
                      {topFeatured.price_minecoin}
                    </div>
                  </div>
                </a>
              )}

              {/* 4 LIST ITEMS */}
              {topList.length > 0 && (
                <div className="w-full lg:w-1/3 flex flex-col gap-4 h-[500px] lg:h-full">
                  {topList.map((item, index) => (
                    <a
                      href={item.link || "#"}
                      target={item.link ? "_blank" : "_self"}
                      key={item.id}
                      className="flex-1 bg-white rounded-xl border border-slate-200 flex group cursor-pointer hover:border-blue-500 hover:shadow-md transition-all overflow-hidden"
                    >
                      <div className="w-[35%] bg-slate-100 overflow-hidden flex-shrink-0">
                        <img
                          src={formatUrl(item.image_url)}
                          alt={item.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      </div>
                      <div className="p-4 flex flex-col justify-center flex-grow w-[65%]">
                        <h4 className="text-base font-black text-slate-900 line-clamp-1 group-hover:text-blue-600 transition-colors">
                          {item.title}
                        </h4>
                        <p className="text-blue-600 text-[10px] font-bold uppercase tracking-wider mt-1">
                          {item.content_type}
                        </p>
                        <div className="flex items-center justify-end mt-2">
                          <div className="flex items-center gap-1 font-black text-xs text-slate-900 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200">
                            <img
                              src="/minecoin.png"
                              alt="Minecoin"
                              className="w-3.5 h-3.5 object-contain"
                            />
                            {item.price_minecoin}
                          </div>
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* =========================================
            SEARCH BAR & DROPDOWN FILTER
            ========================================= */}
        <section className="w-full z-30 relative pt-10 border-t border-slate-200">
          <div className="flex flex-col md:flex-row items-center gap-4">
            <div className="relative flex-grow w-full">
              <Search
                className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400"
                size={22}
              />
              <input
                type="text"
                placeholder="Search other products, skin packs, worlds..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-slate-200 text-slate-900 px-14 py-4 rounded-2xl font-medium focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-sm placeholder:text-slate-400"
              />
            </div>

            <div className="relative w-full md:w-auto shrink-0" ref={filterRef}>
              <button
                onClick={() => setIsFilterOpen(!isFilterOpen)}
                className="w-full md:w-auto flex items-center justify-between gap-3 bg-white border border-slate-200 text-slate-900 px-6 py-4 rounded-2xl font-bold hover:bg-slate-50 transition-colors shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <Filter size={18} className="text-blue-600" />
                  <span className="max-w-[120px] truncate">
                    {activeCategory === "All" ? "All Categories" : activeCategory}
                  </span>
                </div>
                <ChevronDown
                  size={18}
                  className={`text-slate-400 transition-transform ${isFilterOpen ? "rotate-180" : ""}`}
                />
              </button>

              <AnimatePresence>
                {isFilterOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 top-full mt-3 w-full md:w-56 bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden flex flex-col z-50"
                  >
                    {["All", ...uniqueCategories].map((cat, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setActiveCategory(cat as string);
                          setIsFilterOpen(false);
                        }}
                        className={`flex items-center gap-3 px-5 py-3.5 text-left text-sm font-bold transition-colors ${
                          activeCategory === cat
                            ? "bg-blue-50 text-blue-600"
                            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                        }`}
                      >
                        {cat !== "All" && getCategoryIcon(cat as string)}
                        {cat === "All" ? "All Categories" : cat}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </section>

        {/* =========================================
            OTHER PRODUCTS (PAGINATED GRID)
            ========================================= */}
        <section className="w-full">
          <h2 className="text-xl font-black text-slate-900 tracking-tight uppercase mb-6">
            Other Products
          </h2>

          {paginatedData.length === 0 ? (
            <div className="w-full py-20 flex flex-col items-center justify-center text-slate-400">
              <p className="text-sm font-bold uppercase tracking-widest">
                Tidak ada produk ditemukan.
              </p>
            </div>
          ) : (
            <>
              {/* Grid Basic Tanpa Glitch Animasi */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {paginatedData.map((item, idx) => (
                  <a
                    href={item.link || "#"}
                    target={item.link ? "_blank" : "_self"}
                    key={item.id}
                    className="group bg-white rounded-2xl p-3 border border-slate-200 hover:border-blue-500 hover:shadow-lg transition-all flex flex-col cursor-pointer"
                  >
                    <div className="w-full aspect-[16/9] bg-slate-100 rounded-xl overflow-hidden relative mb-3">
                      <img
                        src={formatUrl(item.image_url)}
                        alt={item.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    </div>

                    <div className="flex flex-col flex-grow px-1">
                      <h3 className="text-slate-900 font-bold text-sm line-clamp-1 mb-1 group-hover:text-blue-600 transition-colors">
                        {item.title}
                      </h3>
                      <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-4">
                        {getCategoryIcon(item.content_type)}
                        <span>{item.content_type}</span>
                      </div>

                      <div className="mt-auto flex items-center justify-between pt-3 border-t border-slate-100">
                        <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-widest text-blue-600 group-hover:text-blue-700">
                          <ShoppingCart size={14} /> Buy Now
                        </div>
                        <div className="flex items-center gap-1 font-black text-sm text-slate-900 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                          <img
                            src="/minecoin.png"
                            alt="Minecoin"
                            className="w-4 h-4 object-contain"
                          />
                          {item.price_minecoin}
                        </div>
                      </div>
                    </div>
                  </a>
                ))}
              </div>

              {/* PAGINATION CONTROLS */}
              {totalPages > 1 && (
                <div className="w-full flex items-center justify-center gap-6 mt-16">
                  <button
                    onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="p-3 rounded-xl bg-white border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm"
                  >
                    <ChevronLeft size={20} />
                  </button>
                  <div className="text-sm font-bold text-slate-500 tracking-widest uppercase">
                    Page <span className="text-slate-900 text-lg mx-1">{currentPage}</span> of{" "}
                    {totalPages}
                  </div>
                  <button
                    onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="p-3 rounded-xl bg-white border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm"
                  >
                    <ChevronRight size={20} />
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </main>

      <div className="mt-32 md:mt-40 w-full mt-auto flex-shrink-0">
        <Footer />
      </div>
    </div>
  );
}
