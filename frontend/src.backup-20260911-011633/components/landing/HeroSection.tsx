"use client";

import { motion, useScroll, useTransform } from "framer-motion";

export function HeroSection() {
  const { scrollY } = useScroll();
  const yParallax = useTransform(scrollY, [0, 1000], [0, 600]);
  const xLeft = useTransform(scrollY, [0, 1000], ["0vw", "-120vw"]);
  const xRight = useTransform(scrollY, [0, 1000], ["0vw", "120vw"]);

  const title = "Imagination Through the Clouds";
  const subtitle =
    "The most fun and innovative way to make things different, and we can change the unthinkable through games.";

  // FUNGSI SMOOTH SCROLL KE PRODUCT
  const scrollToProduct = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById("product");
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const CloudsList = (
    <motion.div
      className="flex flex-col w-full h-[300vh] will-change-transform"
      initial={{ y: 400, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      // Delay 0.8 detik agar awan muncul setelah tombol
      transition={{ duration: 1.5, ease: "easeOut", delay: 0.8 }}
    >
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          animate={{
            x: i % 2 === 0 ? ["-1%", "1%", "-1%"] : ["1%", "-1%", "1%"],
            scale: [1.02, 1.05, 1.02],
          }}
          transition={{ duration: 18 + i * 2, repeat: Infinity, ease: "easeInOut" }}
          style={{
            backgroundImage: "url('/Transparent%20sky.png')",
            willChange: "transform",
            maskImage:
              i === 0
                ? "linear-gradient(to bottom, transparent 0%, black 15%, black 90%, transparent 100%)"
                : "linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)",
            WebkitMaskImage:
              i === 0
                ? "linear-gradient(to bottom, transparent 0%, black 15%, black 90%, transparent 100%)"
                : "linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)",
          }}
          className={`w-[104%] -ml-[2%] flex-none aspect-[1/1] md:aspect-[16/9] bg-[length:100%_100%] bg-center bg-no-repeat ${
            i > 0 ? "-mt-[10%]" : ""
          } ${i % 2 !== 0 ? "-scale-y-100" : ""}`}
        ></motion.div>
      ))}
    </motion.div>
  );

  return (
    <section
      id="home"
      className="relative min-h-[100vh] flex flex-col items-center pt-[230px] lg:pt-[28vh] overflow-hidden bg-[#1a65d6]"
    >
      {/* BACKGROUND SKY/CLOUD */}
      <div className="absolute left-0 right-0 top-[18vh] md:top-[26vh] z-10 pointer-events-none w-full min-h-[100vh]">
        <motion.div
          style={{ x: xLeft, y: yParallax, willChange: "transform" }}
          className="absolute inset-0 w-full"
        >
          <div
            className="w-full h-full"
            style={{
              maskImage: "linear-gradient(to right, black 25%, transparent 60%)",
              WebkitMaskImage: "linear-gradient(to right, black 25%, transparent 60%)",
            }}
          >
            {CloudsList}
          </div>
        </motion.div>
        <motion.div
          style={{ x: xRight, y: yParallax, willChange: "transform" }}
          className="absolute inset-0 w-full"
        >
          <div
            className="w-full h-full"
            style={{
              maskImage: "linear-gradient(to left, black 25%, transparent 60%)",
              WebkitMaskImage: "linear-gradient(to left, black 25%, transparent 60%)",
            }}
          >
            {CloudsList}
          </div>
        </motion.div>
      </div>

      {/* GRADIENT SMOOTH TRANSITION KE BAWAH */}
      <div className="absolute bottom-0 left-0 right-0 h-64 bg-gradient-to-t from-white via-white/40 to-transparent z-20 pointer-events-none"></div>

      {/* HERO CONTENT */}
      <div className="max-w-[1100px] mx-auto px-6 relative z-30 w-full flex flex-col items-center text-center pointer-events-none">
        <div className="max-w-[850px] flex flex-col items-center pointer-events-none">
          {/* HEADING: Muncul di 0.2s */}
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            className="w-[819px] max-w-full font-black text-[clamp(40px,7vw,79px)] text-white leading-[1.08] tracking-tight mb-6 [text-shadow:4px_4px_0px_rgba(0,0,0,0.2)] mx-auto"
          >
            {title}
          </motion.h1>
          
          {/* DESKRIPSI: Muncul di 0.4s */}
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
            className="text-lg md:text-xl text-white font-bold leading-relaxed text-center max-w-2xl [text-shadow:2px_2px_0px_rgba(0,0,0,0.2)] mb-8"
          >
            {subtitle}
          </motion.p>
        </div>

        {/* AREA TOMBOL: Muncul di 0.6s */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          className="flex flex-wrap justify-center gap-4 mb-6 md:mb-10 pointer-events-auto"
        >
          {/* TOMBOL 1: Email Redirect */}
          <a
            href="mailto:squarecloudsmc@gmail.com"
            className="flex items-center gap-3 py-3 px-7 font-black text-[16px] text-white rounded-full bg-black/30 border border-white/40 shadow-[4px_4px_0px_rgba(0,0,0,0.2)] hover:-translate-y-1 backdrop-blur-md transition-all active:translate-y-0"
          >
            Build with us
          </a>

          {/* TOMBOL 2: Smooth Scroll */}
          <a
            href="#product"
            onClick={scrollToProduct}
            className="flex items-center gap-3 py-3 px-7 font-black text-[16px] text-white rounded-full bg-black/20 border border-white/40 shadow-[4px_4px_0px_rgba(0,0,0,0.2)] hover:-translate-y-1 backdrop-blur-md transition-all active:translate-y-0 cursor-pointer"
          >
            Explore Our Ecosystem
            <div className="w-[28px] h-[28px] bg-white rounded-full flex items-center justify-center text-[#1A5BAF] text-[14px]">
              →
            </div>
          </a>
        </motion.div>
      </div>
    </section>
  );
}