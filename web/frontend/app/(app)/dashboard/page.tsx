import { fetchAnalyticsSummary, fetchAccounts } from "@/lib/api";

export default async function Dashboard() {
  let stats = { total_actions: 0, today_actions: 0, success_rate: 0 };
  let accounts = [];

  try {
    stats = await fetchAnalyticsSummary();
    accounts = await fetchAccounts();
  } catch (err) {
    console.error("Failed to load dashboard stats", err);
    // Silent fail for demo purposes, UI will show 0s
  }

  const activeAccounts = accounts.filter((a: any) => a.is_active).length;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-400">Total Actions</h3>
          <p className="mt-2 text-3xl font-bold">{stats.total_actions}</p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-400">Actions Today</h3>
          <p className="mt-2 text-3xl font-bold">{stats.today_actions}</p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-400">Active Accounts</h3>
          <p className="mt-2 text-3xl font-bold">{activeAccounts}</p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-400">Success Rate</h3>
          <p className={`mt-2 text-3xl font-bold ${stats.success_rate >= 90 ? 'text-emerald-500' : stats.success_rate >= 70 ? 'text-yellow-500' : 'text-red-500'}`}>
            {stats.success_rate}%
          </p>
        </div>
      </div>
    </div>
  );
}