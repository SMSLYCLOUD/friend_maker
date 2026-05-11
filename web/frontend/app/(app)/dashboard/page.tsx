import { fetchAnalyticsSummary, fetchAccounts } from "@/lib/api";
import { Activity, Users, Target, CheckCircle2 } from "lucide-react";

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

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard</h1>
        <p className="text-sm text-gray-500">Real-time performance metrics for your automation fleet.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Actions", value: stats.total_actions, icon: Activity, color: "text-blue-500" },
          { label: "Actions Today", value: stats.today_actions, icon: Target, color: "text-purple-500" },
          { label: "Active Accounts", value: activeAccounts, icon: Users, color: "text-amber-500" },
          { label: "Success Rate", value: `${stats.success_rate}%`, icon: CheckCircle2, color: stats.success_rate >= 90 ? 'text-emerald-500' : stats.success_rate >= 70 ? 'text-yellow-500' : 'text-red-500' },
        ].map((item, i) => (
          <div key={i} className="group relative overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/40 p-6 transition-all hover:bg-gray-900 hover:border-gray-700">
            <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-white/5 blur-3xl group-hover:bg-white/10 transition-colors" />
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">{item.label}</h3>
              <item.icon className={`h-5 w-5 ${item.color} opacity-80`} />
            </div>
            <p className="mt-4 text-4xl font-bold tracking-tight text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}