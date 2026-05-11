"use client";
import { useState, useEffect } from "react";
import { Plus, Facebook, Instagram, Twitter, Linkedin, Smartphone } from "lucide-react";

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
        .catch(() => setError("Unable to reach backend API. Check NEXT_PUBLIC_API_URL or BACKEND_API_URL."));
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
      setError("Unable to create account right now. Backend may be unavailable.");
    }
  };

  const getIcon = (platform: string) => {
    switch (platform) {
      case "facebook": return <Facebook className="w-5 h-5 text-blue-600" />;
      case "instagram": return <Instagram className="w-5 h-5 text-pink-600" />;
      case "twitter": return <Twitter className="w-5 h-5 text-blue-400" />;
      case "linkedin": return <Linkedin className="w-5 h-5 text-blue-700" />;
      case "android": return <Smartphone className="w-5 h-5 text-green-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Accounts</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" /> Add Account
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-900/40 bg-red-900/20 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acc: any) => (
          <div key={acc.id} className="group relative rounded-xl border border-gray-800 bg-gray-900/50 p-6 flex items-center gap-4 hover:border-blue-500/50 transition-all hover:bg-gray-900">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />
            <div className="relative rounded-full bg-gray-800 p-3 ring-1 ring-gray-700 group-hover:ring-blue-500/50 transition-all">
              {getIcon(acc.platform)}
            </div>
            <div className="relative">
              <h3 className="font-medium text-white">{acc.username}</h3>
              <p className="text-xs text-gray-400 capitalize">{acc.platform}</p>
            </div>
            <div className="relative ml-auto flex flex-col items-end gap-1">
              <div className={`h-2 w-2 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.6)] ${acc.is_active ? "bg-green-500" : "bg-red-500"}`} />
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">{acc.is_active ? "Active" : "Disabled"}</span>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl bg-gray-900 p-6 border border-gray-800">
            <h2 className="mb-4 text-xl font-bold">Add New Account</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Platform</label>
                <select
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all border border-gray-700 focus:border-blue-500/50"
                  value={formData.platform}
                  onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                >
                  <option value="instagram">Instagram</option>
                  <option value="twitter">Twitter / X</option>
                  <option value="facebook">Facebook</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="android">Android App</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Username</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. janesmith_ai"
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all border border-gray-700 focus:border-blue-500/50"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Password</label>
                <input
                  type="password"
                  placeholder="Enter social media password"
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all border border-gray-700 focus:border-blue-500/50"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
                <p className="mt-1 text-[10px] text-gray-500">Stored encrypted for secure browser automation.</p>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-700"
                >
                  Add Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
