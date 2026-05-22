"use client";
import { useState, useEffect } from "react";
import { Plus, Facebook, Instagram, Twitter, Linkedin, Smartphone, ShieldCheck, ShieldAlert, Trash2, X, Settings, Mail, ExternalLink, Save } from "lucide-react";
import clsx from "clsx";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ platform: "instagram", username: "", password: "" });
  const [error, setError] = useState("");
  const [selectedAccount, setSelectedAccount] = useState<any>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [vncMsg, setVncMsg] = useState("");
  const [vncPolling, setVncPolling] = useState(false);

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

  useEffect(() => {
    if (!vncPolling || !selectedAccount) return;
    const interval = setInterval(async () => {
      try {
        const { vncSessionStatus, captureCookies, fetchAccounts } = await import("@/lib/api");
        const status = await vncSessionStatus(selectedAccount.id);
        if (status.login_detected && !status.has_session) {
          const result = await captureCookies(selectedAccount.id);
          setVncMsg(result.message || "Session saved!");
          setVncPolling(false);
          const updated = await fetchAccounts();
          setAccounts(updated);
          setSelectedAccount((prev: any) => ({ ...prev, has_session: true }));
        } else if (status.has_session) {
          setVncMsg("Already connected!");
          setVncPolling(false);
        }
      } catch {
        setVncMsg("Waiting for login...");
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [vncPolling, selectedAccount?.id]);

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

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this account?")) return;
    try {
      const { deleteAccount } = await import("@/lib/api");
      await deleteAccount(id);
      setAccounts(accounts.filter((a: any) => a.id !== id));
    } catch (err) {
      setError("Failed to delete account.");
    }
  };

  const handleVncLogin = async (accountId: string) => {
    setVncMsg("Launching VNC browser...");
    try {
      const { vncLogin } = await import("@/lib/api");
      const data = await vncLogin(accountId);
      window.open(data.vnc_url, "_blank");
      setVncMsg(`Sign in to ${data.platform || "platform"} in the VNC tab...`);
      setVncPolling(true);
    } catch (err: any) {
      setVncMsg(err.message || "Failed");
    }
  };

  const handleCaptureCookies = async (accountId: string) => {
    setVncMsg("Capturing cookies...");
    try {
      const { captureCookies, fetchAccounts } = await import("@/lib/api");
      const data = await captureCookies(accountId);
      setVncMsg(data.message);
      const updated = await fetchAccounts();
      setAccounts(updated);
      setSelectedAccount((prev: any) => prev?.id === accountId ? { ...prev, has_session: true } : prev);
    } catch (err: any) {
      setVncMsg(err.message || "Failed");
    }
  };

  const getIcon = (platform: string) => {
    switch (platform) {
      case "facebook": return <Facebook className="w-5 h-5 text-blue-500" />;
      case "instagram": return <Instagram className="w-5 h-5 text-pink-500" />;
      case "twitter": return <Twitter className="w-5 h-5 text-blue-400" />;
      case "linkedin": return <Linkedin className="w-5 h-5 text-blue-600" />;
      case "gmail": return <Mail className="w-5 h-5 text-red-400" />;

      default: return null;
    }
  };

  return (
    <div className="space-y-6 sm:space-y-10 pb-6 sm:pb-20">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-white">
            Social <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-500">Nodes</span>
          </h1>
          <p className="text-gray-500 text-sm sm:text-base">Manage your autonomous agents across global platforms.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="group flex items-center gap-2 rounded-2xl bg-blue-600 px-4 sm:px-6 py-3 text-sm font-bold text-white transition-all hover:bg-blue-500 hover:scale-105 active:scale-95 shadow-lg shadow-blue-600/20 touch-manipulation w-full sm:w-auto justify-center"
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

      {vncMsg && (
        <div className="flex items-center gap-3 rounded-2xl border border-blue-500/20 bg-blue-500/10 p-4 text-sm text-blue-400">
          <ExternalLink className="w-5 h-5" />
          {vncMsg}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acc: any) => (
          <div key={acc.id} className="group glass-card p-4 sm:p-6 rounded-3xl relative overflow-hidden transition-all duration-300">
            <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/5 blur-2xl group-hover:bg-white/10 transition-all" />
            
            <div className="flex items-start justify-between mb-3 sm:mb-4 relative z-10">
              <div className="rounded-2xl bg-white/5 p-3 sm:p-4 ring-1 ring-white/10 group-hover:ring-blue-500/30 transition-all touch-manipulation">
                {getIcon(acc.platform)}
              </div>
              <div className="flex items-center gap-2">
                <div className={clsx("h-2 w-2 rounded-full", acc.is_active ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500")} />
                <span className={clsx("text-[9px] sm:text-[10px] font-bold uppercase tracking-widest", acc.is_active ? "text-emerald-500" : "text-red-500")}>
                  {acc.is_active ? "Active" : "Disabled"}
                </span>
              </div>
            </div>

            <div className="relative z-10">
              <h3 className="text-base sm:text-lg font-bold text-white truncate max-w-full" title={acc.username}>
                {acc.username}
              </h3>
              <p className="text-[9px] sm:text-xs font-bold text-gray-500 uppercase tracking-widest mt-1 flex items-center gap-2">
                {acc.platform} 
                <span className="h-1 w-1 rounded-full bg-gray-700" /> 
                {acc.has_session ? (
                  <span className="text-emerald-500">Connected</span>
                ) : (
                  <span className="text-yellow-500">Needs Setup</span>
                )}
              </p>
            </div>

            <div className="mt-6 sm:mt-8 flex items-center justify-between pt-4 sm:pt-6 border-t border-white/5 relative z-10">
               <div className="flex -space-x-2">
                  <div className="h-7 w-7 rounded-full border-2 border-black bg-gray-800 flex items-center justify-center text-[8px] font-bold text-white">AI</div>
                  <div className="h-7 w-7 rounded-full border-2 border-black bg-blue-600 flex items-center justify-center text-[8px] font-bold text-white">V2</div>
               </div>
               <div className="flex gap-2">
                   <button onClick={() => { setSelectedAccount(acc); setShowDetailModal(true); }} className="p-3 sm:p-2 rounded-xl sm:rounded-lg hover:bg-white/5 text-gray-500 hover:text-white transition-colors touch-manipulation">
                     <Settings className="w-5 h-5 sm:w-4 sm:h-4" />
                   </button>
                   <button onClick={() => handleDelete(acc.id)} className="p-3 sm:p-2 rounded-xl sm:rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-colors touch-manipulation">
                     <Trash2 className="w-5 h-5 sm:w-4 sm:h-4" />
                   </button>
                </div>
            </div>
          </div>
        ))}
      </div>

      {showDetailModal && selectedAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-300">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-xl" onClick={() => setShowDetailModal(false)} />
          <div className="relative w-full max-w-lg max-h-[90vh] rounded-[2.5rem] glass border border-white/10 p-6 shadow-3xl overflow-y-auto">
            <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-blue-600/10 blur-[80px]" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-black text-white">Node <span className="text-blue-500">Details</span></h2>
                 <button onClick={() => { setShowDetailModal(false); setVncMsg(""); }} className="p-3 sm:p-2 rounded-xl sm:rounded-lg hover:bg-white/5 text-gray-500 hover:text-white transition-colors touch-manipulation">
                   <X className="w-6 h-6 sm:w-5 sm:h-5" />
                 </button>
              </div>
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Username</p>
                  <p className="text-white font-bold">{selectedAccount.username}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Platform</p>
                  <p className="text-white font-bold capitalize">{selectedAccount.platform}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Status</p>
                  <p className={`font-bold ${selectedAccount.is_active ? "text-emerald-400" : "text-red-400"}`}>
                    {selectedAccount.is_active ? "Active" : "Disabled"}
                  </p>
                </div>
                {selectedAccount.has_session ? (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-1">Session</p>
                    <p className="text-emerald-400 font-bold">Cookies stored ✓</p>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                    <p className="text-[10px] font-bold text-yellow-400 uppercase tracking-wider mb-1">Session</p>
                    <p className="text-yellow-400 font-bold">Not yet connected</p>
                  </div>
                )}
                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Account ID</p>
                  <p className="text-gray-400 text-sm font-mono">{selectedAccount.id}</p>
                </div>
              </div>

              {!selectedAccount.has_session && !vncPolling && (
                <div className="mt-4 space-y-2">
                   <button
                     onClick={() => handleVncLogin(selectedAccount.id)}
                     className="w-full rounded-xl bg-purple-600 py-3 text-sm font-bold text-white transition-all hover:bg-purple-500 flex items-center justify-center gap-2 touch-manipulation"
                   >
                     <ExternalLink className="w-4 h-4" /> Sign in via VNC
                   </button>
                   <button
                     onClick={() => handleCaptureCookies(selectedAccount.id)}
                     className="w-full rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white transition-all hover:bg-emerald-500 flex items-center justify-center gap-2 touch-manipulation"
                   >
                     <Save className="w-4 h-4" /> Capture Cookies Now
                   </button>
                </div>
              )}

              {!selectedAccount.has_session && vncPolling && (
                <div className="mt-4 space-y-2">
                  <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-center">
                    <p className="text-purple-400 font-bold animate-pulse text-sm">Waiting for {selectedAccount.platform} login...</p>
                    <p className="text-xs text-gray-400 mt-1">Complete sign-in in the VNC tab.</p>
                  </div>
                   <button
                     onClick={() => { setVncPolling(false); setVncMsg(""); }}
                     className="w-full rounded-xl border border-white/10 py-3 text-sm font-bold text-gray-400 hover:text-white transition-colors touch-manipulation"
                   >
                     Cancel
                   </button>
                </div>
              )}

              {selectedAccount.has_session && (
                <div className="mt-4 space-y-2">
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                    <p className="text-emerald-400 font-bold text-sm">Connected ✓</p>
                    <p className="text-xs text-gray-400 mt-1">{selectedAccount.platform} session is active</p>
                  </div>
                   <button
                     onClick={() => handleVncLogin(selectedAccount.id)}
                     className="w-full rounded-xl bg-purple-600/50 py-3 text-sm font-bold text-white transition-all hover:bg-purple-500 flex items-center justify-center gap-2 touch-manipulation"
                   >
                     <ExternalLink className="w-4 h-4" /> Re-sign in via VNC
                   </button>
                   <button
                     onClick={() => handleCaptureCookies(selectedAccount.id)}
                     className="w-full rounded-xl bg-emerald-600/50 py-3 text-sm font-bold text-white transition-all hover:bg-emerald-500 flex items-center justify-center gap-2 touch-manipulation"
                   >
                     <Save className="w-4 h-4" /> Re-capture Cookies
                   </button>
                </div>
              )}

               <button
                 onClick={() => { setShowDetailModal(false); setVncMsg(""); }}
                 className="w-full mt-4 rounded-xl bg-blue-600 py-3 text-sm font-bold text-white transition-all hover:bg-blue-500 touch-manipulation"
               >
                 Close
               </button>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-300">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-xl" onClick={() => setShowModal(false)} />
          <div className="relative w-full max-w-lg max-h-[90vh] rounded-[2.5rem] glass border border-white/10 p-6 shadow-3xl overflow-y-auto">
            <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-blue-600/10 blur-[80px]" />
            <div className="relative z-10">
              <h2 className="text-2xl font-black text-white mb-1">Initialize <span className="text-blue-500">Node</span></h2>
              <p className="text-gray-500 mb-6">Deploy a new autonomous agent to your fleet.</p>
              
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Select Platform</label>
                   <select
                     className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all appearance-none touch-manipulation"
                     value={formData.platform}
                     onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                   >
                    <option value="instagram" className="bg-gray-950">Instagram</option>
                    <option value="twitter" className="bg-gray-950">Twitter / X</option>
                    <option value="facebook" className="bg-gray-950">Facebook</option>
                    <option value="linkedin" className="bg-gray-950">LinkedIn</option>
                    <option value="gmail" className="bg-gray-950">Gmail</option>
                    <option value="tiktok" className="bg-gray-950">TikTok</option>

                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Identity (Username/Email)</label>
                   <input
                     type={formData.platform === "gmail" ? "email" : "text"}
                     required
                     placeholder={formData.platform === "gmail" ? "e.g. janesmith@gmail.com" : "e.g. janesmith_ai"}
                     className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all touch-manipulation"
                     value={formData.username}
                     onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                   />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] ml-2">Security (Password)</label>
                   <input
                     type="password"
                     placeholder="Enter security key"
                     className="w-full rounded-2xl bg-white/5 px-5 py-4 text-white outline-none ring-1 ring-white/10 focus:ring-2 focus:ring-blue-500 transition-all touch-manipulation"
                     value={formData.password}
                     onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                   />
                </div>

                <div className="flex gap-3 pt-4">
                   <button
                     type="button"
                     onClick={() => setShowModal(false)}
                     className="flex-1 rounded-xl border border-white/10 py-3 text-sm font-bold text-gray-400 transition-colors hover:bg-white/5 hover:text-white touch-manipulation"
                   >
                     Abort
                   </button>
                   <button
                     type="submit"
                     className="flex-1 rounded-xl bg-blue-600 py-3 text-sm font-bold text-white transition-all hover:bg-blue-500 hover:scale-[1.02] shadow-lg shadow-blue-600/20 touch-manipulation"
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