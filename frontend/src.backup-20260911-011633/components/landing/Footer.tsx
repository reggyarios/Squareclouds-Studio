"use client";

import Link from "next/link";
import { Mail } from "lucide-react";
import { FaTwitter, FaInstagram, FaYoutube, FaTiktok, FaLinkedin } from "react-icons/fa";

export function Footer() {
  return (
    <footer className="w-full mt-auto text-slate-800 flex flex-col border-t border-gray-100">
      
      {/* =========================================
          BAGIAN ATAS (BACKGROUND GAMBAR + GRADIENT)
          ========================================= */}
      <div className="relative w-full pt-20 pb-16 overflow-hidden">
        
        {/* Layer 1: Gambar Background (Opasitas dinaikkan agar sedikit lebih jelas) */}
        <div 
          className="absolute inset-0 z-0 opacity-[0.80]"
          style={{
            backgroundImage: "url('/folder/card-bg.png')",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        
        {/* Layer 2: Gradient (Putih solid di paling atas, perlahan transparan ke arah bawah) */}
        <div className="absolute inset-0 z-0 bg-gradient-to-b from-white via-white/80 to-white/40" />

        {/* KONTEN UTAMA */}
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 relative z-10">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-12 lg:gap-8">
            
            {/* KOLOM 1: BRANDING */}
            <div className="lg:col-span-4 flex flex-col gap-6 lg:pr-8">
              <Link href="/" className="flex items-center gap-3 w-max">
                <img
            src="/logo.png"
            alt="Squareclouds Logo"
            className="h-[43px] w-auto rounded-md object-contain group-hover:scale-105 transition-transform duration-300"
          />
          <img
            src="/logo_font.png"
            alt="Squareclouds Logo"
            className="h-[40px] w-auto object-contain group-hover:scale-105 transition-transform duration-300"
          />
              </Link>
              <p className="text-slate-700 text-[15px] leading-relaxed font-medium">
                The most fun and innovative way to make things different, and we can change the
                unthinkable through games.
              </p>

              {/* Social Media Icons */}
              <div className="flex gap-3 mt-2 flex-wrap">
                <a
                  href="https://x.com/squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200 flex items-center justify-center text-slate-400 hover:bg-[#1DA1F2] hover:text-white hover:border-[#1DA1F2] shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaTwitter size={15} />
                </a>
                <a
                  href="http://instagram.com/squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200 flex items-center justify-center text-slate-400 hover:bg-[#E1306C] hover:text-white hover:border-[#E1306C] shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaInstagram size={15} />
                </a>
                <a
                  href="https://www.youtube.com/@squareclds"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200 flex items-center justify-center text-slate-400 hover:bg-[#FF0000] hover:text-white hover:border-[#FF0000] shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaYoutube size={15} />
                </a>
                <a
                  href="https://www.tiktok.com/@squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200 flex items-center justify-center text-slate-400 hover:bg-black hover:text-white hover:border-black shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaTiktok size={15} />
                </a>
                <a
                  href="https://www.linkedin.com/company/squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200 flex items-center justify-center text-slate-400 hover:bg-[#0A66C2] hover:text-white hover:border-[#0A66C2] shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaLinkedin size={15} />
                </a>
              </div>
            </div>

            {/* KOLOM 2: RESOURCES */}
            <div className="lg:col-span-2 flex flex-col gap-4">
              <h4 className="text-slate-900 font-bold tracking-wider text-[13px] uppercase mb-1">
                Resources
              </h4>
              <FooterLink href="/">Home</FooterLink>
              <FooterLink href="/commission">Commissioning</FooterLink>
              <FooterLink href="/marketplace">Marketplace</FooterLink>
              <FooterLink href="/premade">Premade Assets</FooterLink>
            </div>

            {/* KOLOM 3: ABOUT US */}
            <div className="lg:col-span-2 flex flex-col gap-4">
              <h4 className="text-slate-900 font-bold tracking-wider text-[13px] uppercase mb-1">
                About Us
              </h4>
              <FooterLink href="/#manifesto">Our Story</FooterLink>
              <FooterLink href="/team">Team</FooterLink>
              <FooterLink href="mailto:squarecloudsmc@gmail.com">Partner With Us</FooterLink>
            </div>

            {/* KOLOM 4: NEWSLETTER */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              <h4 className="text-slate-900 font-bold tracking-wider text-[13px] uppercase mb-1">
                Our Newsletter
              </h4>
              <p className="text-slate-700 text-[14px] leading-relaxed mb-1 font-medium">
                Subscribe to our newsletter to get our news & deals delivered to you.
              </p>
              <form
                className="relative flex items-center w-full mt-1"
                onSubmit={(e) => e.preventDefault()}
              >
                <div className="absolute left-4 text-slate-400">
                  <Mail size={16} />
                </div>
                <input
                  type="email"
                  placeholder="Email Address"
                  className="w-full bg-white/90 backdrop-blur-md border border-gray-200 text-slate-900 text-sm rounded-full py-3 pl-11 pr-28 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-400 shadow-sm"
                  required
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1.5 bottom-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold px-5 rounded-full transition-colors flex items-center justify-center shadow-md"
                >
                  Join
                </button>
              </form>
            </div>
            
          </div>
        </div>
      </div>

      {/* =========================================
          BAGIAN BAWAH (BLUE COPYRIGHT BAR)
          ========================================= */}
      <div className="w-full bg-[#1a65d6] relative z-20">
        {/* py-8 diubah menjadi py-4 agar tinggi/ketebalannya berkurang setengah */}
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 py-4 flex flex-col md:flex-row items-center justify-between gap-3 border-t border-white/10">
          
          {/* Ukuran teks dikecilkan (text-[11px]) dan warna diperbaiki ke text-white/90 */}
          <p className="text-[#ffffff] text-[11px] font-bold tracking-widest uppercase text-center md:text-left">
            © {new Date().getFullYear()} Squareclouds. All rights reserved.
          </p>
          
          {/* Teks link dikecilkan (text-xs) dan disesuaikan warnanya (text-white/70) agar cocok dengan background biru */}
          <div className="flex gap-6 text-xs text-white font-medium">
            <Link href="#" className="hover:text-white/70 transition-colors font-medium">
              Privacy Policy
            </Link>
            <Link href="#" className="hover:text-white/70 transition-colors font-medium">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>

    </footer>
  );
}

// Komponen link diubah warna defaultnya (slate-500) dan efek hover menjadi biru (blue-600)
function FooterLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="text-slate-700 hover:text-blue-600 font-medium transition-colors w-max text-[15px]"
    >
      {children}
    </Link>
  );
}