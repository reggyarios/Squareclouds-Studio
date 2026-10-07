import "../globals.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "CMS Admin - Squareclouds",
};

export default function CMSLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-50 text-slate-800 antialiased`}>{children}</body>
    </html>
  );
}
