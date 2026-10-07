"use client";

import { motion, useScroll, useTransform } from "framer-motion";

export function HeroSection() {
  const { scrollY } = useScroll();
  const yParallax = useTransform(scrollY, [0, 1000], [0, 600]);
  const mobileCloudLeftX = useTransform(scrollY, [0, 700], ["0vw", "-100vw"]);
  const mobileCloudRightX = useTransform(scrollY, [0, 700], ["0vw", "100vw"]);
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

  const SingleCloudLayer = (
    <motion.div
      className="absolute inset-x-0 bottom-0 aspect-[2496/1726] w-full md:hidden"
      initial={{ y: 400, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 1.5, ease: "easeOut", delay: 0.8 }}
      style={{
        maskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 70%, transparent 100%)",
        WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 70%, transparent 100%)",
      }}
    >
      {[
        {
          x: mobileCloudLeftX,
          mask: "linear-gradient(to right, black 20%, transparent 70%)",
        },
        {
          x: mobileCloudRightX,
          mask: "linear-gradient(to left, black 20%, transparent 70%)",
        },
      ].map(({ x, mask }, index) => (
        <motion.div
          key={index}
          animate={{ scale: [1.02, 1.05, 1.02] }}
          transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          style={{
            x,
            backgroundImage: "url('/Transparent%20sky.png')",
            maskImage: mask,
            WebkitMaskImage: mask,
            willChange: "transform",
          }}
          className="absolute inset-0 bg-[length:100%_100%] bg-center bg-no-repeat"
        />
      ))}
    </motion.div>
  );

  const CloudsList = (
    <motion.div
      className="flex flex-col w-full h-[300vh] will-change-transform"
      initial={{ y: 400, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 1.5, ease: "easeOut", delay: 0.8 }}
    >
      {[...Array(3)].map((_, i) => (
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
      className="relative min-h-[90svh] md:min-h-[100svh] flex flex-col items-center pt-[150px] sm:pt-[190px] lg:pt-[28vh] overflow-hidden bg-[#1a65d6]"
    >
      {/* BACKGROUND SKY/CLOUD */}
      <div className="absolute inset-0 z-10 pointer-events-none w-full md:inset-x-0 md:bottom-auto md:top-[26vh] md:min-h-[100svh]">
        {SingleCloudLayer}
        <motion.div
          style={{ x: xLeft, y: yParallax, willChange: "transform" }}
          className="absolute inset-0 hidden w-full md:block"
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
          className="absolute inset-0 hidden w-full md:block"
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

      {/* HORIZON: BLUE SKY FADES INTO THE WHITE PAGE */}
      <div className="absolute bottom-0 left-0 right-0 z-20 h-64 bg-gradient-to-t from-white via-white/80 to-transparent pointer-events-none sm:h-72 md:h-64" />

      {/* HERO CONTENT */}
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 relative z-30 w-full flex flex-col items-center text-center pointer-events-none">
        <div className="w-full max-w-[850px] flex flex-col items-center pointer-events-none">
          {/* HEADING: Muncul di 0.2s */}
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            className="w-full max-w-[819px] font-black text-[clamp(36px,7vw,79px)] text-white leading-[1.05] tracking-tight mb-5 sm:mb-6 [text-shadow:3px_3px_0px_rgba(0,0,0,0.2)] mx-auto break-words"
          >
            {title}
          </motion.h1>
          
          {/* DESKRIPSI: Muncul di 0.4s */}
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
            className="text-base sm:text-lg md:text-xl text-white font-bold leading-relaxed text-center max-w-2xl [text-shadow:2px_2px_0px_rgba(0,0,0,0.2)] mb-7 px-2"
          >
            {subtitle}
          </motion.p>
        </div>

        {/* AREA TOMBOL: Muncul di 0.6s */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          className="flex w-full flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-6 md:mb-10 pointer-events-auto"
        >
          {/* TOMBOL 1: Email Redirect */}
          <a
            href="mailto:squarecloudsmc@gmail.com"
            className="flex items-center justify-center gap-3 py-3 px-7 w-full max-w-[250px] font-black text-[16px] text-white rounded-full bg-white/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_12px_28px_rgba(3,25,70,0.16)] hover:bg-white/30 hover:-translate-y-1 backdrop-blur-xl transition-all active:translate-y-0"
          >
            Build with us
          </a>

          {/* TOMBOL 2: Smooth Scroll */}
          <a
            href="#product"
            onClick={scrollToProduct}
            className="flex items-center justify-center py-3 px-5 w-full max-w-[320px] font-black text-[16px] text-white rounded-full bg-white/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_12px_28px_rgba(3,25,70,0.16)] hover:bg-white/30 hover:-translate-y-1 backdrop-blur-xl transition-all active:translate-y-0 cursor-pointer"
          >
            Explore Our Ecosystem
          </a>
        </motion.div>
      </div>
    </section>
  );
}