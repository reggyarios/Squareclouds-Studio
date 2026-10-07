import { Footer } from "@/components/landing/Footer";

const connectionSteps = [
  "Open Minecraft: Java Edition or Minecraft: Bedrock Edition.",
  "Choose Multiplayer, then select Add Server.",
  "Enter play.sqarecloudsmc.com as the server address.",
  "Save the entry, then join using the supported version and port shown above.",
];

export default function MinecraftServerPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <main className="pt-24 md:pt-28">
        <section className="relative overflow-hidden bg-[#1a65d6] text-white">
          <div className="mx-auto grid min-h-[560px] max-w-[1200px] items-center gap-10 px-6 py-14 md:grid-cols-[1.1fr_0.9fr] md:px-12 md:py-20">
            <div className="relative z-10">
              <h1 className="max-w-2xl text-4xl font-black leading-tight sm:text-5xl md:text-6xl">
                Squareclouds Workshop Server
              </h1>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-white/70 md:text-lg">
                A server from Squareclouds Studio for our community. Designed for builders,
                especially Bedrock builders, to experience Java-style building features.
              </p>
            </div>

            <div className="relative mx-auto flex aspect-square w-full max-w-[360px] items-center justify-center">
              <div className="absolute inset-[12%] rotate-45 border border-emerald-300/20" />
              <div className="absolute inset-[22%] -rotate-12 border border-white/10" />
              <img
                src="/logo.png"
                alt="Squareclouds logo"
                className="relative z-10 h-[62%] w-[62%] object-contain drop-shadow-[0_24px_48px_rgba(0,0,0,0.35)]"
              />
            </div>
          </div>
        </section>

        <section className="bg-[#1a65d6] text-white">
          <div className="mx-auto grid max-w-[1200px] gap-8 px-6 py-10 md:grid-cols-[1fr_1fr] md:px-12 md:py-12">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/65">
                Server address
              </p>
              <p className="mt-2 break-all text-xl font-black">play.sqarecloudsmc.com</p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/65">
                Supported version
              </p>
              <p className="mt-2 text-xl font-black">1.20 - 26.1.3</p>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-6 py-20 md:px-12 md:py-28">
          <div className="grid gap-14 md:grid-cols-2 md:gap-20">
            <div>
              <h2 className="text-3xl font-black leading-tight md:text-4xl">What is inside?</h2>
              <p className="mt-5 text-base leading-relaxed text-slate-600">
                A dedicated Squareclouds workshop where Minecraft builders can build freely and
                bring their ideas to life. The server is cross-platform, supporting both Java and
                Bedrock players, while giving Bedrock builders access to Java-style building
                features and tools such as Axiom.
              </p>
            </div>
          </div>
        </section>

        <section className="border-t border-slate-200 bg-slate-50">
          <div className="mx-auto max-w-[1200px] px-6 py-20 md:px-12 md:py-24">
            <div className="max-w-2xl">
              <h2 className="text-3xl font-black leading-tight md:text-4xl">
                How to join from Minecraft Java or Bedrock
              </h2>
              <p className="mt-4 text-base leading-relaxed text-slate-600">
                Use the server address above in Minecraft Java or Bedrock Edition. Make sure your
                client is running a version between 1.20 and 26.1.3.
              </p>
            </div>

            <ol className="mt-12 grid gap-x-10 gap-y-8 md:grid-cols-2">
              {connectionSteps.map((step, index) => (
                <li key={step} className="flex gap-5 border-t border-slate-200 pt-5">
                  <span className="font-mono text-sm font-bold text-blue-600">0{index + 1}</span>
                  <p className="max-w-md text-base font-semibold leading-relaxed text-slate-800">
                    {step}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}