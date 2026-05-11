import { ArrowRight, Sparkles, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col pt-16 bg-white">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center text-center px-4 pt-32 pb-20 overflow-hidden bg-gray-50">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-100/50 rounded-full blur-[120px] pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-gray-200 text-sm text-gray-600 mb-8 shadow-sm">
          <Sparkles className="w-4 h-4 text-blue-500" />
          <span className="font-medium">Introducing Local AI Engine 2.0</span>
        </div>

        <h1 className="text-6xl md:text-8xl font-medium tracking-tighter mb-6 text-gray-900 max-w-4xl">
          Social automation, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
            reimagined.
          </span>
        </h1>

        <p className="text-xl text-gray-500 mb-10 max-w-2xl font-light">
          The ultimate platform for AI-driven, multi-platform social media growth. Engage smarter, faster, and securely.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <Link
            href="/login"
            className="group flex items-center justify-center px-8 py-4 bg-gray-900 text-white hover:bg-gray-800 font-medium rounded-full shadow-lg hover:shadow-xl transition-all"
          >
            Sign in <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            href="/enterprise"
            className="flex items-center justify-center px-8 py-4 bg-white hover:bg-gray-50 text-gray-900 font-medium rounded-full border border-gray-200 shadow-sm transition-all"
          >
            View Enterprise
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 border-t border-gray-100 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-medium tracking-tight text-gray-900 mb-4">Engineered for scale.</h2>
            <p className="text-xl text-gray-500 font-light">Everything you need to manage thousands of interactions daily.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="p-8 rounded-3xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-6">
                <Sparkles className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">Contextual AI</h3>
              <p className="text-gray-500 font-light leading-relaxed">
                Connect your local Ollama models or OpenRouter to generate highly personalized outreach that actually converts, without compromising data privacy.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 rounded-3xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-6">
                <ShieldCheck className="w-6 h-6 text-indigo-600" />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">Anti-Detection</h3>
              <p className="text-gray-500 font-light leading-relaxed">
                State-of-the-art stealth browser automation utilizing Playwright. Mimics human behavior with random delays, cursor movement, and sensible daily limits.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 rounded-3xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-6">
                <Zap className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">Hybrid Architecture</h3>
              <p className="text-gray-500 font-light leading-relaxed">
                Run the robust FastAPI server for team collaboration, or compile our Rust-based Tauri Desktop client for native, local execution.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 py-12 text-center text-gray-500 text-sm">
        <p>&copy; {new Date().getFullYear()} SocialGrowthAI Inc. All rights reserved.</p>
      </footer>
    </main>
  );
}
