"use client";
import { useEffect, useState } from "react";
import {
  fetchCampaigns, createCampaign, startCampaign, stopCampaign, deleteCampaign, fetchAccounts,
  triggerEmailCampaign, triggerPlatform, triggerAllPlatforms, fetchPlatforms,
} from "@/lib/api";
import { Plus, Play, Square, Loader2, Sparkles, Send, Mail, Globe, Boxes, FileText, ArrowLeft, ArrowRight, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import Link from "next/link";

const ICONS: Record<string, any> = {
  instagram: Globe, tiktok: Globe, substack: Globe, notarycafe: Globe, rotary: Globe, "notary-sites": FileText,
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [triggerStates, setTriggerStates] = useState<Record<string, string>>({});
  const [triggerZip, setTriggerZip] = useState("");
  const [triggerBusiness, setTriggerBusiness] = useState("");
  const [expandedCampaign, setExpandedCampaign] = useState<string | null>(null);

  const setTriggerState = (key: string, msg: string) => {
    setTriggerStates(prev => ({ ...prev, [key]: msg }));
  };

  const handleTriggerEmail = async () => {
    setTriggerState("email", "Starting...");
    try {
      const r = await triggerEmailCampaign();
      setTriggerState("email", r.message || "Started");
    } catch (e: any) {
      setTriggerState("email", e.message || "Failed");
    }
    setTimeout(() => setTriggerState("email", ""), 5000);
  };

  const handleTriggerPlatform = async (platform: string, zip?: string, biz?: string) => {
    setTriggerState(platform, "Starting...");
    try {
      const r = await triggerPlatform(platform, zip || undefined, biz || undefined);
      setTriggerState(platform, r.message || "Started");
    } catch (e: any) {
      setTriggerState(platform, e.message || "Failed");
    }
    setTimeout(() => setTriggerState(platform, ""), 5000);
  };

  const handleTriggerAll = async () => {
    setTriggerState("all", "Starting all...");
    try {
      const r = await triggerAllPlatforms();
      setTriggerState("all", r.message || "Started");
    } catch (e: any) {
      setTriggerState("all", e.message || "Failed");
    }
    setTimeout(() => setTriggerState("all", ""), 5000);
  };

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
    fetchPlatforms().then(r => setPlatforms(r.platforms || [])).catch(() => {});
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
      setForm({ ...form, name: "" });
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

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this campaign?")) return;
    try {
      await deleteCampaign(id);
      loadData();
    } catch (err) {
      setError("Failed to delete campaign.");
    }
  };

  if (loading) return <div className="flex items-center justify-center h-[400px]"><Loader2 className="animate-spin text-blue-500" /></div>;

  return (
    <div className="space-y-6 sm:space-y-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Campaigns</h1>
          <p className="text-sm text-gray-500 mt-1">Design and deploy autonomous social media agents.</p>
        </div>
        <Link href="/dashboard" className="flex items-center gap-2 rounded-xl border border-gray-800 px-4 py-2.5 text-xs font-bold text-gray-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap touch-manipulation">
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </Link>
      </div>

      {error && <div className="p-4 bg-red-900/20 border border-red-800 text-red-400 rounded-xl text-sm">{error}</div>}

       <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
         <div className="lg:col-span-1 space-y-6">
           <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-4 sm:p-6 backdrop-blur-sm max-h-[calc(100vh-12rem)] overflow-y-auto">
             <div className="flex items-center gap-2 mb-6">
               <Plus className="w-5 h-5 text-blue-500" />
               <h2 className="text-lg sm:text-xl font-bold text-white">Create Campaign</h2>
             </div>
            
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Campaign Name</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all touch-manipulation"
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
                      placeholder="e.g. Talk like a friendly tech enthusiast."
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1">
                      <Send className="w-3 h-3" /> Message Context
                    </label>
                    <textarea
                      value={form.message_template}
                      onChange={(e) => setForm({ ...form, message_template: e.target.value })}
                       className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all min-h-[80px] text-sm touch-manipulation"
                       placeholder="e.g. I saw your recent post about [Topic]..."
                     />
                  </div>
                </>
              )}

               <button type="submit" className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all flex items-center justify-center gap-2 touch-manipulation">
                 Save Campaign
               </button>
            </form>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-4">
              <Boxes className="w-5 h-5 text-purple-500" />
              <h2 className="text-xl font-bold text-white">Automation Triggers</h2>
            </div>
            <div className="space-y-3">
              <button onClick={handleTriggerEmail} className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 touch-manipulation">
                <Mail className="w-4 h-4" /> Trigger Email Campaign
              </button>
              {triggerStates["email"] && (
                <p className="text-xs text-gray-400 text-center">{triggerStates["email"]}</p>
              )}

              <div className="border-t border-gray-800 pt-3 space-y-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Platform Scripts</p>
                {platforms.map(p => {
                  const Icon = ICONS[p] || Globe;
                  return (
                    <div key={p}>
                      <button onClick={() => handleTriggerPlatform(p, triggerZip, triggerBusiness)} className="w-full py-3 sm:py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl sm:rounded-lg text-sm transition-all flex items-center justify-center gap-2 capitalize touch-manipulation">
                        <Icon className="w-4 h-4" /> Run {p}
                      </button>
                      {p === "rotary" && (
                        <div className="mt-2 space-y-1.5">
                          <input
                            type="text"
                            placeholder="Zip code"
                            value={triggerZip}
                            onChange={e => setTriggerZip(e.target.value)}
                            className="w-full px-3 py-2 text-xs bg-gray-800 rounded-xl sm:rounded-lg border border-gray-700 text-white placeholder-gray-500 touch-manipulation"
                          />
                          <input
                            type="text"
                            placeholder="Business type"
                            value={triggerBusiness}
                            onChange={e => setTriggerBusiness(e.target.value)}
                            className="w-full px-3 py-2 text-xs bg-gray-800 rounded-xl sm:rounded-lg border border-gray-700 text-white placeholder-gray-500 touch-manipulation"
                          />
                        </div>
                      )}
                      {triggerStates[p] && <p className="text-xs text-gray-400 text-center mt-1">{triggerStates[p]}</p>}
                    </div>
                  );
                })}
              </div>

               {platforms.length > 0 && (
                 <div className="border-t border-gray-800 pt-3">
                   <button onClick={handleTriggerAll} className="w-full py-3 sm:py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl sm:rounded-lg text-sm transition-all flex items-center justify-center gap-2 touch-manipulation">
                     <Boxes className="w-4 h-4" /> Run All Platforms
                   </button>
                   {triggerStates["all"] && <p className="text-xs text-gray-400 text-center mt-1">{triggerStates["all"]}</p>}
                 </div>
               )}
            </div>
          </div>
        </div>

         <div className="lg:col-span-2 space-y-6">
           <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-4 sm:p-6 backdrop-blur-sm min-h-[400px]">
             <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
               <h2 className="text-lg sm:text-xl font-bold text-white">Active Fleet</h2>
               <Link href="/accounts" className="text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1 touch-manipulation">
                 Manage Nodes <ArrowRight className="w-3 h-3" />
               </Link>
             </div>
            
            {campaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-gray-600 italic">
                <p>No campaigns deployed. Create one using the form to start.</p>
              </div>
            ) : (
               <div className="grid grid-cols-1 gap-3 sm:gap-4">
                 {campaigns.map((c: any) => (
                   <div key={c.id} className="rounded-xl border border-gray-800 bg-black/50 hover:border-gray-700 transition-all">
                     <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 p-3 sm:p-4">
                       <div className="flex-1 min-w-0">
                         <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-2">
                           <h3 className="font-bold text-white truncate">{c.name}</h3>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase whitespace-nowrap ${c.status === 'active' ? 'bg-green-500/10 text-green-500 ring-1 ring-green-500/20' : 'bg-yellow-500/10 text-yellow-500 ring-1 ring-yellow-500/20'}`}>
                             {c.status}
                           </span>
                         </div>
                         <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mt-1 text-[10px] sm:text-[11px] text-gray-500 font-medium">
                           <span className="capitalize">{c.campaign_type}</span>
                           <span>{c.daily_limit} actions/day</span>
                         </div>
                      </div>
                        <div className="flex items-center gap-1">
                          {(c.ai_instructions || c.message_template) && (
                            <button onClick={() => setExpandedCampaign(expandedCampaign === c.id ? null : c.id)} className="p-3 sm:p-2 rounded-xl sm:rounded-lg hover:bg-white/5 text-gray-500 hover:text-white transition-colors touch-manipulation">
                              {expandedCampaign === c.id ? <ChevronUp className="w-5 h-5 sm:w-4 sm:h-4" /> : <ChevronUp className="w-5 h-5 sm:w-4 sm:h-4" />}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(c.id)}
                            className="p-4 sm:p-3 rounded-xl sm:rounded-full bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-all touch-manipulation"
                          >
                            <Trash2 className="w-5 h-5 sm:w-4 sm:h-4" />
                          </button>
                          <button
                            onClick={() => handleToggleStatus(c.id, c.status)}
                            className={`p-4 sm:p-3 rounded-xl sm:rounded-full transition-all touch-manipulation ${c.status === 'active' ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' : 'bg-green-500/10 text-green-500 hover:bg-green-500/20'}`}
                          >
                            {c.status === 'active' ? <Square className="w-5 h-5 sm:w-4 sm:h-4" /> : <Play className="w-5 h-5 sm:w-4 sm:h-4" />}
                          </button>
                        </div>
                    </div>
                     {expandedCampaign === c.id && (
                       <div className="px-3 sm:px-4 pb-3 sm:pb-4 pt-0 border-t border-gray-800/50 space-y-2">
                         {c.ai_instructions && (
                            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
                              <p className="text-[10px] font-bold text-purple-400 uppercase tracking-wider mb-1">AI Instructions</p>
                             <p className="text-xs text-gray-300 whitespace-pre-wrap">{c.ai_instructions}</p>
                           </div>
                         )}
                         {c.message_template && (
                            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
                              <p className="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-1">Message Template</p>
                             <p className="text-xs text-gray-300 whitespace-pre-wrap">{c.message_template}</p>
                           </div>
                         )}
                       </div>
                     )}
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
