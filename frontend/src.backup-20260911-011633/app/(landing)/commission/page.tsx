"use client";

import { motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import { useState, useEffect, useRef, useMemo, memo } from "react";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Footer } from "@/components/landing/Footer";

// ==============================================================
// 1. HELPER COMPONENTS & FUNCTIONS
// ==============================================================
const formatUrl = (url: string) => {
  if (!url) return "";
  return url.startsWith("http") ? url : `https://squarecloudsmc.com${url}`;
};

const toRoman = (num: number) => {
  const roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
  return roman[num - 1] || num.toString();
};

const RevealText = memo(function RevealText({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
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
});

// ==============================================================
// 2. LAYOUT 2022: ALTERNATING KIRI - KANAN
// ==============================================================
const ChapterLeftRight = memo(function ChapterLeftRight({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) {
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
          2022
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
                className="w-full md:w-1/2 aspect-[4/5] bg-slate-100 rounded-sm overflow-hidden shadow-xl"
              >
                <img
                  src={formatUrl(c.thumbnail_url)}
                  alt={c.title || "Project Image"}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover hover:scale-105 transition-transform duration-[1.5s]"
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1, delay: 0.2 }}
                className="w-full md:w-1/2 flex flex-col"
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
});

// ==============================================================
// 3. LAYOUT 2023: HORIZONTAL MAGAZINE PARALLAX
// ==============================================================
const ChapterMagazine = memo(function ChapterMagazine({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  const xTransform = useTransform(
    scrollYProgress,
    [0, 1],
    ["calc(0% + 0vw)", "calc(-100% + 100vw)"]
  );
  const textXTransform = useTransform(
    scrollYProgress,
    [0, 1],
    ["calc(0% + 0vw)", "calc(-30% + 0vw)"]
  );

  const dataWithGallery = useMemo(
    () =>
      data.map((c) => ({
        ...c,
        _galleryImgs: c.gallery_urls ? c.gallery_urls.split(",").filter(Boolean) : [],
      })),
    [data]
  );

  return (
    <div
      ref={containerRef}
      style={{ contentVisibility: "auto", containIntrinsicSize: "0 400vh" }}
      className="relative h-[300vh] md:h-[400vh] w-full bg-slate-50 border-y border-gray-100"
    >
      <div className="sticky top-0 h-screen w-full flex flex-col justify-center overflow-hidden">
        <motion.div
          style={{ x: textXTransform, willChange: "transform", transform: "translateZ(0)" }}
          className="absolute top-1/2 -translate-y-1/2 whitespace-nowrap -z-10 pl-12"
        >
          <h1 className="text-[25vw] md:text-[18vw] font-black text-slate-200/60 tracking-tighter uppercase leading-none mix-blend-multiply">
            FEATURED ARCHIVES
          </h1>
        </motion.div>

        <div className="absolute top-20 left-6 md:left-12 z-20 mix-blend-difference text-white pointer-events-none">
          <p className="text-xs font-bold uppercase tracking-widest mb-1">
            // {chapterStr} //
          </p>
          <h2 className="text-2xl md:text-4xl font-black tracking-tight uppercase">
            2023
          </h2>
        </div>

        <motion.div
          style={{ x: xTransform, willChange: "transform", transform: "translateZ(0)" }}
          className="flex gap-16 md:gap-32 px-12 md:px-[20vw] items-center w-max h-full"
        >
          {dataWithGallery.map((c, idx) => {
            const galleryImgs = c._galleryImgs;
            const tiltAngle = idx % 2 === 0 ? "rotate-[-3deg]" : "rotate-[3deg]";
            const verticalOffset = idx % 2 === 0 ? "mb-20 md:mb-40" : "mt-20 md:mt-40";
            return (
              <div
                key={c.id}
                className={`relative flex items-center justify-center w-[80vw] md:w-[45vw] ${verticalOffset}`}
              >
                <div
                  className={`relative w-full aspect-[3/4] rounded-sm overflow-hidden shadow-[0_30px_60px_rgba(0,0,0,0.15)] bg-white ${tiltAngle} transition-transform duration-700 hover:scale-[1.02]`}
                >
                  <img
                    src={formatUrl(c.thumbnail_url)}
                    alt={c.title || "Cover"}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-full object-cover"
                  />
                  {galleryImgs[0] && (
                    <div className="absolute -bottom-6 -right-6 md:-bottom-12 md:-right-12 w-[55%] aspect-[3/4] shadow-2xl border-[8px] border-white bg-slate-100">
                      <img
                        src={formatUrl(galleryImgs[0])}
                        loading="lazy"
                        decoding="async"
                        className="w-full h-full object-cover"
                        alt=""
                      />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent flex flex-col justify-end p-8 md:p-12 pointer-events-none">
                    <p className="text-blue-400 font-bold text-xs uppercase tracking-widest mb-2 border border-blue-400/30 px-3 py-1 w-max rounded-full backdrop-blur-sm">
                      EDITION • {c.year}
                    </p>
                    {c.title && (
                      <h3 className="text-4xl md:text-6xl font-black text-white tracking-tighter uppercase drop-shadow-xl">
                        {c.title}
                      </h3>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
});

// ==============================================================
// 4. LAYOUT 2024: FULL-WIDTH EDITORIAL CASCADE
// ==============================================================
const ChapterArtsyCascade = memo(function ChapterArtsyCascade({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) {
  const galleryFeed = useMemo(() => {
    const feed: { url: string; title: string | null; year: string; isMain: boolean }[] = [];
    data.forEach((c) => {
      feed.push({
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
            feed.push({ url: formatUrl(gUrl), title: c.title, year: c.year, isMain: false });
          });
      }
    });
    return feed;
  }, [data]);

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
        <RevealText delay={0.2} className="text-slate-500 text-lg leading-relaxed font-medium">
          Moments frozen in time. An exploration of architecture, space, and meticulous details
          scattered across the digital canvas.
        </RevealText>
      </div>

      <div className="flex flex-col gap-20 md:gap-40 w-full pb-20">
        {galleryFeed.map((img, idx) => {
          let sizingClass = "";
          if (idx % 4 === 0) {
            sizingClass = "w-full md:w-[55%] mr-auto";
          } else if (idx % 4 === 1) {
            sizingClass = "w-[85%] md:w-[45%] ml-auto";
          } else if (idx % 4 === 2) {
            sizingClass = "w-full md:w-[70%] mx-auto";
          } else {
            sizingClass = "w-[80%] md:w-[35%] ml-[10%]";
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
                  loading="lazy"
                  decoding="async"
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
});

// ==============================================================
// 5. LAYOUT 2025: LIGHT MOVIE TAPE + TYPOGRAPHY SECTION
// ==============================================================
const ChapterCinematicLight = memo(function ChapterCinematicLight({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });
  const xTransform = useTransform(
    scrollYProgress,
    [0, 1],
    ["calc(0% + 0vw)", "calc(-100% + 100vw)"]
  );

  return (
    <>
      <div
        ref={containerRef}
        style={{ contentVisibility: "auto", containIntrinsicSize: "0 400vh" }}
        className="relative h-[300vh] md:h-[400vh] w-full bg-white text-slate-900 border-y border-gray-100"
      >
        <div className="sticky top-0 h-screen w-full flex flex-col justify-center overflow-hidden">
          <div className="absolute top-20 left-6 md:left-12 z-20 mix-blend-difference text-white pointer-events-none">
            <p className="text-xs font-bold uppercase tracking-widest mb-1">
              // {chapterStr} //
            </p>
            <h2 className="text-2xl md:text-4xl font-black tracking-tight uppercase">
              2025
            </h2>
          </div>

          <motion.div
            style={{ x: xTransform, willChange: "transform", transform: "translateZ(0)" }}
            className="flex h-screen w-max items-center"
          >
            {data.map((c, idx) => (
              <div
                key={c.id}
                className="h-screen w-[100vw] md:w-[85vw] flex-shrink-0 flex items-center justify-center border-r-[5px] md:border-r-[20px] border-white relative group"
              >
                <img
                  src={formatUrl(c.thumbnail_url)}
                  alt={c.title || "Cinematic"}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover grayscale-[20%] opacity-90 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-[1.5s] ease-[cubic-bezier(0.25,1,0.5,1)]"
                />

                <div className="absolute inset-0 bg-gradient-to-t from-white/95 via-white/40 to-transparent flex flex-col justify-end p-10 md:p-20 opacity-0 group-hover:opacity-100 transition-opacity duration-1000 pointer-events-none">
                  <div className="max-w-4xl">
                    <span className="inline-block text-blue-600 text-sm font-bold tracking-widest uppercase mb-4 border border-blue-600/30 bg-white/50 px-4 py-1 rounded-full backdrop-blur-md">
                      SCENE 0{idx + 1}
                    </span>
                    {c.title && (
                      <h3 className="text-5xl md:text-8xl font-black uppercase tracking-tight text-slate-900 mb-4 drop-shadow-sm">
                        {c.title}
                      </h3>
                    )}
                    {c.description && (
                      <p className="text-slate-600 text-lg md:text-xl font-medium leading-relaxed max-w-3xl drop-shadow-sm">
                        {c.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      <section className="w-full py-40 px-6 md:px-12 max-w-[1600px] mx-auto text-center flex flex-col items-center justify-center overflow-hidden">
        <RevealText className="text-[8vw] md:text-[6vw] font-black tracking-tighter uppercase text-slate-900 leading-none">
          BEYOND BLOCKS
        </RevealText>
        <RevealText
          delay={0.1}
          className="text-[8vw] md:text-[6vw] font-black tracking-tighter uppercase text-slate-300 leading-none my-4"
        >
          ARCHITECTING PLAY
        </RevealText>
      </section>
    </>
  );
});

// ==============================================================
// 6. LAYOUT 2026: VERTICAL PARALLAX MASKING
// ==============================================================
const ParallaxVerticalCard = memo(function ParallaxVerticalCard({
  c,
  idx,
}: {
  c: any;
  idx: number;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: cardRef, offset: ["start end", "end start"] });
  const yTransform = useTransform(scrollYProgress, [0, 1], ["-15%", "15%"]);

  return (
    <div
      className="flex flex-col items-center mb-40 last:mb-0"
      style={{ contentVisibility: "auto", containIntrinsicSize: "0 90vh" }}
    >
      <div className="text-center mb-8">
        <span className="text-xs font-bold text-blue-600 uppercase tracking-widest border border-blue-100 bg-blue-50 px-3 py-1 rounded-full">
          NO. 0{idx + 1}
        </span>
        {c.title && (
          <h3 className="text-4xl md:text-6xl font-black text-slate-900 tracking-tight mt-4 uppercase">
            {c.title}
          </h3>
        )}
      </div>

      <div
        ref={cardRef}
        className="w-full max-w-[1200px] h-[70vh] md:h-[90vh] overflow-hidden rounded-sm shadow-2xl relative"
      >
        <motion.img
          style={{
            y: yTransform,
            scale: 1.15,
            willChange: "transform",
            transform: "translateZ(0)",
          }}
          src={formatUrl(c.thumbnail_url)}
          loading="lazy"
          decoding="async"
          className="w-full h-full object-cover"
          alt={c.title || "Vertical Parallax"}
        />
        {c.description && (
          <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-10 flex justify-center text-center">
            <p className="text-white text-lg font-medium max-w-2xl">{c.description}</p>
          </div>
        )}
      </div>
    </div>
  );
});

const ChapterVerticalParallax = memo(function ChapterVerticalParallax({
  data,
  year,
  chapterStr,
}: {
  data: any[];
  year: string;
  chapterStr: string;
}) {
  return (
    <section className="w-full py-32 px-6 md:px-12 max-w-[1600px] mx-auto bg-white overflow-hidden">
      <div className="mb-32 text-center">
        <RevealText className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-4">
          // {chapterStr} //
        </RevealText>
        <RevealText
          delay={0.1}
          className="text-4xl md:text-7xl font-black tracking-tighter text-slate-900 uppercase"
        >
          2026
        </RevealText>
      </div>

      <div className="flex flex-col w-full">
        {data.map((c, idx) => (
          <ParallaxVerticalCard key={c.id} c={c} idx={idx} />
        ))}
      </div>
    </section>
  );
});

// ==============================================================
// MAIN PAGE COMPONENT
// ==============================================================
export default function CommissionPage() {
  const [commissions, setCommissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    const fetchData = async () => {
      try {
        const res = await fetch("https://squarecloudsmc.com/cms/commissions", {
          signal: controller.signal,
        });
        const data = await res.json();
        const mappedData = (data.data || []).map((item: any) => ({
          ...item,
          year: item.year || "2024",
        }));
        setCommissions(mappedData);
      } catch (error: any) {
        if (error?.name !== "AbortError") {
          console.error("Gagal menarik data komisi:", error);
        }
      } finally {
        setLoading(false);
        setTimeout(() => setIsTransitioning(false), 800);
      }
    };
    fetchData();

    return () => controller.abort();
  }, []);

  // CATATAN: useEffect penghilang navbar sudah DIHAPUS agar Navbar utama tetap tampil.

  const sortedCommissions = useMemo(
    () => [...commissions].sort((a, b) => (parseInt(a.year) || 0) - (parseInt(b.year) || 0)),
    [commissions]
  );

  const uniqueYears = useMemo(
    () => Array.from(new Set(sortedCommissions.map((c) => c.year || "2024"))),
    [sortedCommissions]
  );

  const oldestYear = uniqueYears[0] || "2022";
  const newestYear = uniqueYears[uniqueYears.length - 1] || "2026";

  const heroProject = sortedCommissions[sortedCommissions.length - 1];

  // Precompute chapter data sekali agar referensi array stabil -> React.memo efektif
  const chapters = useMemo(
    () =>
      uniqueYears.map((year, index) => {
        const chapterData = sortedCommissions.filter((c) => c.year === year);
        const chapterStr = `CHAPTER ${toRoman(index + 1)}`;
        return { year, index, chapterData, chapterStr };
      }),
    [uniqueYears, sortedCommissions]
  );

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
        {/* HERO OPENING - Padding top disesuaikan (pt-32 md:pt-40) agar aman di bawah header navbar */}
        <section className="w-full pt-32 md:pt-40 pb-32 px-6 md:px-12 max-w-[1600px] mx-auto overflow-hidden">
          <RevealText
            delay={0.1}
            className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6"
          >
            Our Works Archive / {oldestYear}—{newestYear}
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
                loading="eager"
                fetchPriority="high"
                decoding="async"
                className="w-full h-full object-cover grayscale opacity-80 hover:grayscale-0 hover:opacity-100 transition-all duration-[1.5s] ease-[cubic-bezier(0.25,1,0.5,1)]"
              />
            </motion.div>
          )}
        </section>

        {/* DYNAMIC CHAPTER LOOP */}
        {chapters.map(({ year, index, chapterData, chapterStr }) => {
          if (chapterData.length === 0) return null;

          let renderedChapter = null;
          let spacerClass = "bg-white";

          if (year === "2022" || index === 0) {
            renderedChapter = (
              <ChapterLeftRight data={chapterData} year={year} chapterStr={chapterStr} />
            );
            spacerClass = "bg-gradient-to-b from-white to-slate-50";
          } else if (year === "2023" || index === 1) {
            renderedChapter = (
              <ChapterMagazine data={chapterData} year={year} chapterStr={chapterStr} />
            );
            spacerClass = "bg-gradient-to-b from-slate-50 to-white";
          } else if (year === "2024" || index === 2) {
            renderedChapter = (
              <ChapterArtsyCascade data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else if (year === "2025" || index === 3) {
            renderedChapter = (
              <ChapterCinematicLight data={chapterData} year={year} chapterStr={chapterStr} />
            );
          } else if (year >= "2026" || index >= 4) {
            renderedChapter = (
              <ChapterVerticalParallax data={chapterData} year={year} chapterStr={chapterStr} />
            );
          }

          return (
            <div key={year} className="w-full flex flex-col">
              {index > 0 && index % 2 === 1 && (
                <section className="w-full py-24 md:py-32 px-6 md:px-12 max-w-[1600px] mx-auto text-center flex flex-col items-center justify-center overflow-hidden">
                  <RevealText className="text-[8vw] md:text-[6vw] font-black tracking-tighter uppercase text-slate-900 leading-none">
                    SPATIAL POETRY
                  </RevealText>
                  <RevealText
                    delay={0.1}
                    className="text-[8vw] md:text-[6vw] font-black tracking-tighter uppercase text-slate-300 leading-none my-4"
                  >
                    IN DIGITAL REALMS
                  </RevealText>
                </section>
              )}

              {index > 0 && <div className={`w-full h-[25vh] md:h-[40vh] ${spacerClass}`} />}
              {renderedChapter}
            </div>
          );
        })}

        {/* CLOSING: EDITORIAL METRICS & CTA */}
        <section className="w-full pt-32 pb-40 px-6 md:px-12 max-w-[1600px] mx-auto overflow-hidden">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-12 md:gap-8 mb-40 border-t border-b border-gray-200 py-20">
            <div>
              <p className="text-5xl md:text-7xl font-black text-slate-900 mb-4">03</p>
              <p className="text-sm font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                Years
                <br />
                shaping
                <br />
                excellence
              </p>
            </div>
            <div>
              <p className="text-5xl md:text-7xl font-black text-slate-900 mb-4">
                {commissions.length}+
              </p>
              <p className="text-sm font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                Projects
                <br />
                brought
                <br />
                to life
              </p>
            </div>
            <div>
              <p className="text-5xl md:text-7xl font-black text-slate-900 mb-4">∞</p>
              <p className="text-sm font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                Blocks
                <br />
                placed
                <br />
                with intent
              </p>
            </div>
            <div>
              <p className="text-5xl md:text-7xl font-black text-slate-900 mb-4">1M+</p>
              <p className="text-sm font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                Players
                <br />
                reached
                <br />
                globally
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center text-center">
            <RevealText className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-12">
              Contact is the first gesture of trust
            </RevealText>
            <a href="mailto:squarecloudsmc@gmail.com" className="group block pointer-events-auto">
              <RevealText className="text-[12vw] md:text-[9vw] font-black tracking-tighter uppercase text-slate-900 leading-none group-hover:text-blue-600 transition-colors duration-500">
                GET IN TOUCH
              </RevealText>
            </a>
          </div>
        </section>

        {/* FOOTER dengan jarak margin bawah yang rapi (mt-32 md:mt-40) */}
        <div className="w-full mt-32 md:mt-40 border-t border-gray-100 pt-12">
          <Footer />
        </div>
      </main>
    </div>
  );
}