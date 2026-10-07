"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { ArrowRight, Globe, Quote } from "lucide-react";
import { FaLinkedin, FaTwitter, FaInstagram } from "react-icons/fa";
import { Footer } from "@/components/landing/Footer";

// HELPER: Fungsi untuk memastikan URL selalu jadi absolute link (punya https://)
const formatUrl = (url: string) => {
  if (!url) return "#";
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `https://${url}`;
};

export default function TeamPage() {
  const [team, setTeam] = useState<any[]>([]);

  // STATE UNTUK TRANSISI
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);

  // 1. Tarik Data Backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("https://squarecloudsmc.com/cms/team");
        const data = await res.json();
        if (data.data) setTeam(data.data);
      } catch (error) {
        console.error("Gagal menarik data tim:", error);
      } finally {
        setLoading(false);
        setTimeout(() => {
          setIsTransitioning(false);
        }, 1000);
      }
    };
    fetchData();
  }, []);

  // CATATAN: Kode useEffect yang menyembunyikan navbar sudah DIHAPUS 
  // agar Navbar utama tetap tampil di halaman Team.

  return (
    <div className="min-h-screen bg-white selection:bg-blue-200 flex flex-col">
      {/* =========================================
          TRANSISI TIRAI / PAGE TRANSITION OVERLAY
          ========================================= */}
      <AnimatePresence>
        {(loading || isTransitioning) && (
          <motion.div
            key="curtain"
            initial={{ y: 0 }}
            exit={{ y: "-100%" }}
            transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-0 z-[99999] bg-[#1a65d6] flex flex-col items-center justify-center"
          >
            <div className="overflow-hidden">
              <motion.div
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="flex items-center gap-4 px-4"
              >
                <img
                  src="/logo.png"
                  alt="Squareclouds"
                  className="h-12 md:h-14 w-auto object-contain drop-shadow-md rounded-xl"
                />
                <h1 className="text-3xl md:text-5xl font-black text-white tracking-tight">
                  {loading ? "Connecting to HQ..." : "Hello there, Cloudians!"}
                </h1>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {/* ========================================= */}

      {/* Padding Top disesuaikan (pt-28 md:pt-36) agar konten tidak tertutup header navbar putih di atas */}
      <main className="relative z-10 w-full flex-grow flex flex-col items-center pt-28 md:pt-36">
        {/* 1. BRAND HEADER */}
        <section className="w-full max-w-[1000px] mx-auto px-6 pb-16 flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            className="mb-8"
          >
            <img
              src="/logo.png"
              alt="Squareclouds"
              className="h-20 md:h-24 w-auto object-contain drop-shadow-sm rounded-2xl md:rounded-3xl"
            />
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-black text-slate-900 tracking-tight mb-4"
          >
            Meet the Team
          </motion.h1>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="flex flex-wrap items-center justify-center gap-3 text-slate-500 font-medium text-sm md:text-base uppercase tracking-wider"
          >
            <span>Medan, Indonesia</span>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
            <span>Digital, Video Games</span>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
            <a href="https://squareclouds.com" className="text-blue-600 hover:underline">
              View Website
            </a>
          </motion.div>
        </section>

        {/* 2. STATS BAR & QUOTE */}
        <section className="w-full max-w-[1000px] mx-auto px-6 mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-slate-50 rounded-[32px] p-8 md:p-12 flex flex-col md:flex-row gap-12 items-center justify-between border border-slate-100"
          >
            <div className="flex-1 flex gap-8 md:gap-16 justify-center md:justify-start flex-wrap">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Year of Founding
                </p>
                <p className="text-3xl font-black text-slate-900">2022</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Employees
                </p>
                <p className="text-3xl font-black text-slate-900">{team.length}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Average Age
                </p>
                <p className="text-3xl font-black text-slate-900">24 yrs</p>
              </div>
            </div>

            <div className="flex-1 md:border-l border-slate-200 md:pl-12 flex items-start gap-4">
              <Quote size={40} className="text-blue-200 rotate-180 shrink-0" />
              <p className="text-xl md:text-2xl font-black text-slate-900 leading-tight italic">
                "Imagination through the clouds."
              </p>
            </div>
          </motion.div>
        </section>

        {/* 3. STORY / PRESENTATION SECTION */}
        <section className="w-full max-w-[1000px] mx-auto px-6 pb-24 border-b border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h3 className="text-2xl font-black text-slate-900 mb-6">Presentation</h3>
              <div className="space-y-4 text-slate-500 leading-relaxed text-[17px]">
                <p>
                  Founded in July 2022, Squareclouds is a creative collective and game development
                  studio based in Medan, Indonesia, pioneering UGC (User Generated Content) gaming
                  experiences.
                </p>
                <p>
                  We blend engineering with artistry to build innovative games played by global
                  communities. By supporting the next generation of content creators through our
                  internal teams and partnerships, we aim to set new standards in digital
                  entertainment.
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h3 className="text-2xl font-black text-slate-900 mb-6">Good to know</h3>
              <div className="space-y-4 text-slate-500 leading-relaxed text-[17px]">
                <p>
                  At Squareclouds, innovation is at the heart of everything we do. Though we come
                  from different backgrounds, we're united by a shared passion for the world of
                  voxel and video games.
                </p>
                <p>
                  Passionate and attentive, we design environments and assets that resonate with the
                  desires of our community. After all, it's by laying each block that we build
                  mountains.
                </p>
              </div>
            </motion.div>
          </div>
        </section>

        {/* 4. DYNAMIC TEAM GRID (Cloudians) */}
        <section className="w-full py-24 px-6 bg-white">
          <div className="max-w-[1200px] mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16">
              <div>
                <h2 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight">
                  The Crew
                </h2>
              </div>
              <a
                href="mailto:squarecloudsmc@gmail.com"
                className="group flex items-center gap-2 text-blue-600 font-bold hover:text-blue-700 transition-colors"
              >
                Join the team{" "}
                <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
              </a>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16">
              {team.map((member, idx) => {
                const imgUrl = member.image_url?.startsWith("http")
                  ? member.image_url
                  : `https://squarecloudsmc.com${member.image_url}`;

                return (
                  <motion.div
                    key={member.id || idx}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-50px" }}
                    transition={{ duration: 0.5, delay: (idx % 3) * 0.1 }}
                    className="group flex flex-col cursor-pointer"
                  >
                    <div className="relative w-full aspect-[4/5] rounded-[32px] overflow-hidden bg-slate-100 mb-6 shadow-sm border border-slate-100">
                      <img
                        src={imgUrl}
                        alt={member.name}
                        className="absolute inset-0 w-full h-full object-cover grayscale opacity-80 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-700 group-hover:scale-105"
                      />

                      <div className="absolute top-4 right-4 flex flex-col gap-2 opacity-0 translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-500">
                        {member.link_x && (
                          <a
                            href={formatUrl(member.link_x)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-slate-900 flex items-center justify-center hover:bg-[#1DA1F2] hover:text-white shadow-lg transition-colors"
                          >
                            <FaTwitter size={16} />
                          </a>
                        )}
                        {member.link_instagram && (
                          <a
                            href={formatUrl(member.link_instagram)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-slate-900 flex items-center justify-center hover:bg-[#E1306C] hover:text-white shadow-lg transition-colors"
                          >
                            <FaInstagram size={16} />
                          </a>
                        )}
                        {member.link_linkedin && (
                          <a
                            href={formatUrl(member.link_linkedin)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-slate-900 flex items-center justify-center hover:bg-[#0A66C2] hover:text-white shadow-lg transition-colors"
                          >
                            <FaLinkedin size={16} />
                          </a>
                        )}
                        {member.link_website && (
                          <a
                            href={formatUrl(member.link_website)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm text-slate-900 flex items-center justify-center hover:bg-slate-900 hover:text-white shadow-lg transition-colors"
                          >
                            <Globe size={16} />
                          </a>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col px-2">
                      <h3 className="text-2xl font-bold text-slate-900 mb-1 group-hover:text-blue-600 transition-colors">
                        {member.name}
                      </h3>
                      <p className="text-blue-600 font-bold text-sm tracking-wide uppercase mb-3">
                        {member.role}
                      </p>
                      <p className="text-slate-500 font-medium text-[15px] leading-relaxed line-clamp-3">
                        {member.bio}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 5. CTA / HIRING */}
        <section className="w-full py-24 px-6 bg-slate-50 border-t border-slate-100 text-center">
          <div className="max-w-[800px] mx-auto flex flex-col items-center">
            <h2 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight mb-6">
              What we are looking for
            </h2>
            <p className="text-slate-500 text-lg md:text-xl leading-relaxed mb-10 max-w-2xl">
              We're constantly evolving with a strong drive for growth. We’re looking for
              passionate, autonomous, and rigorous individuals. If you’re eager to hone your skills
              and create games that reflect your creativity, we want to hear from you.
            </p>
            <a
              href="mailto:squarecloudsmc@gmail.com"
              className="px-10 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-full transition-all shadow-[0_8px_20px_rgba(37,99,235,0.2)] hover:-translate-y-1"
            >
              Apply Now
            </a>
          </div>
        </section>

        {/* FOOTER dengan Jarak Margin Bawah (mt-32 md:mt-40) */}
        <div className="w-full mt-32 md:mt-40">
          <Footer />
        </div>
      </main>
    </div>
  );
}