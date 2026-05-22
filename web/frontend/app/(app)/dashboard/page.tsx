"use client";

import { useState, useEffect } from "react";
import { fetchAnalyticsSummary, fetchAccounts, fetchActivityFeed, fetchAudienceInsights } from "@/lib/api";
import { Activity, Target, CheckCircle2, Shield, Zap, Clock, Star, BarChart, Globe, Cpu, ArrowRight } from "lucide-react";
import Link from "next/link";
import clsx from "clsx";

function formatTime(unix: number): string {
  const seconds = Math.floor((Date.now() / 1000) - unix);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function Dashboard() {
  const [stats, setStats] = useState({ total_actions: 0, today_actions: 0, success_rate: 0 });
  const [accounts, setAccounts] = useState<any[]>([]);
  const [activityFeed, setActivityFeed] = useState<any[]>([]);
  const [audienceInsights, setAudienceInsights] = useState<any>({ total_targets: 0, processed_targets: 0, avg_ai_score: 0 });

  useEffect(() => {
    Promise.all([
      fetchAnalyticsSummary(),
      fetchAccounts(),
      fetchActivityFeed(),
      fetchAudienceInsights()
    ]).then(([s, a, f, i]) => {
      setStats(s);
      setAccounts(a);
      setActivityFeed(f);
      setAudienceInsights(i);
    }).catch(err => {
      console.error("Failed to load dashboard stats", err);
    });
  }, []);

  const activeAccounts = accounts.filter((a: any) => a.is_active).length;
  const topAccounts = accounts.slice(0, 3);

  return (
    <div className="space-y-6 sm:space-y-10 pb-6 sm:pb-20">
      {/* Header Section */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
          <span className="text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-500">System Online</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-white lg:text-6xl">
          Fleet <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-500">Intelligence</span>
        </h1>
        <p className="text-gray-500 max-w-xs sm:max-w-lg">Orchestrating {activeAccounts} autonomous agents across global social clusters.</p>
      </div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Fleet Actions", value: stats.total_actions, icon: Activity, color: "text-blue-400", glow: "glow-blue", trend: "All Time" },
          { label: "Daily Throughput", value: stats.today_actions, icon: Zap, color: "text-purple-400", glow: "glow-purple", trend: "24h" },
          { label: "Active Nodes", value: activeAccounts, icon: Globe, color: "text-amber-400", glow: "glow-amber", trend: "Current" },
          { label: "Success Variance", value: `${stats.success_rate}%`, icon: CheckCircle2, color: stats.success_rate >= 90 ? 'text-emerald-400' : 'text-yellow-400', glow: "glow-emerald", trend: stats.success_rate >= 90 ? "Healthy" : "Warning" },
        ].map((item, i) => (
          <div key={i} className={clsx("group glass-card p-4 sm:p-6 rounded-3xl relative overflow-hidden", item.glow)}>
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
              <p className="text-2xl sm:text-4xl font-black text-white tracking-tight">{item.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Second Row: Performance Leaderboard & AI Insights */}
      <div className="grid grid-cols-1 gap-6 lg:gap-8 lg:grid-cols-3">
        {/* Top Performing Nodes */}
        <div className="glass-card rounded-3xl p-4 sm:p-8">
            <div className="flex items-center justify-between mb-6 sm:mb-8">
                <div className="flex items-center gap-2 sm:gap-3">
                    <Star className="h-4 w-4 sm:h-5 sm:w-5 text-amber-400" />
                    <h2 className="text-lg sm:text-xl font-bold text-white">Elite Nodes</h2>
                </div>
                <Link href="/accounts" className="text-[10px] font-bold text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-wider">View All</Link>
            </div>
            <div className="space-y-3 sm:space-y-5">
                {topAccounts.length > 0 ? topAccounts.map((acc: any, i) => (
                    <div key={i} className="flex items-center gap-3 sm:gap-4 group">
                        <div className="h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-gradient-to-br from-gray-800 to-gray-900 border border-white/5 flex items-center justify-center text-xs sm:text-xs font-bold text-white group-hover:border-blue-500/50 transition-colors">
                            {acc.username[0].toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs sm:text-sm font-bold text-white truncate">@{acc.username}</p>
                            <p className="text-[9px] sm:text-[10px] text-gray-500 uppercase tracking-wider">{acc.platform}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-xs sm:text-sm font-bold text-blue-400">{acc.is_active ? "Active" : "Inactive"}</p>
                            <p className="text-[9px] sm:text-[10px] text-gray-500">STATUS</p>
                        </div>
                    </div>
                )) : (
                    <p className="text-sm text-gray-600 italic">No nodes available yet.</p>
                )}
            </div>
            <Link href="/campaigns" className="w-full mt-6 sm:mt-8 py-2 sm:py-3 rounded-xl bg-white/5 border border-white/5 text-xs sm:text-xs font-bold text-gray-400 hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-2">
                Deploy Campaigns <ArrowRight className="w-3 h-3 sm:w-3 sm:h-3" />
            </Link>
        </div>

        {/* AI Audience Insights */}
        <div className="glass-card rounded-3xl p-4 sm:p-8 bg-gradient-to-br from-white/5 to-transparent">
          <div className="flex items-center gap-2 sm:gap-3 mb-6 sm:mb-8">
            <Cpu className="h-4 w-4 sm:h-5 sm:w-5 text-purple-400" />
            <h2 className="text-lg sm:text-xl font-bold text-white">AI Targeting</h2>
          </div>
          {audienceInsights.total_targets > 0 ? (
            <div className="space-y-4 sm:space-y-6">
              <div className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-white/5 border border-white/5">
                <div>
                  <p className="text-[9px] sm:text-[10px] font-bold text-gray-500 uppercase tracking-wider">Total Targets</p>
                  <p className="text-xl sm:text-2xl font-black text-white">{audienceInsights.total_targets}</p>
                </div>
                <div className="text-right">
                  <p className="text-[9px] sm:text-[10px] font-bold text-gray-500 uppercase tracking-wider">Processed</p>
                  <p className="text-xl sm:text-2xl font-black text-purple-400">{audienceInsights.processed_targets}</p>
                </div>
              </div>
              <div className="p-3 sm:p-4 rounded-xl bg-white/5 border border-white/5">
                <p className="text-[9px] sm:text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Avg AI Score</p>
                <p className="text-xl sm:text-2xl font-black text-white">{audienceInsights.avg_ai_score}</p>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mt-2">
                  <div className="h-full bg-purple-500 rounded-full" style={{ width: `${Math.min(audienceInsights.avg_ai_score * 20, 100)}%` }} />
                </div>
              </div>
            </div>
          ) : (
            <div className="py-8 sm:py-12 text-center">
              <div className="mx-auto w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-white/5 flex items-center justify-center mb-3">
                <Target className="h-5 w-5 sm:h-6 sm:w-6 text-gray-600" />
              </div>
              <p className="text-gray-500 text-sm">No targeting data yet.</p>
              <p className="text-xs text-gray-600 mt-1">Insights will appear when campaigns begin processing.</p>
            </div>
          )}
        </div>

        {/* Fleet Health */}
        <div className="glass-card rounded-3xl p-4 sm:p-8 border border-white/5">
          <div className="flex items-center gap-2 sm:gap-3 mb-6 sm:mb-8">
            <Shield className="h-4 w-4 sm:h-5 sm:w-5 text-emerald-400" />
            <h2 className="text-lg sm:text-xl font-bold text-white">Fleet Health</h2>
          </div>
          
          <div className="space-y-4 sm:space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-gray-500">Active Nodes</span>
                <span className="text-emerald-400">{activeAccounts}/{accounts.length}</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]" style={{ width: accounts.length > 0 ? `${(activeAccounts / accounts.length) * 100}%` : '0%' }} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-gray-500">Success Rate</span>
                <span className="text-blue-400">{stats.success_rate}%</span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full shadow-[0_0_8px_#3b82f6]" style={{ width: `${stats.success_rate}%` }} />
              </div>
            </div>

            <div className="mt-6 sm:mt-10 pt-4 sm:pt-8 border-t border-white/5 space-y-3 sm:space-y-4">
                <div className="flex items-center justify-between text-xs sm:text-xs font-bold">
                    <span className="text-gray-500">Total Accounts</span>
                    <span className="text-white">{accounts.length}</span>
                </div>
                <Link href="/settings" className="flex items-center justify-between text-xs sm:text-xs font-bold text-gray-400 hover:text-white transition-colors">
                    System Settings <ArrowRight className="w-3 h-3 sm:w-3 sm:h-3" />
                </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Third Row: Activity Feed */}
      <div className="glass-card rounded-3xl p-4 sm:p-8">
          <div className="flex items-center justify-between mb-6 sm:mb-8">
            <div className="flex items-center gap-2 sm:gap-3">
              <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
              <h2 className="text-lg sm:text-xl font-bold text-white">Live Activity Feed</h2>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
                 <div className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-ping" />
                    <span className="text-[9px] sm:text-[10px] font-bold text-blue-400 uppercase">Live Streaming</span>
                 </div>
            </div>
          </div>
          
          <div className="space-y-3 sm:space-y-4">
            {activityFeed.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:gap-4">
                 {activityFeed.map((act: any, i) => (
                    <div key={act.id || i} className="flex items-start gap-3 sm:gap-4 p-3 sm:p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] transition-colors cursor-pointer group">
                        <div className="h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-blue-500/10 flex items-center justify-center group-hover:scale-110 transition-shrink-0 transform">
                           <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                           <p className="text-xs sm:text-sm font-medium text-white truncate capitalize">{act.action_type.replace(/_/g, ' ')}</p>
                           <p className="text-[9px] sm:text-xs text-gray-500">{formatTime(act.created_at)} • {act.platform || act.action_type}</p>
                        </div>
                        <span className={clsx("text-[8px] sm:text-[10px] font-bold px-2 py-1 rounded-md", act.success ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10')}>
                            {act.success ? "SUCCESS" : "FAILED"}
                        </span>
                    </div>
                 ))}
              </div>
            ) : (
              <div className="py-12 sm:py-20 text-center">
                <div className="mx-auto w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                  <BarChart className="h-6 w-6 sm:h-8 sm:w-8 text-gray-600" />
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