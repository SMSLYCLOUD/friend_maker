"use client";
import { useState, useEffect } from "react";
import { Plus, Facebook, Instagram, Twitter, Linkedin } from "lucide-react";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ platform: "instagram", username: "" });

  useEffect(() => {
    import("@/lib/api").then(({ fetchAccounts }) => {
      fetchAccounts()
        .then((data) => setAccounts(data))
        .catch((err) => console.error(err));
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const { createAccount } = await import("@/lib/api");
      const newAccount = await createAccount(formData);
      setAccounts([...accounts, newAccount] as any);
      setShowModal(false);
      setFormData({ platform: "instagram", username: "" });
    } catch (err) {
      console.error(err);
    }
  };

  const getIcon = (platform: string) => {
    switch (platform) {
      case "facebook": return <Facebook className="w-5 h-5 text-blue-600" />;
      case "instagram": return <Instagram className="w-5 h-5 text-pink-600" />;
      case "twitter": return <Twitter className="w-5 h-5 text-blue-400" />;
      case "linkedin": return <Linkedin className="w-5 h-5 text-blue-700" />;
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

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acc: any) => (
          <div key={acc.id} className="rounded-xl border border-gray-800 bg-gray-900 p-6 flex items-center gap-4">
            <div className="rounded-full bg-gray-800 p-3">
              {getIcon(acc.platform)}
            </div>
            <div>
              <h3 className="font-medium">{acc.username}</h3>
              <p className="text-sm text-gray-400 capitalize">{acc.platform}</p>
            </div>
            <div className={`ml-auto h-2 w-2 rounded-full ${acc.is_active ? "bg-green-500" : "bg-red-500"}`} />
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl bg-gray-900 p-6 border border-gray-800">
            <h2 className="mb-4 text-xl font-bold">Add New Account</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-400">Platform</label>
                <select
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-600"
                  value={formData.platform}
                  onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                >
                  <option value="instagram">Instagram</option>
                  <option value="twitter">Twitter / X</option>
                  <option value="facebook">Facebook</option>
                  <option value="linkedin">LinkedIn</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-400">Username</label>
                <input
                  type="text"
                  required
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-600"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                />
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
