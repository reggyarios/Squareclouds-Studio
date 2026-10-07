"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isScrolledDeep, setIsScrolledDeep] = useState(false);
  
  // STATE UNTUK FITUR "SMART NAVBAR"
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const pathname = usePathname();
  const isHomePage = pathname === "/";

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      // 1. Cek Kedalaman Scroll untuk ubah warna Navbar
      setIsScrolled(currentScrollY > 50);
      setIsScrolledDeep(currentScrollY > window.innerHeight * 0.5);

      // ==========================================
      // PENGECUALIAN UNTUK LANDING PAGE (HOME)
      // ==========================================
      if (isHomePage) {
        setIsVisible(true); // Selalu tampilkan!
        if (timerRef.current) clearTimeout(timerRef.current);
        setLastScrollY(currentScrollY);
        return; // Hentikan fungsi di sini
      }

      // ==========================================
      // LOGIKA SEMBUNYI UNTUK HALAMAN SELAIN HOME
      // ==========================================
      if (currentScrollY <= 100) {
        setIsVisible(true);
        if (timerRef.current) clearTimeout(timerRef.current);
      } else if (currentScrollY > lastScrollY) {
        setIsVisible(false); // Sembunyi saat scroll bawah
        if (timerRef.current) clearTimeout(timerRef.current);
      } else if (currentScrollY < lastScrollY) {
        setIsVisible(true); // Muncul saat scroll atas
        if (timerRef.current) clearTimeout(timerRef.current);
        
        timerRef.current = setTimeout(() => {
          setIsVisible(false); // Hilang otomatis 5 detik
        }, 5000);
      }

      setLastScrollY(currentScrollY);
    };

    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [lastScrollY, isHomePage]);

  const navLinks = [
    { label: "Team", href: "/team", isExternal: true },
    { label: "About Us", href: "/#manifesto", isExternal: false },
  ];

  const handleNavClick = (
    e: React.MouseEvent<HTMLAnchorElement, MouseEvent>,
    href: string,
    isExternal: boolean
  ) => {
    if (isExternal) return;

    if (href.startsWith("/#")) {
      e.preventDefault();
      if (isHomePage) {
        const target = document.querySelector(href.replace("/", ""));
        if (target) {
          target.scrollIntoView({ behavior: "smooth" });
          window.history.replaceState(null, "", window.location.pathname);
        }
      } else {
        window.location.href = href;
      }
    }
  };

  // ===============================================
  // OTAK LOGIKA PERUBAHAN WUJUD (SHAPESHIFTING)
  // ===============================================

  // 1. Logika Pembungkus Luar (Posisi Top & Padding)
  const wrapperClass = (!isHomePage && !isScrolled)
    ? "top-0 px-0" 
    : "top-6 px-4 md:px-6";

  // 2. Logika Bentuk Navbar (Warna, Border Radius, Max-Width)
  let navStyle = "";
  if (isHomePage) {
    navStyle = isScrolled
      ? "w-full max-w-[1050px] h-[64px] rounded-full bg-white/30 backdrop-blur-md shadow-lg border-white/40 px-5 md:px-8"
      : "w-full max-w-[1200px] h-[64px] rounded-full bg-transparent border-transparent px-5 md:px-8";
  } else {
    navStyle = isScrolled
      // Efek glassmorphism diubah menjadi bg-white/40 dengan backdrop-blur-md agar transparan buram yang elegan
      ? "w-full max-w-[1050px] h-[64px] rounded-full bg-white/40 backdrop-blur-md shadow-md border-white/40 px-5 md:px-8"
      : "w-full max-w-full h-[88px] rounded-none bg-white border-b border-gray-100 px-6 md:px-12 shadow-sm"; 
  }

  // 3. Logika Warna Teks Menu
  let linkStyle = "";
  if (isHomePage) {
    linkStyle = isScrolledDeep
      ? "text-[#144b99] hover:[text-shadow:0_0_15px_rgba(20,75,153,0.8)]"
      : "text-white hover:[text-shadow:0_0_15px_rgba(255,255,255,0.8)]";
  } else {
    linkStyle = "text-slate-800 hover:text-blue-600";
  }

  // 4. Logika Warna Tombol Partner
  let btnStyle = "";
  if (isHomePage) {
    btnStyle = isScrolledDeep 
      ? "bg-white/50 text-[#144b99] border-white/50 hover:bg-white/70 backdrop-blur-md hover:[box-shadow:0_0_15px_rgba(20,75,153,0.4)]"
      : "bg-white/20 text-white border-white/30 hover:bg-white/30 backdrop-blur-md hover:[box-shadow:0_0_15px_rgba(255,255,255,0.4)]";
  } else {
    btnStyle = "bg-blue-600 text-white border-blue-600 hover:bg-blue-700 shadow-md"; 
  }

  // 5. Logika Warna Teks Logo
  let logoTextStyle = "";
  if (isHomePage) {
    logoTextStyle = isScrolledDeep ? "text-[#144b99]" : "text-white";
  } else {
    logoTextStyle = "text-slate-900";
  }

return (
  <motion.div 
    key={pathname} 
    style={{ fontFamily: "var(--font-montserrat), sans-serif" }}
    initial={{ y: -100, opacity: 0 }}
    animate={{ y: isVisible ? 0 : -100, opacity: isVisible ? 1 : 0 }}
    transition={{ 
      duration: 0.6, 
      delay: isHomePage ? 1.2 : 1.1, 
      ease: [0.16, 1, 0.3, 1] 
    }}
    className={`fixed left-0 right-0 z-50 flex justify-center pointer-events-none transition-all duration-500 ${wrapperClass}`}
  >
    <nav className={`pointer-events-auto flex items-center justify-between transition-all duration-500 border ${navStyle}`}>
       
      {/* BAGIAN KIRI: LOGO */}
        <Link
          href="/"
          onClick={(e) => {
            if (isHomePage) {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: "smooth" });
            }
          }}
          className="flex items-center gap-3 z-10 shrink-0 pointer-events-auto hover:opacity-80 transition-opacity group"
        >
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

        {/* BAGIAN KANAN: MENU + TOMBOL PARTNER */}
        <div className="z-10 shrink-0 flex items-center gap-6 md:gap-8">
          <div className="hidden md:flex items-center gap-6 md:gap-8">
            {navLinks.map((link) =>
              link.isExternal ? (
                <Link
                  key={link.label}
                  href={link.href}
                  className={`relative text-[17.5px] font-bold transition-all duration-300 ${linkStyle}`}
                >
                  {link.label}
                </Link>
              ) : (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={(e) => handleNavClick(e, link.href, link.isExternal)}
                  className={`relative text-[17.5px] font-bold transition-all duration-300 ${linkStyle}`}
                >
                  {link.label}
                </a>
              )
            )}
          </div>

          <a
            href="mailto:hello@squareclouds.com"
            className={`flex items-center justify-center px-6 py-2 h-[42px] rounded-full text-[15.5px] font-semibold transition-all duration-300 border ${btnStyle}`}
          >
            <span className="hidden lg:inline">Partner With Us</span>
          </a>
        </div>
      </nav>
    </motion.div>
  );
}