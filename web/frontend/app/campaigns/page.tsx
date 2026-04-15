"use client";

import { FormEvent, useState } from "react";

type Campaign = {
  id: string;
  name: string;
  platform: string;
  objective: string;
  dailyLimit: number;
  status: "draft" | "active";
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [form, setForm] = useState({
    name: "",
    platform: "instagram",
    objective: "outreach",
    dailyLimit: 50,
  });

  const createCampaign = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const campaign: Campaign = {
      id: crypto.randomUUID(),
      name: form.name,
      platform: form.platform,
      objective: form.objective,
      dailyLimit: Number(form.dailyLimit),
      status: "draft",
    };
    setCampaigns((prev) => [campaign, ...prev]);
    setForm({ name: "", platform: "instagram", objective: "outreach", dailyLimit: 50 });
  };

  const activateCampaign = (id: string) => {
    setCampaigns((prev) => prev.map((c) => (c.id === id ? { ...c, status: "active" } : c)));
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Campaigns</h1>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h2 className="mb-4 text-xl font-semibold">Create campaign</h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={createCampaign}>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm text-gray-300">Campaign name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
              placeholder="Q2 Growth Outreach"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-gray-300">Platform</label>
            <select
              value={form.platform}
              onChange={(e) => setForm((prev) => ({ ...prev, platform: e.target.value }))}
              className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
            >
              <option value="instagram">Instagram</option>
              <option value="twitter">Twitter / X</option>
              <option value="linkedin">LinkedIn</option>
              <option value="facebook">Facebook</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm text-gray-300">Objective</label>
            <select
              value={form.objective}
              onChange={(e) => setForm((prev) => ({ ...prev, objective: e.target.value }))}
              className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
            >
              <option value="outreach">Outreach</option>
              <option value="growth">Audience growth</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm text-gray-300">Daily limit</label>
            <input
              type="number"
              min={1}
              max={500}
              value={form.dailyLimit}
              onChange={(e) => setForm((prev) => ({ ...prev, dailyLimit: Number(e.target.value) }))}
              className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
            />
          </div>

          <div className="md:col-span-2">
            <button type="submit" className="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-500">
              Save campaign
            </button>
          </div>
        </form>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h2 className="mb-4 text-xl font-semibold">Campaign list</h2>
        {campaigns.length === 0 ? (
          <p className="text-gray-400">No campaigns yet. Create your first campaign above.</p>
        ) : (
          <div className="space-y-3">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-800 bg-gray-950 p-4">
                <div className="min-w-[220px]">
                  <p className="font-medium">{campaign.name}</p>
                  <p className="text-sm text-gray-400">
                    {campaign.platform} • {campaign.objective} • {campaign.dailyLimit}/day
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-semibold ${
                    campaign.status === "active" ? "bg-emerald-900/40 text-emerald-300" : "bg-yellow-900/40 text-yellow-300"
                  }`}
                >
                  {campaign.status}
                </span>
                {campaign.status === "draft" && (
                  <button
                    onClick={() => activateCampaign(campaign.id)}
                    className="ml-auto rounded-md border border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-800"
                  >
                    Activate
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
