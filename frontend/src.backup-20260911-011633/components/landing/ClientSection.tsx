"use client";

import { useState, useEffect } from "react";

export function ClientSection() {
  const [clients, setClients] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const res = await fetch("https://squarecloudsmc.com/cms/clients");
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();

        if (data.data && Array.isArray(data.data)) {
          setClients(data.data);
        }
      } catch (error: any) {
        console.error("Gagal memuat data client:", error);
        setFetchError(error.message);
      } finally {
        setIsLoaded(true);
      }
    };
    fetchClients();
  }, []);

  const marqueeClients = [...clients, ...clients, ...clients, ...clients];

  return (
    <section className="w-full py-16 bg-white overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 mb-8 text-center">
        <h2 className="text-xs font-bold tracking-widest text-slate-400 uppercase">
          Trusted by
        </h2>
      </div>

      <div
        className="relative w-full overflow-hidden flex"
        style={{
          maskImage:
            "linear-gradient(to right, transparent 0%, black 15%, black 85%, transparent 100%)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent 0%, black 15%, black 85%, transparent 100%)",
        }}
      >
        <div className="flex gap-16 items-center py-4 marquee-track group cursor-pointer w-max">
          {marqueeClients.map((client, idx) => {
            const rawImg = client.img || client.image_url || "";
            const imgUrl = rawImg.startsWith("http") ? rawImg : `https://squarecloudsmc.com${rawImg}`;

            return (
              <a
                key={idx}
                href={client.link || "#"}
                target={client.link ? "_blank" : "_self"}
                rel="noopener noreferrer"
                className="flex-shrink-0 transition-transform duration-300 hover:scale-105"
              >
                <img
                  src={imgUrl}
                  alt="Client Logo"
                  className="h-10 md:h-14 w-auto object-contain"
                  onError={(e) => {
                    console.error("Gagal memuat gambar logo:", imgUrl);
                  }}
                />
              </a>
            );
          })}
        </div>
      </div>

      <style jsx global>{`
        @keyframes marqueeScroll {
          0% {
            transform: translateX(0%);
          }
          100% {
            transform: translateX(-50%);
          }
        }

        .marquee-track {
          display: flex;
          width: max-content;
          animation: marqueeScroll 35s linear infinite;
        }

        .marquee-track.group:hover {
          animation-play-state: paused !important;
        }
      `}</style>
    </section>
  );
}
