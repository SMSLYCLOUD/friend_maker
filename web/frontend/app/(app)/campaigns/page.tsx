"use client";
import { useEffect, useState } from "react";
import { fetchCampaigns, createCampaign, startCampaign, stopCampaign, fetchAccounts } from "@/lib/api";
import { Plus, Play, Square, Loader2, Sparkles, Send } from "lucide-react";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [form, setForm] = useState({
    name: "",
    account_id: "",
    campaign_type: "outreach",
    message_template: "",
    ai_instructions: "",
    daily_limit: 50,
    targeting: { tags: [] },
    schedule: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start_time: "09:00", end_time: "18:00", timezone: "UTC" }
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cData, aData] = await Promise.all([fetchCampaigns(), fetchAccounts()]);
      setCampaigns(cData);
      setAccounts(aData);
      if (aData.length > 0 && !form.account_id) {
        setForm(prev => ({ ...prev, account_id: aData[0].id }));
      }
    } catch (err) {
      setError("Failed to load data. Backend might be offline.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const newC = await createCampaign(form);
      setCampaigns([newC, ...campaigns] as any);
      setForm({ ...form, name: "" }); // Reset name
    } catch (err) {
      setError("Failed to create campaign.");
    }
  };

  const handleToggleStatus = async (id: string, status: string) => {
    try {
      if (status === "active") {
        await stopCampaign(id);
      } else {
        await startCampaign(id);
      }
      loadData();
    } catch (err) {
      setError("Failed to update status.");
    }
  };

  if (loading) return <div className="flex items-center justify-center h-[400px]"><Loader2 className="animate-spin text-blue-500" /></div>;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Campaigns</h1>
          <p className="text-sm text-gray-500 mt-1">Design and deploy autonomous social media agents.</p>
        </div>
      </div>

      {error && <div className="p-4 bg-red-900/20 border border-red-800 text-red-400 rounded-xl text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-6">
              <Plus className="w-5 h-5 text-blue-500" />
              <h2 className="text-xl font-bold text-white">Create Campaign</h2>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Campaign Name</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                  placeholder="e.g. Summer Outreach"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Target Account</label>
                <select
                  value={form.account_id}
                  onChange={(e) => setForm({ ...form, account_id: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                >
                  {accounts.map((acc: any) => (
                    <option key={acc.id} value={acc.id}>{acc.username} ({acc.platform})</option>
                  ))}
                  {accounts.length === 0 && <option disabled>No accounts found</option>}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Campaign Type</label>
                <select
                  value={form.campaign_type}
                  onChange={(e) => setForm({ ...form, campaign_type: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
                >
                  <option value="outreach">Personalized Outreach</option>
                  <option value="growth">Audience Growth (Follow/Unfollow)</option>
                </select>
              </div>

              {form.campaign_type === "outreach" && (
                <>
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1">
                      <Sparkles className="w-3 h-3" /> AI Instructions
                    </label>
                    <textarea
                      value={form.ai_instructions}
                      onChange={(e) => setForm({ ...form, ai_instructions: e.target.value })}
                      className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all min-h-[100px] text-sm"
                      placeholder="e.g. Talk like a friendly tech enthusiast. Use casual language. Focus on the user's recent posts."
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1">
                      <Send className="w-3 h-3" /> Message Context
                    </label>
                    <textarea
                      value={form.message_template}
                      onChange={(e) => setForm({ ...form, message_template: e.target.value })}
                      className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all min-h-[80px] text-sm"
                      placeholder="e.g. I saw your recent post about [Topic] and loved the insight..."
                    />
                  </div>
                </>
              )}

              <button type="submit" className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all flex items-center justify-center gap-2">
                Save Campaign
              </button>
            </form>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm min-h-[400px]">
            <h2 className="text-xl font-bold text-white mb-6">Active Fleet</h2>
            
            {campaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-gray-600 italic">
                <p>No campaigns deployed. Start by creating one.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {campaigns.map((c: any) => (
                  <div key={c.id} className="group flex items-center gap-4 p-4 rounded-xl border border-gray-800 bg-black/50 hover:border-gray-700 transition-all">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-white">{c.name}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${c.status === 'active' ? 'bg-green-500/10 text-green-500 ring-1 ring-green-500/20' : 'bg-yellow-500/10 text-yellow-500 ring-1 ring-yellow-500/20'}`}>
                          {c.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-[11px] text-gray-500 font-medium">
                        <span className="capitalize">{c.campaign_type}</span>
                        <span>{c.daily_limit} actions/day</span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleToggleStatus(c.id, c.status)}
                      className={`p-3 rounded-full transition-all ${c.status === 'active' ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' : 'bg-green-500/10 text-green-500 hover:bg-green-500/20'}`}
                    >
                      {c.status === 'active' ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
