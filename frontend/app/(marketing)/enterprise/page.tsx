import { Check, ShieldAlert, Globe, Server, Activity } from "lucide-react";
import Link from "next/link";

export default function Enterprise() {
  return (
    <main className="flex-1 flex flex-col pt-16">
      {/* Enterprise Hero */}
      <section className="relative flex flex-col items-center justify-center text-center px-4 pt-32 pb-20">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[500px] bg-gradient-to-b from-blue-900/20 to-transparent pointer-events-none" />

        <h1 className="text-5xl md:text-7xl font-medium tracking-tighter mb-6 text-white max-w-4xl relative z-10">
          Scale without limits.
        </h1>

        <p className="text-xl text-gray-400 mb-10 max-w-2xl font-light relative z-10">
          Advanced security, robust infrastructure, and dedicated support for organizations pushing millions of interactions.
        </p>

        <div className="flex gap-4 relative z-10">
          <Link
            href="/contact"
            className="px-8 py-4 bg-white text-black hover:bg-gray-200 font-medium rounded-full transition-all"
          >
            Contact Sales
          </Link>
        </div>
      </section>

      {/* Enterprise Capabilities */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl font-medium tracking-tight text-white mb-6">Built for mission-critical workloads.</h2>
              <p className="text-gray-400 font-light leading-relaxed mb-8">
                The Enterprise tier replaces SQLite with highly available PostgreSQL, utilizes durable Redis queues for background tasks, and provides advanced Role-Based Access Control (RBAC) for your entire team.
              </p>

              <ul className="space-y-4">
                {[
                  "SOC2 Type II Compliance",
                  "Dedicated VPC Deployment",
                  "SSO & SAML Authentication",
                  "Custom LLM Fine-tuning",
                  "99.99% Uptime SLA",
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-gray-300">
                    <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <Check className="w-3 h-3 text-blue-400" />
                    </div>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Visual Graphic */}
            <div className="relative h-[400px] rounded-3xl border border-white/10 bg-white/[0.02] overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10" />
              <div className="grid grid-cols-2 gap-4 relative z-10 p-8 w-full">
                <div className="p-6 rounded-2xl bg-black border border-white/10 flex flex-col items-center justify-center gap-3">
                  <ShieldAlert className="w-8 h-8 text-blue-400" />
                  <span className="text-sm font-medium text-gray-300">Advanced Security</span>
                </div>
                <div className="p-6 rounded-2xl bg-black border border-white/10 flex flex-col items-center justify-center gap-3">
                  <Globe className="w-8 h-8 text-indigo-400" />
                  <span className="text-sm font-medium text-gray-300">Global Proxies</span>
                </div>
                <div className="p-6 rounded-2xl bg-black border border-white/10 flex flex-col items-center justify-center gap-3">
                  <Server className="w-8 h-8 text-emerald-400" />
                  <span className="text-sm font-medium text-gray-300">PostgreSQL Config</span>
                </div>
                <div className="p-6 rounded-2xl bg-black border border-white/10 flex flex-col items-center justify-center gap-3">
                  <Activity className="w-8 h-8 text-purple-400" />
                  <span className="text-sm font-medium text-gray-300">Custom APM</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 text-center text-gray-500 text-sm mt-auto">
        <p>&copy; {new Date().getFullYear()} SocialGrowthAI Inc. Enterprise Solutions.</p>
      </footer>
    </main>
  );
}
