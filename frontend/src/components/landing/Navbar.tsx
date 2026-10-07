"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isScrolledDeep, setIsScrolledDeep] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  // STATE UNTUK FITUR "SMART NAVBAR"
  const [isVisible, setIsVisible] = useState(true);
  const lastScrollYRef = useRef(0);

  const pathname = usePathname();
  const isHomePage = pathname === "/";

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMobileMenuOpen(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMobileMenuOpen]);

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
        lastScrollYRef.current = currentScrollY;
        return; // Hentikan fungsi di sini
      }

      // ==========================================
      // LOGIKA SEMBUNYI UNTUK HALAMAN SELAIN HOME
      // ==========================================
      if (currentScrollY <= 100 || currentScrollY < lastScrollYRef.current) {
        setIsVisible(true);
      } else if (currentScrollY > lastScrollYRef.current) {
        setIsVisible(false);
      }

      lastScrollYRef.current = currentScrollY;
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [isHomePage]);

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
    : "top-4 px-3 sm:top-6 sm:px-4 md:px-6";

  // 2. Logika Bentuk Navbar (Warna, Border Radius, Max-Width)
  let navStyle = "";
  if (isHomePage) {
    navStyle = isScrolled
      ? "w-full max-w-[1050px] h-[58px] sm:h-[64px] rounded-full bg-white/30 backdrop-blur-md shadow-lg px-4 sm:px-5 md:px-8"
      : "w-full max-w-[1200px] h-[58px] sm:h-[64px] rounded-full bg-transparent px-4 sm:px-5 md:px-8";
  } else {
    navStyle = isScrolled
      // Efek glassmorphism diubah menjadi bg-white/40 dengan backdrop-blur-md agar transparan buram yang elegan
      ? "w-full max-w-[1050px] h-[64px] rounded-full bg-white/40 backdrop-blur-md shadow-md px-5 md:px-8"
      : "w-full max-w-full h-[88px] rounded-none bg-white px-6 md:px-12 shadow-sm"; 
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
      ? "bg-white/50 text-[#144b99] hover:bg-white/70 backdrop-blur-md hover:[box-shadow:0_0_15px_rgba(20,75,153,0.4)]"
      : "bg-white/20 text-white hover:bg-white/30 backdrop-blur-md hover:[box-shadow:0_0_15px_rgba(255,255,255,0.4)]";
  } else {
    btnStyle = "bg-blue-600 text-white hover:bg-blue-700 shadow-md"; 
  }

  // 5. Logika Warna Teks Logo
  let logoTextStyle = "";
  if (isHomePage) {
    logoTextStyle = isScrolledDeep ? "text-[#144b99]" : "text-white";
  } else {
    logoTextStyle = "text-slate-900";
  }

return (
  <>
  <motion.div 
    key={pathname} 
    style={{ fontFamily: "var(--font-montserrat), sans-serif" }}
    initial={{ y: -100, opacity: 0 }}
    animate={{ y: isVisible ? 0 : -100, opacity: isVisible ? 1 : 0 }}
    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
    className={`fixed left-0 right-0 z-50 flex justify-center pointer-events-none transition-[top,padding] duration-200 ${wrapperClass}`}
  >
    <nav className={`pointer-events-auto flex items-center justify-between transition-all duration-500 ${navStyle}`}>
       
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
            className="h-[34px] sm:h-[43px] w-auto rounded-md object-contain group-hover:scale-105 transition-transform duration-300"
          />
          <img
            src="/logo_font.png"
            alt="Squareclouds Logo"
            className={`h-[30px] sm:h-[40px] w-auto object-contain group-hover:scale-105 transition-transform duration-300 ${
              isHomePage && !isScrolledDeep ? "brightness-0 invert" : ""
            }`}
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
            className={`hidden md:flex items-center justify-center px-3 sm:px-6 py-2 h-[38px] sm:h-[42px] rounded-full text-[13px] sm:text-[15.5px] font-semibold transition-all duration-300 ${btnStyle}`}
          >
            Partner With Us
          </a>

          <button
            type="button"
            aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            className={`flex md:hidden h-10 w-10 items-center justify-center transition-opacity ${
              isHomePage
                ? isScrolledDeep
                  ? "text-[#144b99] hover:opacity-70"
                  : "text-white hover:opacity-70"
                : "text-slate-800 hover:opacity-70"
            }`}
          >
            {isMobileMenuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          </button>
        </div>
      </nav>
    </motion.div>

    <AnimatePresence>
      {isMobileMenuOpen && (
        <>
          <motion.button
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setIsMobileMenuOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-slate-950/55 md:hidden"
          />
          <motion.aside
            id="mobile-navigation"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="fixed inset-y-0 right-0 z-[61] flex w-[min(88vw,360px)] flex-col bg-white px-7 pb-8 pt-6 text-slate-900 shadow-2xl md:hidden"
          >
            <div className="flex items-center justify-between pb-5">
              <span className="text-sm font-bold uppercase tracking-widest text-slate-500">Menu</span>
              <button
                type="button"
                aria-label="Close menu"
                onClick={() => setIsMobileMenuOpen(false)}
                className="flex h-10 w-10 items-center justify-center rounded-full text-slate-700 transition-colors hover:bg-slate-100"
              >
                <X size={22} aria-hidden="true" />
              </button>
            </div>

            <nav className="flex flex-col gap-2 py-7" aria-label="Mobile navigation">
              {navLinks.map((link) =>
                link.isExternal ? (
                  <Link
                    key={link.label}
                    href={link.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="rounded-md px-3 py-4 text-xl font-bold transition-colors hover:bg-slate-100 hover:text-blue-700"
                  >
                    {link.label}
                  </Link>
                ) : (
                  <a
                    key={link.label}
                    href={link.href}
                    onClick={(event) => {
                      handleNavClick(event, link.href, link.isExternal);
                      setIsMobileMenuOpen(false);
                    }}
                    className="rounded-md px-3 py-4 text-xl font-bold transition-colors hover:bg-slate-100 hover:text-blue-700"
                  >
                    {link.label}
                  </a>
                )
              )}
            </nav>

            <a
              href="mailto:hello@squareclouds.com"
              onClick={() => setIsMobileMenuOpen(false)}
              className="mt-auto flex min-h-12 items-center justify-center rounded-full border border-blue-700 bg-blue-700 px-5 text-base font-bold text-white transition-colors hover:bg-blue-800"
            >
              Partner With Us
            </a>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  </>
  );
}