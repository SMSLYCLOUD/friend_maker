import { ArrowRight, Sparkles, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col pt-16">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center text-center px-4 pt-32 pb-20 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm text-gray-300 mb-8 backdrop-blur-sm">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span>Introducing Local AI Engine 2.0</span>
        </div>

        <h1 className="text-6xl md:text-8xl font-medium tracking-tighter mb-6 text-white max-w-4xl">
          Social automation, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
            reimagined.
          </span>
        </h1>

        <p className="text-xl text-gray-400 mb-10 max-w-2xl font-light">
          The ultimate platform for AI-driven, multi-platform social media growth. Engage smarter, faster, and securely.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <Link
            href="/register"
            className="group flex items-center justify-center px-8 py-4 bg-white text-black hover:bg-gray-200 font-medium rounded-full transition-all"
          >
            Start building <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            href="/enterprise"
            className="flex items-center justify-center px-8 py-4 bg-white/5 hover:bg-white/10 text-white font-medium rounded-full border border-white/10 transition-all"
          >
            View Enterprise
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-medium tracking-tight text-white mb-4">Engineered for scale.</h2>
            <p className="text-xl text-gray-400 font-light">Everything you need to manage thousands of interactions daily.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-8 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6">
                <Sparkles className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-xl font-medium text-white mb-3">Contextual AI</h3>
              <p className="text-gray-400 font-light leading-relaxed">
                Connect your local Ollama models or OpenRouter to generate highly personalized outreach that actually converts, without compromising data privacy.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-6">
                <ShieldCheck className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-medium text-white mb-3">Anti-Detection</h3>
              <p className="text-gray-400 font-light leading-relaxed">
                State-of-the-art stealth browser automation utilizing Playwright. Mimics human behavior with random delays, cursor movement, and sensible daily limits.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-6">
                <Zap className="w-6 h-6 text-emerald-400" />
              </div>
              <h3 className="text-xl font-medium text-white mb-3">Hybrid Architecture</h3>
              <p className="text-gray-400 font-light leading-relaxed">
                Run the robust FastAPI server for team collaboration, or compile our Rust-based Tauri Desktop client for native, local execution.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 text-center text-gray-500 text-sm">
        <p>&copy; {new Date().getFullYear()} SocialGrowthAI Inc. All rights reserved.</p>
      </footer>
    </main>
  );
}
