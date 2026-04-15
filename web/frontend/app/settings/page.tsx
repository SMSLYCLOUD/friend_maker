"use client";

import { FormEvent, useState } from "react";

export default function SettingsPage() {
  const [workspaceName, setWorkspaceName] = useState("SocialGrowthAI Team");
  const [timezone, setTimezone] = useState("UTC");
  const [defaultPlatform, setDefaultPlatform] = useState("instagram");
  const [autoPauseOnErrors, setAutoPauseOnErrors] = useState(true);
  const [saveMessage, setSaveMessage] = useState("");

  const saveSettings = (event: FormEvent) => {
    event.preventDefault();
    setSaveMessage("Settings saved locally.");
    setTimeout(() => setSaveMessage(""), 2500);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <form className="space-y-6" onSubmit={saveSettings}>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="mb-4 text-xl font-semibold">Workspace</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-gray-300">Workspace name</label>
              <input
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-300">Timezone</label>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
                <option value="Asia/Dubai">Asia/Dubai</option>
              </select>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="mb-4 text-xl font-semibold">Automation defaults</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-gray-300">Default platform</label>
              <select
                value={defaultPlatform}
                onChange={(e) => setDefaultPlatform(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
              >
                <option value="instagram">Instagram</option>
                <option value="twitter">Twitter / X</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>

            <label className="flex items-center gap-3 rounded-md border border-gray-800 bg-gray-950 p-3 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={autoPauseOnErrors}
                onChange={(e) => setAutoPauseOnErrors(e.target.checked)}
                className="h-4 w-4"
              />
              Auto-pause campaigns on repeated errors
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="mb-4 text-xl font-semibold">Security</h2>
          <div className="space-y-3 text-sm text-gray-300">
            <p>Session auth is currently cookie-based for frontend route protection.</p>
            <p>For production security, enable backend JWT/session validation on all API endpoints.</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-500">
            Save settings
          </button>
          {saveMessage && <span className="text-sm text-emerald-400">{saveMessage}</span>}
        </div>
      </form>
    </div>
  );
}
