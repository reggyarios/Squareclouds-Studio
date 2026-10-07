"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { ArrowRight, Globe } from "lucide-react";
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
  const [selectedMember, setSelectedMember] = useState<any | null>(null);
  const roleOrder = ["CEO", "CTO", "CFO", "CCO"];
  const teamCards = [
    ...[...team].sort((a, b) => {
      const firstRole = roleOrder.indexOf(String(a.role || "").toUpperCase());
      const secondRole = roleOrder.indexOf(String(b.role || "").toUpperCase());
      return (firstRole === -1 ? roleOrder.length : firstRole) - (secondRole === -1 ? roleOrder.length : secondRole);
    }),
    {
      id: "other-cloudians",
      name: "27+ Other Cloudians",
      role: "Builders",
      bio: "More builders bringing ideas, detail, and imagination to the Squareclouds community.",
      image_url: "https://mc-heads.net/body/Steve/100.png",
    },
  ];

  // STATE UNTUK TRANSISI
  const [loading, setLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(true);

  useEffect(() => {
    if (!selectedMember) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedMember(null);
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [selectedMember]);

  // 1. Tarik Data Backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("https://api.squarecloudsmc.com/cms/team");
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
              {teamCards.map((member, idx) => {
                const imgUrl = member.image_url?.startsWith("http")
                  ? member.image_url
                  : `https://api.squarecloudsmc.com${member.image_url}`;

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

                      <button
                        type="button"
                        aria-label={`View ${member.name}'s profile`}
                        onClick={() => setSelectedMember(member)}
                        className="absolute inset-0 z-10 md:hidden"
                      />

                      <div className="absolute top-4 right-4 hidden md:flex flex-col gap-2 opacity-0 translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-500">
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
                      <p className="hidden md:line-clamp-3 text-slate-500 font-medium text-[15px] leading-relaxed">
                        {member.bio}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </section>

        <AnimatePresence>
          {selectedMember && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-5 md:hidden">
              <motion.button
                type="button"
                aria-label="Close team profile"
                onClick={() => setSelectedMember(null)}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
              />
              <motion.div
                role="dialog"
                aria-modal="true"
                aria-label={`${selectedMember.name} profile`}
                initial={{ opacity: 0, y: 20, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.98 }}
                transition={{ duration: 0.22, ease: "easeOut" }}
                className="relative z-10 flex max-h-[90svh] w-full max-w-sm flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
              >
                <div className="relative aspect-[4/5] max-h-[55svh] shrink-0 overflow-hidden bg-slate-100">
                  <img
                    src={selectedMember.image_url?.startsWith("http")
                      ? selectedMember.image_url
                      : `https://api.squarecloudsmc.com${selectedMember.image_url}`}
                    alt={selectedMember.name}
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute right-3 top-3 flex flex-col gap-2">
                    {selectedMember.link_x && (
                      <a href={formatUrl(selectedMember.link_x)} target="_blank" rel="noopener noreferrer" aria-label={`${selectedMember.name} on X`} className="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-slate-900 shadow-md"><FaTwitter size={16} /></a>
                    )}
                    {selectedMember.link_instagram && (
                      <a href={formatUrl(selectedMember.link_instagram)} target="_blank" rel="noopener noreferrer" aria-label={`${selectedMember.name} on Instagram`} className="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-slate-900 shadow-md"><FaInstagram size={16} /></a>
                    )}
                    {selectedMember.link_linkedin && (
                      <a href={formatUrl(selectedMember.link_linkedin)} target="_blank" rel="noopener noreferrer" aria-label={`${selectedMember.name} on LinkedIn`} className="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-slate-900 shadow-md"><FaLinkedin size={16} /></a>
                    )}
                    {selectedMember.link_website && (
                      <a href={formatUrl(selectedMember.link_website)} target="_blank" rel="noopener noreferrer" aria-label={`${selectedMember.name}'s website`} className="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-slate-900 shadow-md"><Globe size={16} /></a>
                    )}
                  </div>
                </div>
                <div className="min-h-0 overflow-y-auto px-6 py-5">
                  <h3 className="text-2xl font-bold text-slate-900">{selectedMember.name}</h3>
                  <p className="mb-3 mt-1 text-sm font-bold uppercase tracking-wide text-blue-600">{selectedMember.role}</p>
                  {selectedMember.bio && <p className="text-[15px] leading-relaxed text-slate-600">{selectedMember.bio}</p>}
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

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