import type { Metadata } from "next";
import { Inter, Silkscreen, Montserrat } from "next/font/google";
import "../globals.css";
import { Navbar } from "@/components/landing/Navbar";
import { TransitionOverlay } from "@/components/landing/TransitionOverlay";
import { CustomScrollbar } from "@/components/CustomScrollbar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "900"],
  display: "swap",
});

// 1. Konfigurasi Font Montserrat
const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

const silkscreen = Silkscreen({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-pixel",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Squareclouds Studio",
  description:
    "The most fun and innovative way to make things different, and we can change the unthinkable through games.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        // 2. Masukkan ${montserrat.variable} ke className body
        className={`${inter.variable} ${silkscreen.variable} ${montserrat.variable} font-sans bg-white text-slate-300 antialiased relative min-h-screen flex flex-col`}
      >
        <TransitionOverlay />
        <Navbar />
        <CustomScrollbar />
        <main className="w-full relative z-10 flex-1">{children}</main>
      </body>
    </html>
  );
}