"use client";

import Link from "next/link";
import { FaTwitter, FaInstagram, FaYoutube, FaTiktok, FaLinkedin } from "react-icons/fa";

export function Footer() {
  return (
    <footer className="relative isolate w-full mt-auto overflow-hidden text-slate-800 flex flex-col">
      <div
        aria-hidden="true"
        className="absolute inset-0 z-0 opacity-[0.80]"
        style={{
          backgroundImage: "url('/folder/card-bg.png')",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 z-0 bg-gradient-to-b from-white via-white/80 to-white/40"
      />
      
      {/* =========================================
          BAGIAN ATAS (BACKGROUND GAMBAR + GRADIENT)
          ========================================= */}
      <div className="relative z-10 w-full pt-20 pb-16">
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
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:bg-[#1DA1F2] hover:text-white shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaTwitter size={15} />
                </a>
                <a
                  href="http://instagram.com/squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:bg-[#E1306C] hover:text-white shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaInstagram size={15} />
                </a>
                <a
                  href="https://www.youtube.com/@squareclds"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:bg-[#FF0000] hover:text-white shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaYoutube size={15} />
                </a>
                <a
                  href="https://www.tiktok.com/@squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:bg-black hover:text-white shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaTiktok size={15} />
                </a>
                <a
                  href="https://www.linkedin.com/company/squarecloudsmc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:bg-[#0A66C2] hover:text-white shadow-sm hover:shadow-md transition-all duration-300"
                >
                  <FaLinkedin size={15} />
                </a>
              </div>
            </div>

            {/* KOLOM 2: RESOURCES */}
            <div className="lg:col-span-2 lg:col-start-9 flex flex-col gap-4">
              <h4 className="text-slate-900 font-bold tracking-wider text-[13px] uppercase mb-1">
                Resources
              </h4>
              <FooterLink href="/">Home</FooterLink>
              <FooterLink href="/commission">Commissioning</FooterLink>
              <FooterLink href="/marketplace">Marketplace</FooterLink>
              <FooterLink href="/premade">Premade Assets</FooterLink>
            </div>

            {/* KOLOM 3: ABOUT US */}
            <div className="lg:col-span-2 lg:col-start-11 flex flex-col gap-4">
              <h4 className="text-slate-900 font-bold tracking-wider text-[13px] uppercase mb-1">
                About Us
              </h4>
              <FooterLink href="/#manifesto">Our Story</FooterLink>
              <FooterLink href="/team">Team</FooterLink>
              <FooterLink href="mailto:contact@squarecloudsmc.com">Partner With Us</FooterLink>
            </div>

          </div>
        </div>
      </div>

      {/* =========================================
          BAGIAN BAWAH (BLUE COPYRIGHT BAR)
          ========================================= */}
      <div className="relative z-10 w-full bg-[#1a65d6]">
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