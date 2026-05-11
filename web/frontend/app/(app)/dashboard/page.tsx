import { fetchAnalyticsSummary, fetchAccounts } from "@/lib/api";
import { Activity, Users, Target, CheckCircle2, TrendingUp, Shield, Zap, Clock, Star, BarChart, Globe, Cpu } from "lucide-react";
import clsx from "clsx";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  let stats = { total_actions: 0, today_actions: 0, success_rate: 0 };
  let accounts = [];

  try {
    stats = await fetchAnalyticsSummary();
    accounts = await fetchAccounts();
  } catch (err) {
    console.error("Failed to load dashboard stats", err);
  }

  const activeAccounts = accounts.filter((a: any) => a.is_active).length;
  const topAccounts = accounts.slice(0, 3); // Simplified for now

  return (
    <div className="space-y-10 pb-20">
      {/* Header Section */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-500">System Online</span>
        </div>
        <h1 className="text-4xl font-black tracking-tight text-white lg:text-6xl">
          Fleet <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-500">Intelligence</span>
        </h1>
        <p className="text-gray-500 max-w-lg">Orchestrating {activeAccounts} autonomous agents across global social clusters.</p>
      </div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Fleet Actions", value: stats.total_actions, icon: Activity, color: "text-blue-400", glow: "glow-blue", trend: "+12.5%" },
          { label: "Daily Throughput", value: stats.today_actions, icon: Zap, color: "text-purple-400", glow: "glow-purple", trend: "+5.2%" },
          { label: "Active Nodes", value: activeAccounts, icon: Globe, color: "text-amber-400", glow: "glow-amber", trend: "Optimal" },
          { label: "Success Variance", value: `${stats.success_rate}%`, icon: CheckCircle2, color: stats.success_rate >= 90 ? 'text-emerald-400' : 'text-yellow-400', glow: "glow-emerald", trend: "Stable" },
        ].map((item, i) => (
          <div key={i} className={clsx("group glass-card p-6 rounded-3xl relative overflow-hidden", item.glow)}>
            <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-white/5 blur-2xl group-hover:bg-white/10 transition-all duration-500" />
            <div className="flex items-center justify-between">
              <div className={clsx("rounded-xl bg-white/5 p-2.5", item.color)}>
                <item.icon className="h-5 w-5" />
              </div>
              <span className={clsx("text-[10px] font-bold px-2 py-1 rounded-full bg-white/5", item.color)}>
                {item.trend}
              </span>
            </div>
            <div className="mt-5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">{item.label}</h3>
              <p className="text-4xl font-black text-white tracking-tight">{item.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Second Row: Performance Leaderboard & AI Insights */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Top Performing Nodes */}
        <div className="glass-card rounded-3xl p-8">
            <div className="flex items-center gap-3 mb-8">
                <Star className="h-5 w-5 text-amber-400" />
                <h2 className="text-xl font-bold text-white">Elite Nodes</h2>
            </div>
            <div className="space-y-5">
                {topAccounts.length > 0 ? topAccounts.map((acc: any, i) => (
                    <div key={i} className="flex items-center gap-4 group">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-gray-800 to-gray-900 border border-white/5 flex items-center justify-center text-xs font-bold text-white group-hover:border-blue-500/50 transition-colors">
                            {acc.username[0].toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-white truncate">@{acc.username}</p>
                            <p className="text-[10px] text-gray-500 uppercase tracking-wider">{acc.platform}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm font-bold text-blue-400">98%</p>
                            <p className="text-[10px] text-gray-500">TRUST</p>
                        </div>
                    </div>
                )) : (
                    <p className="text-sm text-gray-600 italic">No nodes available yet.</p>
                )}
            </div>
            <button className="w-full mt-8 py-3 rounded-xl bg-white/5 border border-white/5 text-xs font-bold text-gray-400 hover:bg-white/10 hover:text-white transition-all">
                Manage All Nodes
            </button>
        </div>

        {/* AI Audience Insights */}
        <div className="glass-card rounded-3xl p-8 bg-gradient-to-br from-white/5 to-transparent">
          <div className="flex items-center gap-3 mb-8">
            <Cpu className="h-5 w-5 text-purple-400" />
            <h2 className="text-xl font-bold text-white">AI Targeting</h2>
          </div>
          <div className="space-y-6">
            {[
                { niche: "Software Dev", share: 45, color: "bg-blue-500" },
                { niche: "Crypto / Web3", share: 30, color: "bg-purple-500" },
                { niche: "SaaS Founders", share: 25, color: "bg-emerald-500" },
            ].map((n, i) => (
                <div key={i} className="space-y-2">
                    <div className="flex justify-between text-xs font-bold">
                        <span className="text-gray-400">{n.niche}</span>
                        <span className="text-white">{n.share}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <div className={clsx("h-full rounded-full transition-all duration-1000", n.color)} style={{ width: `${n.share}%` }} />
                    </div>
                </div>
            ))}
            <div className="mt-8 p-4 rounded-2xl bg-purple-500/10 border border-purple-500/20">
                <p className="text-[10px] font-bold text-purple-400 uppercase mb-1">Targeting Sentiment</p>
                <p className="text-sm text-gray-300">Audience sentiment is currently <span className="text-white font-bold">Highly Receptive</span> to technical outreach.</p>
            </div>
          </div>
        </div>

        {/* Fleet Health */}
        <div className="glass-card rounded-3xl p-8 border border-white/5">
          <div className="flex items-center gap-3 mb-8">
            <Shield className="h-5 w-5 text-emerald-400" />
            <h2 className="text-xl font-bold text-white">Fleet Health</h2>
          </div>
          
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-gray-500">Uptime Score</span>
                <span className="text-emerald-400">99.8%</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]" style={{ width: '99.8%' }} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-gray-500">Proxy Stability</span>
                <span className="text-blue-400">Optimal</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full shadow-[0_0_8px_#3b82f6]" style={{ width: '85%' }} />
              </div>
            </div>

            <div className="mt-10 pt-8 border-t border-white/5">
                <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-gray-500">Version</span>
                    <span className="text-white">v0.4.2-PRO</span>
                </div>
            </div>
          </div>
        </div>
      </div>

      {/* Third Row: Activity Feed */}
      <div className="glass-card rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-blue-400" />
              <h2 className="text-xl font-bold text-white">Live Activity Feed</h2>
            </div>
            <div className="flex items-center gap-4">
                 <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-ping" />
                    <span className="text-[10px] font-bold text-blue-400 uppercase">Live Streaming</span>
                 </div>
                 <button className="text-xs font-bold text-gray-500 hover:text-white transition-colors">History</button>
            </div>
          </div>
          
          <div className="space-y-4">
            {stats.total_actions > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 {[
                    { text: 'Campaign "Growth-01" completed 54 actions', time: '2m ago', platform: 'Instagram', status: 'SUCCESS' },
                    { text: 'New Account Synced: @growth_pilot', time: '1h ago', platform: 'Twitter', status: 'SYNCED' },
                    { text: 'Target Profile Scraped: tech_insider', time: '3h ago', platform: 'LinkedIn', status: 'SUCCESS' },
                    { text: 'Automated DM Sent to 12 users', time: '5h ago', platform: 'TikTok', status: 'SUCCESS' },
                 ].map((act, i) => (
                    <div key={i} className="flex items-center gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] transition-colors cursor-pointer group">
                        <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                           <Zap className="h-5 w-5 text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                           <p className="text-sm font-medium text-white truncate">{act.text}</p>
                           <p className="text-xs text-gray-500">{act.time} • {act.platform}</p>
                        </div>
                        <span className={clsx("text-[10px] font-bold px-2 py-1 rounded-md", act.status === 'SUCCESS' ? 'text-emerald-400 bg-emerald-500/10' : 'text-blue-400 bg-blue-500/10')}>
                            {act.status}
                        </span>
                    </div>
                 ))}
              </div>
            ) : (
              <div className="py-20 text-center">
                <div className="mx-auto w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                  <BarChart className="h-8 w-8 text-gray-600" />
                </div>
                <p className="text-gray-500 font-medium">No system activity detected.</p>
                <p className="text-xs text-gray-600 mt-1">Activities will appear here once your agents begin processing.</p>
              </div>
            )}
          </div>
      </div>
    </div>
  );
}
);
}