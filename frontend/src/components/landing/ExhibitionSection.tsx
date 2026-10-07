"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { apiUrl } from "@/lib/api";

export function ExhibitionSection() {
  const [exhibitions, setExhibitions] = useState<any[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const fetchExhibitions = async () => {
      try {
        const res = await fetch(apiUrl("/cms/exhibitions"));
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        
        const itemsList = Array.isArray(data) ? data : (data.data && Array.isArray(data.data) ? data.data : []);

        if (itemsList.length > 0) {
          let items = itemsList;
          while (items.length > 0 && items.length < 6) {
            items = [...items, ...items];
          }
          setExhibitions(items);
        }
      } catch (error) {
        console.error("Gagal menarik data Exhibition:", error);
      } finally {
        setIsReady(true);
      }
    };
    fetchExhibitions();
  }, []);

  if (!isReady || exhibitions.length === 0) return null;

  const getScatteredStyle = (index: number) => {
    const styles = [
      "-rotate-6 translate-y-6",
      "rotate-3 -translate-y-4",
      "-rotate-2 -translate-y-8",
      "rotate-6 translate-y-2",
      "-rotate-3 translate-y-8",
      "rotate-2 -translate-y-2",
    ];
    return styles[index % styles.length];
  };

  const getImageUrl = (rawImg: string) => {
    if (!rawImg) return "";
    if (rawImg.startsWith("http")) return rawImg;
    const apiDomain = process.env.NEXT_PUBLIC_API_URL || "/api";
    const cleanPath = rawImg.startsWith("/") ? rawImg : `/${rawImg}`;
    return `${apiDomain}${cleanPath}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1.2, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative z-30 w-full mt-32 overflow-x-hidden"
    >
      <div
        className="w-full pt-8 pb-24"
        style={{
          maskImage:
            "linear-gradient(to right, transparent 0%, black 15%, black 85%, transparent 100%)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent 0%, black 15%, black 85%, transparent 100%)",
        }}
      >
        <motion.div
          animate={{ x: ["0%", "-50%"] }}
          transition={{ ease: "linear", duration: 45, repeat: Infinity }}
          className="flex w-max"
        >
          {/* GRUP 1 */}
          <div className="flex items-center gap-8 md:gap-12 px-4 md:px-6">
            {exhibitions.map((item, idx) => {
              const imgUrl = getImageUrl(item.image_url);

              return (
                <div
                  key={`grup1-${idx}`}
                  className={`w-[200px] h-[280px] md:w-[240px] md:h-[340px] rounded-[32px] overflow-hidden flex-shrink-0 relative group bg-slate-900 shadow-[0_8px_16px_rgba(0,0,0,0.08)] hover:shadow-[0_15px_30px_rgba(0,0,0,0.15)] transition-all duration-500 cursor-default hover:z-10 hover:!rotate-0 hover:!translate-y-0 hover:scale-110 ${getScatteredStyle(idx)}`}
                >
                  {item.image_url ? (
                    <img
                      src={imgUrl}
                      alt="Project Showcase"
                      className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-500 font-bold bg-slate-800">
                      NO IMG
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* GRUP 2 */}
          <div className="flex items-center gap-8 md:gap-12 px-4 md:px-6" aria-hidden="true">
            {exhibitions.map((item, idx) => {
              const imgUrl = getImageUrl(item.image_url);

              return (
                <div
                  key={`grup2-${idx}`}
                  className={`w-[200px] h-[280px] md:w-[240px] md:h-[340px] rounded-[32px] overflow-hidden flex-shrink-0 relative group bg-slate-900 shadow-[0_8px_16px_rgba(0,0,0,0.08)] hover:shadow-[0_15px_30px_rgba(0,0,0,0.15)] transition-all duration-500 cursor-default hover:z-10 hover:!rotate-0 hover:!translate-y-0 hover:scale-110 ${getScatteredStyle(idx)}`}
                >
                  {item.image_url ? (
                    <img
                      src={imgUrl}
                      alt="Project Showcase"
                      className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-500 font-bold bg-slate-800">
                      NO IMG
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}