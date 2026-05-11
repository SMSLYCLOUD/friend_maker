"use client";
import { useState, useEffect } from "react";
import { Plus, Facebook, Instagram, Twitter, Linkedin, Smartphone, ShieldCheck, ShieldAlert, MoreVertical, Trash2 } from "lucide-react";
import clsx from "clsx";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ platform: "instagram", username: "", password: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    import("@/lib/api").then(({ fetchAccounts }) => {
      fetchAccounts()
        .then((data) => {
          setAccounts(data);
          setError("");
        })
        .catch(() => setError("Unable to reach backend API. Check connectivity."));
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const { createAccount } = await import("@/lib/api");
      const newAccount = await createAccount(formData);
      setAccounts([...accounts, newAccount] as any);
      setShowModal(false);
      setFormData({ platform: "instagram", username: "", password: "" });
    } catch (err) {
      setError("Unable to create account. Backend error.");
    }
  };

  const getIcon = (platform: string) => {
    switch (platform) {
      case "facebook": return <Facebook className="w-5 h-5 text-blue-500" />;
      case "instagram": return <Instagram className="w-5 h-5 text-pink-500" />;
      case "twitter": return <Twitter className="w-5 h-5 text-blue-400" />;
      case "linkedin": return <Linkedin className="w-5 h-5 text-blue-600" />;
      case "android": return <Smartphone className="w-5 h-5 text-emerald-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-4xl font-black tracking-tight text-white">
            Social <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-500">Nodes</span>
          </h1>
          <p className="text-gray-500">Manage your autonomous agents across global platforms.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="group flex items-center gap-2 rounded-2xl bg-blue-600 px-6 py-3 text-sm font-bold text-white transition-all hover:bg-blue-500 hover:scale-105 active:scale-95 shadow-lg shadow-blue-600/20"
        >
          <Plus className="w-5 h-5 transition-transform group-hover:rotate-90" /> 
          Add Account
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400 animate-in fade-in slide-in-from-top-4">
          <ShieldAlert className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acc: any) => (
          <div key={acc.id} className="group glass-card p-6 rounded-3xl relative overflow-hidden transition-all duration-300">
            <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/5 blur-2xl group-hover:bg-white/10 transition-all" />
            
            <div className="flex items-start justify-between mb-4 relative z-10">
              <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10 group-hover:ring-blue-500/30 transition-all">
                {getIcon(acc.platform)}
              </div>
              <div className="flex items-center gap-2">
                <div className={clsx("h-2 w-2 rounded-full", acc.is_active ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500")} />
                <span className={clsx("text-[10px] font-bold uppercase tracking-widest", acc.is_active ? "text-emerald-500" : "text-red-500")}>
                  {acc.is_active ? "Active" : "Disabled"}
                </span>
              </div>
            </div>

            <div className="relative z-10">
              <h3 className="text-lg font-bold text-white truncate max-w-full" title={acc.username}>
                {acc.username}
              </h3>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mt-1 flex items-center gap-2">
                {acc.platform} 
                <span className="h-1 w-1 rounded-full bg-gray-700" /> 
                <span className="text-blue-500">Node Ready</span>
              </p>
            </div>

            <div className="mt-8 flex items-center justify-between pt-6 border-t border-white/5 relative z-10">
               <div className="flex -space-x-2">
                  <div className="h-7 w-7 rounded-full border-2 border-black bg-gray-800 flex items-center justify-center text-[8px] font-bold text-white">AI</div>
                  <div className="h-7 w-7 rounded-full border-2 border-black bg-blue-600 flex items-center justify-center text-[8px] font-bold text-white">V2</div>
               </div>
               <div className="flex gap-2">
                  <button className="p-2 rounded-lg hover:bg-white/5 text-gray-500 hover:text-white transition-colors">
                    <Settings className="w-4 h-4" />
                  </button>
                  <button className="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
               </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-300">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-xl" onClick={() => setShowModal(false)} />
          <div className="relative w-full max-w-lg rounded-[2.5rem] glass border border-white/10 p-10 shadow-3xl overflow-hidden">
            <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-blue-600/10 blur-[80px]" />
            <div className="relative z-10">
              <h2 className="text-3xl font-black text-white mb-2">Initialize <span className="text-blue-500">Node</span></h2>
              <p className="text-gray-500 mb-8">Deploy a new autonomous agent to your fleet.</p>
              
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Select Platform</label>
                  <select
                    className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all appearance-none"
                    value={formData.platform}
                    onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                  >
                    <option value="instagram" className="bg-gray-950">Instagram</option>
                    <option value="twitter" className="bg-gray-950">Twitter / X</option>
                    <option value="facebook" className="bg-gray-950">Facebook</option>
                    <option value="linkedin" className="bg-gray-950">LinkedIn</option>
                    <option value="tiktok" className="bg-gray-950">TikTok</option>
                    <option value="android" className="bg-gray-950">Android App</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Identity (Username/Email)</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. janesmith_ai"
                    className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Security (Password)</label>
                  <input
                    type="password"
                    placeholder="Enter security key"
                    className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>

                <div className="flex gap-4 pt-6">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 rounded-2xl border border-white/10 py-4 text-sm font-bold text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
                  >
                    Abort
                  </button>
                  <button
                    type="submit"
                    className="flex-1 rounded-2xl bg-blue-600 py-4 text-sm font-bold text-white transition-all hover:bg-blue-500 hover:scale-[1.02] shadow-lg shadow-blue-600/20"
                  >
                    Deploy Node
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Fixed missing Settings import
import { Settings } from "lucide-react";
