import { HeroSection } from "@/components/landing/HeroSection";
import { ManifestoSection } from "@/components/landing/ManifestoSection";
import { ClientSection } from "@/components/landing/ClientSection";
import { ExhibitionSection } from "@/components/landing/ExhibitionSection";
import { ProductSection } from "@/components/landing/ProductSection";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="bg-white min-h-screen">
      <HeroSection />

      <main className="relative z-10 w-full flex flex-col items-center">
        <ExhibitionSection />
        <ManifestoSection />
        <ClientSection />
        <ProductSection />
        <div className="w-full">
          <Footer />
        </div>
      </main>
    </div>
  );
}