import { ArrowRight, Bot, Shield, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20 bg-gradient-to-b from-gray-900 to-black">
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
          Supercharge Your Social Growth
        </h1>
        <p className="text-xl md:text-2xl text-gray-400 mb-10 max-w-3xl">
          The ultimate hybrid platform for AI-driven, multi-platform social media automation. Engage smarter, not harder.
        </p>
        <div className="flex space-x-4">
          <Link
            href="/dashboard"
            className="flex items-center px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all"
          >
            Go to Dashboard <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
          <Link
            href="/accounts"
            className="flex items-center px-8 py-4 bg-gray-800 hover:bg-gray-700 text-white font-semibold rounded-lg border border-gray-700 transition-all"
          >
            Connect Accounts
          </Link>
        </div>
      </main>

      {/* Features Section */}
      <section className="py-20 bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white">Why SocialGrowthAI?</h2>
            <p className="mt-4 text-gray-400">Production-ready features designed for scale and privacy.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {/* Feature 1 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-gray-700 transition-colors">
              <Bot className="w-12 h-12 text-blue-500 mb-6" />
              <h3 className="text-2xl font-bold text-white mb-4">Local AI Engine</h3>
              <p className="text-gray-400">
                Leverage local LLMs like Ollama to analyze profiles and generate highly contextual, personalized direct messages without leaking data to third parties.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-gray-700 transition-colors">
              <Shield className="w-12 h-12 text-emerald-500 mb-6" />
              <h3 className="text-2xl font-bold text-white mb-4">Anti-Detection</h3>
              <p className="text-gray-400">
                Advanced browser automation with intelligent scheduling, random delays, and natural behavioral mimicking to keep your accounts safe from bans.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-gray-700 transition-colors">
              <Zap className="w-12 h-12 text-purple-500 mb-6" />
              <h3 className="text-2xl font-bold text-white mb-4">Hybrid Architecture</h3>
              <p className="text-gray-400">
                Built as a powerful monorepo. Run the robust Web application (FastAPI + Next.js) for team collaboration, or compile the Tauri Desktop app for sheer native performance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-t from-gray-900 to-black text-center">
        <h2 className="text-3xl font-bold text-white mb-6">Ready to scale your audience?</h2>
        <Link
          href="/accounts"
          className="inline-flex items-center px-10 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg transition-all"
        >
          Get Started Now
        </Link>
      </section>

      <footer className="bg-gray-950 py-8 text-center text-gray-500 text-sm">
        <p>&copy; {new Date().getFullYear()} SocialGrowthAI. Open Source Architecture.</p>
      </footer>
    </div>
  );
}