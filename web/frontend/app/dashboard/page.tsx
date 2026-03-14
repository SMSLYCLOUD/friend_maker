export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Stats Cards */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h3 className="text-sm font-medium text-gray-400">Total Actions</h3>
          <p className="mt-2 text-3xl font-bold">1,234</p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h3 className="text-sm font-medium text-gray-400">Active Accounts</h3>
          <p className="mt-2 text-3xl font-bold">5</p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h3 className="text-sm font-medium text-gray-400">Success Rate</h3>
          <p className="mt-2 text-3xl font-bold text-green-500">98.2%</p>
        </div>
      </div>
    </div>
  );
}