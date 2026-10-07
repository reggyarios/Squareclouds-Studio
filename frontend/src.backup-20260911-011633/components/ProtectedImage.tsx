"use client";

import React from "react";

interface ProtectedImageProps {
  src: string;
  alt: string;
  className?: string;
  watermarkText?: string; // Opsional: jika ingin tambah teks watermark dari kode
}

export function ProtectedImage({ 
  src, 
  alt, 
  className = "", 
  watermarkText 
}: ProtectedImageProps) {
  return (
    <div 
      className={`relative overflow-hidden ${className}`}
      // Mencegah klik kanan pada area ini
      onContextMenu={(e) => e.preventDefault()} 
    >
      {/* 1. LAYER SHIELD: Overlay transparan di posisi paling atas */}
      {/* Jika user mencoba "Save Image", mereka akan menargetkan div kosong ini */}
      <div className="absolute inset-0 z-20 w-full h-full bg-transparent"></div>

      {/* 2. OPTIONAL WATERMARK: Teks transparan di atas gambar (opsional) */}
      {watermarkText && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none select-none overflow-hidden">
          <div className="transform -rotate-45 opacity-20 text-white font-black text-4xl md:text-6xl tracking-widest whitespace-nowrap">
            {watermarkText} • {watermarkText}
          </div>
        </div>
      )}

      {/* 3. MAIN IMAGE: Gambar produk itu sendiri */}
      <img
        src={src}
        alt={alt}
        // Mencegah gambar di-drag & drop ke desktop
        draggable={false} 
        // Tailwind class: mematikan seleksi & interaksi kursor pada gambar
        className="object-cover w-full h-full select-none pointer-events-none" 
      />
    </div>
  );
}