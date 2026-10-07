"use client";

import { motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Footer } from "@/components/landing/Footer";
import { apiUrl } from "@/lib/api";

// ==============================================================
// 1. HELPER COMPONENTS & FUNCTIONS
// ==============================================================
const formatUrl = (url: string) => {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  
  // Sesuaikan basis URL backend jika diperlukan, atau ambil dari environment variable
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "https://api.squarecloudsmc.com";
  return `${backendBase}${url.startsWith("/") ? "" : "/"}${url}`;
};

const toRoman = (num: number) => {
  const roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
  return roman[num - 1] || num.toString();
};

const RevealText = ({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) => (
  <div className="overflow-hidden leading-tight">
    <motion.div
      initial={{ y: "100%" }}
      whileInView={{ y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 1, delay, ease: [0.76, 0, 0.24, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  </div>
);

// ==============================================================
// 2. LAYOUT 2022: ALTERNATING KIRI - KANAN (CHAPTER I)
// ==============================================================
const ChapterLeftRight = ({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) => {
  return (
    <section className="w-full px-6 md:px-12 max-w-[1400px] mx-auto py-24 overflow-hidden">
      <div className="mb-24 text-center">
        <RevealText className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-4">
          // {chapterStr} //
        </RevealText>
        <RevealText
          delay={0.1}
          className="text-4xl md:text-6xl font-black tracking-tighter uppercase text-slate-900"
        >
          {year}
        </RevealText>
      </div>

      <div className="flex flex-col gap-32">
        {data.map((c, idx) => {
          const isEven = idx % 2 === 0;
          return (
            <div
              key={c.id}
              className={`flex flex-col md:flex-row items-center gap-12 md:gap-24 ${isEven ? "md:flex-row" : "md:flex-row-reverse"}`}
            >
              <motion.div
                initial={{ opacity: 0, x: isEven ? -50 : 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1, ease: [0.76, 0, 0.24, 1] }}
                className="w-full md:w-3/4 bg-slate-100 rounded-sm overflow-hidden shadow-xl"
              >
                <img
                  src={formatUrl(c.thumbnail_url)}
                  alt={c.title || "Project Image"}
                  className="block w-full h-auto object-contain hover:scale-[1.02] transition-transform duration-[1.5s]"
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1, delay: 0.2 }}
                className="w-full md:w-1/4 flex flex-col"
              >
                {c.title && (
                  <h3 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight mb-6">
                    {c.title}
                  </h3>
                )}
                {c.description && (
                  <p className="text-slate-500 text-lg leading-relaxed">{c.description}</p>
                )}
                {!c.title && !c.description && (
                  <span className="text-sm font-bold text-blue-600 uppercase tracking-widest">
                    ARCHIVE • {c.year}
                  </span>
                )}
              </motion.div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

// ==============================================================
// ==============================================================
// 3. LAYOUT 2023: FULL-SCREEN HORIZONTAL MOVIE TAPE (CHAPTER II)
// ==============================================================
const ChapterMagazine = ({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const updateViewport = () => setIsMobile(mediaQuery.matches);

    updateViewport();
    mediaQuery.addEventListener("change", updateViewport);
    return () => mediaQuery.removeEventListener("change", updateViewport);
  }, []);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  const xTransform = useTransform(
    scrollYProgress,
    [0, 1],
    ["0vw", `-${Math.max(0, data.length * (isMobile ? 100 : 92) - 100)}vw`]
  );

  return (
    <div
      ref={containerRef}
      className="relative h-[300vh] md:h-[400vh] w-full bg-black border-y border-black"
    >
      <div className="sticky top-0 h-[100svh] w-full overflow-hidden bg-black md:h-screen">
        <div className="absolute top-6 md:top-10 left-6 md:left-12 z-40 text-white pointer-events-none mix-blend-difference">
          <p className="text-[10px] md:text-xs font-bold uppercase tracking-[0.25em] mb-1">
            // {chapterStr} //
          </p>
          <h2 className="text-2xl md:text-4xl font-black tracking-tight uppercase">
            {year}
          </h2>
        </div>

        <motion.div
          style={{ x: xTransform }}
          className="flex h-[100svh] w-max items-center md:h-screen"
        >
          {data.map((c, idx) => (
            <div
              key={c.id}
              className="relative h-[100svh] w-screen flex-shrink-0 overflow-hidden border-r border-white/10 md:h-screen md:w-[92vw]"
            >
              <div
                aria-hidden="true"
                className="absolute inset-0 scale-110 bg-cover bg-center opacity-45 blur-xl md:hidden"
                style={{ backgroundImage: `url("${formatUrl(c.thumbnail_url)}")` }}
              />
              <img
                src={formatUrl(c.thumbnail_url)}
                alt={c.title || "Cinematic project"}
                className="relative z-10 block h-full w-full object-contain grayscale-[15%] opacity-95 transition-all duration-[1.5s] ease-out md:object-cover"
              />

              <div className="absolute inset-0 z-20 bg-gradient-to-t from-black/90 via-black/10 to-transparent pointer-events-none" />

              <div className="absolute left-5 right-5 bottom-8 z-30 text-white md:left-12 md:right-12 md:bottom-14">
                <div className="flex items-end justify-between gap-8">
                  <div>
                    <span className="inline-flex text-[9px] md:text-[10px] font-bold uppercase tracking-[0.22em] border border-white/30 bg-black/20 backdrop-blur-sm px-3 py-1.5 rounded-full mb-4">
                      SCENE 0{idx + 1}
                    </span>
                    {c.title && (
                        <h3 className="text-4xl sm:text-6xl md:text-8xl lg:text-9xl font-black uppercase tracking-tight leading-[0.9] md:leading-[0.82] max-w-6xl text-white/45">
                        {c.title}
                      </h3>
                    )}
                  </div>

                  <div className="hidden md:block max-w-sm text-right shrink-0">
                    {c.description && (
                      <p className="text-white/45 text-sm lg:text-base leading-relaxed">
                        {c.description}
                      </p>
                    )}
                    <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.24em] text-white/30">
                      {String(idx + 1).padStart(2, "0")} / {String(data.length).padStart(2, "0")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
};

// ==============================================================
// 4. LAYOUT 2024: FULL-WIDTH EDITORIAL CASCADE (CHAPTER III)
// ==============================================================
const ChapterArtsyCascade = ({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) => {
  const galleryFeed: { url: string; title: string | null; year: string; isMain: boolean }[] = [];
  data.forEach((c) => {
    galleryFeed.push({
      url: formatUrl(c.thumbnail_url),
      title: c.title,
      year: c.year,
      isMain: true,
    });
    if (c.gallery_urls) {
      c.gallery_urls
        .split(",")
        .filter(Boolean)
        .forEach((gUrl: string) => {
          galleryFeed.push({ url: formatUrl(gUrl), title: c.title, year: c.year, isMain: false });
        });
    }
  });

  return (
    <section className="w-full py-32 px-6 md:px-12 max-w-[1600px] mx-auto overflow-hidden">
      <div className="mb-24 md:mb-40 md:w-1/2">
        <RevealText className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-6">
          // {chapterStr} //
        </RevealText>
        <RevealText
          delay={0.1}
          className="text-4xl md:text-6xl font-black tracking-tighter uppercase text-slate-900 leading-[1.1] mb-8"
        >
          2024
        </RevealText>
      </div>

      <div className="flex flex-col gap-20 md:gap-40 w-full pb-20">
        {galleryFeed.map((img, idx) => {
          let sizingClass = "";
          if (img.isMain) {
            const mainSizing = [
              "w-full md:w-[76%] mr-auto",
              "w-full md:w-[66%] ml-auto",
              "w-full md:w-[88%] mx-auto",
              "w-[92%] md:w-[54%] ml-[4%]",
            ];
            sizingClass = mainSizing[Math.floor(idx / 1) % mainSizing.length];
          } else if (idx % 3 === 0) {
            sizingClass = "w-[86%] md:w-[52%] ml-auto";
          } else if (idx % 3 === 1) {
            sizingClass = "w-[82%] md:w-[46%] ml-[4%]";
          } else {
            sizingClass = "w-[88%] md:w-[48%] mx-auto";
          }

          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 80 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 1.2, ease: [0.76, 0, 0.24, 1] }}
              className={`${sizingClass} flex flex-col group`}
            >
              <div className="w-full overflow-hidden bg-slate-50 shadow-sm border border-gray-100 rounded-sm">
                <img
                  src={img.url}
                  className="w-full h-auto object-cover hover:scale-[1.03] transition-transform duration-[1.5s] ease-out"
                  alt={img.title || "Exhibition"}
                />
              </div>

              {img.isMain && (
                <div className="mt-4 flex justify-between items-start px-2">
                  <div className="flex flex-col">
                    {img.title && (
                      <h3 className="text-xl md:text-2xl font-black text-slate-900 uppercase tracking-tight">
                        {img.title}
                      </h3>
                    )}
                  </div>
                  <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest bg-blue-50 px-2 py-1 rounded shrink-0">
                    {img.year}
                  </span>
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </section>
  );
};

// ==============================================================
// ==============================================================
// 5. LAYOUT 2025: FULL-SCREEN VERTICAL IMAGE STACK (CHAPTER IV)
// ==============================================================
const ChapterFullscreenStack = ({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) => {
  return (
    <section className="w-full bg-black overflow-hidden">
      {data.map((project, idx) => (
        <article
          key={project.id}
          className="relative h-screen min-h-[100svh] w-full overflow-hidden bg-black"
        >
          <img
            src={formatUrl(project.thumbnail_url)}
            alt={project.title || "Vertical project"}
            loading={idx === 0 ? "eager" : "lazy"}
            decoding="async"
            className="block h-full w-full object-cover"
          />

          <div className="absolute inset-0 bg-black/10 pointer-events-none" />

          {idx === 0 && (
            <div className="absolute top-6 md:top-10 left-6 md:left-12 z-20 text-white pointer-events-none">
              <p className="text-[10px] md:text-xs font-bold uppercase tracking-[0.25em] mb-1 text-white/45">
                // {chapterStr} //
              </p>
              <h2 className="text-2xl md:text-4xl font-black tracking-tight uppercase text-white/45">
                {year}
              </h2>
            </div>
          )}

          <div className="absolute inset-x-6 md:inset-x-12 bottom-8 md:bottom-14 flex items-end justify-between gap-8">
            <div className="max-w-5xl">
              <span className="inline-flex text-[9px] md:text-[10px] font-bold uppercase tracking-[0.22em] border border-white/20 bg-black/10 px-3 py-1.5 rounded-full mb-4 text-white/45">
                SCENE 0{idx + 1}
              </span>

              {project.title && (
                <h3 className="text-5xl sm:text-6xl md:text-8xl lg:text-9xl font-black uppercase tracking-tight leading-[0.82] text-white/45">
                  {project.title}
                </h3>
              )}
            </div>

            <div className="hidden md:flex flex-col items-end gap-3 text-right shrink-0">
              {project.description && (
                <p className="max-w-sm text-sm lg:text-base leading-relaxed text-white/45">
                  {project.description}
                </p>
              )}

              <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-[0.24em] text-white/35">
                <span>{String(idx + 1).padStart(2, "0")} / {String(data.length).padStart(2, "0")}</span>
              </div>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
};

// ==============================================================
// 6. LAYOUT 2026+: ASYMMETRICAL EDITORIAL GRID (CHAPTER V)
// ==============================================================
const ChapterAsymmetrical = ({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) => {
  return (
    <section className="w-full py-32 px-6 md:px-12 max-w-[1600px] mx-auto bg-white overflow-hidden">
      <div className="mb-24 text-center md:text-left">
        <RevealText className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-4">
          // {chapterStr} //
          <RevealText
            delay={0.1}
            className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-6"
          >
            Our Best Works Archive / 2022 - NOW
          </RevealText>
        </RevealText>
      </div>

      <div className="flex flex-col gap-28 md:gap-40">
        {data.map((c, idx) => {
          const galleryImgs = c.gallery_urls
            ? c.gallery_urls.split(",").filter(Boolean)
            : [];

          const gallerySpans = [
            "md:col-span-7 md:translate-y-0",
            "md:col-span-5 md:translate-y-20",
            "md:col-span-6 md:col-start-2 md:-translate-y-10",
            "md:col-span-8 md:col-start-5 md:translate-y-4",
            "md:col-span-5 md:-translate-y-8",
            "md:col-span-7 md:col-start-3 md:translate-y-8",
          ];

          return (
            <div key={c.id} className="w-full">
              {/* Thumbnail: always large, full and centered */}
              <motion.div
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1, ease: [0.76, 0, 0.24, 1] }}
                className="w-full md:w-[84%] lg:w-[76%] mx-auto"
              >
                <div className="relative w-full overflow-hidden rounded-sm bg-slate-100 shadow-2xl">
                  <img
                    src={formatUrl(c.thumbnail_url)}
                    alt={c.title || "Project thumbnail"}
                    className="block w-full h-auto object-contain"
                  />
                  <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-md px-3 py-1 rounded-full text-xs font-bold text-slate-900 shadow-md">
                    NO. 0{idx + 1}
                  </div>
                </div>

                <div className="mt-6 px-2 text-center">
                  {c.title && (
                    <h3 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight uppercase mb-3">
                      {c.title}
                    </h3>
                  )}

                  {c.description && (
                    <p className="text-slate-500 text-base md:text-lg leading-relaxed max-w-3xl mx-auto">
                      {c.description}
                    </p>
                  )}
                </div>
              </motion.div>

              {/* Asymmetry is used only inside the gallery */}
              {galleryImgs.length > 0 && (
                <div className="mt-14 md:mt-20">
                  <div className="mb-6 md:mb-10 flex items-end justify-between gap-6">
                    <div>
                      <p className="text-[10px] md:text-xs font-bold text-blue-600 uppercase tracking-[0.25em]">
                        Project Gallery
                      </p>
                      <p className="text-sm text-slate-400 mt-1">
                        {galleryImgs.length} images
                      </p>
                    </div>
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">
                      Archive 0{idx + 1}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-12 items-start">
                    {galleryImgs.map((galleryUrl: string, galleryIdx: number) => {
                      const spanClass = gallerySpans[galleryIdx % gallerySpans.length];

                      return (
                        <motion.div
                          key={`${c.id}-gallery-${galleryIdx}`}
                          initial={{ opacity: 0, y: 50 }}
                          whileInView={{ opacity: 1, y: 0 }}
                          viewport={{ once: true, margin: "-80px" }}
                          transition={{
                            duration: 0.9,
                            delay: galleryIdx * 0.08,
                            ease: [0.76, 0, 0.24, 1],
                          }}
                          className={`flex flex-col ${spanClass} group`}
                        >
                          <div className="relative w-full overflow-hidden rounded-sm bg-slate-100 shadow-xl border border-gray-100">
                            <img
                              src={formatUrl(galleryUrl)}
                              alt={`${c.title || "Project"} gallery ${galleryIdx + 1}`}
                              className="block w-full h-auto object-cover transition-transform duration-1000 ease-out group-hover:scale-[1.03]"
                            />
                          </div>

                          <div className="mt-3 px-1 flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                              Detail {String(galleryIdx + 1).padStart(2, "0")}
                            </span>
                            <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest">
                              {c.year}
                            </span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

// MAIN PAGE COMPONENT
// ==============================================================
export default function CommissionPage() {
  const [commissions, setCommissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(apiUrl("/cms/commissions"));
        const data = await res.json();
        const mappedData = (data.data || []).map((item: any) => ({
          ...item,
          year: item.year || "2024",
        }));
        setCommissions(mappedData);
      } catch (error) {
        console.error("Gagal menarik data komisi:", error);
      } finally {
        setLoading(false);
        setTimeout(() => setIsTransitioning(false), 800);
      }
    };
    fetchData();
  }, []);

  const sortedCommissions = [...commissions].sort(
    (a, b) => (parseInt(a.year) || 0) - (parseInt(b.year) || 0)
  );

  const uniqueYears = Array.from(new Set(sortedCommissions.map((c) => c.year || "2024")));

  const heroProject = sortedCommissions[sortedCommissions.length - 1];

  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-blue-200 selection:text-blue-900 flex flex-col font-sans">
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
                {loading ? "Preparing ..." : "Our Portfolio"}
              </motion.h1>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="relative z-10 w-full flex-grow flex flex-col">
        {/* HERO OPENING */}
        <section className="w-full pt-32 md:pt-40 pb-32 px-6 md:px-12 max-w-[1600px] mx-auto overflow-hidden">
          <RevealText
            delay={0.1}
            className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6"
          >
            Our Best Works Archive / 2022 - NOW
          </RevealText>
          <RevealText
            delay={0.2}
            className="text-[14vw] md:text-[11vw] font-black tracking-tighter uppercase text-slate-900 leading-[0.85] mb-4"
          >
            Shaping
          </RevealText>
          <RevealText
            delay={0.3}
            className="text-[14vw] md:text-[11vw] font-black tracking-tighter uppercase text-blue-600 leading-[0.85] md:text-right md:pr-12"
          >
            The Unthinkable.
          </RevealText>

          {heroProject && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 1.2, delay: 0.5, ease: [0.76, 0, 0.24, 1] }}
              className="mt-32 w-full aspect-video md:aspect-[21/9] bg-slate-100 overflow-hidden rounded-sm"
            >
              <img
                src={formatUrl(heroProject.thumbnail_url)}
                alt={heroProject.title || "Archive"}
                className="w-full h-full object-cover grayscale opacity-80 hover:grayscale-0 hover:opacity-100 transition-all duration-[1.5s] ease-[cubic-bezier(0.25,1,0.5,1)]"
              />
            </motion.div>
          )}
        </section>

        {/* DYNAMIC CHAPTER LOOP */}
        {uniqueYears.map((year, index) => {
          const chapterData = sortedCommissions.filter((c) => c.year === year);
          if (chapterData.length === 0) return null;

          const chapterStr = `CHAPTER ${toRoman(index + 1)}`;
          let renderedChapter = null;
          if (index === 0) {
            renderedChapter = (
              <ChapterLeftRight data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else if (index === 1) {
            renderedChapter = (
              <ChapterMagazine data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else if (index === 2) {
            renderedChapter = (
              <ChapterArtsyCascade data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else if (index === 3) {
            renderedChapter = (
              <ChapterFullscreenStack data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else {
            renderedChapter = (
              <ChapterAsymmetrical data={chapterData} year={year} chapterStr={chapterStr} />
            );
          }

          return (
            <div key={year} className="w-full flex flex-col">
              {renderedChapter}
            </div>
          );
        })}

        {/* CLOSING: EDITORIAL METRICS & CTA */}
        <section className="w-full pt-32 pb-40 px-6 md:px-12 max-w-[1600px] mx-auto overflow-hidden">
          <div className="flex flex-col items-center text-center">
            <a href="mailto:squarecloudsmc@gmail.com" className="group block pointer-events-auto">
              <RevealText className="text-[12vw] md:text-[9vw] font-black tracking-tighter uppercase text-slate-900 leading-none group-hover:text-blue-600 transition-colors duration-500">
                GET IN TOUCH
              </RevealText>
            </a>
          </div>
        </section>

        {/* FOOTER */}
        <div className="w-full mt-32 md:mt-40 border-t border-gray-100 pt-12">
          <Footer />
        </div>
      </main>
    </div>
  );
}