"use client";
import { useEffect, useState } from "react";
import { fetchSettings, updateSettings } from "@/lib/api";
import { Save, Smartphone, Shield, Settings2, Globe, Loader2 } from "lucide-react";

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({
    USE_ANDROID_EMULATOR: "true",
    WORKSPACE_NAME: "SocialGrowthAI Team",
    TIMEZONE: "UTC",
    AUTO_PAUSE: "true"
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      if (Object.keys(data).length > 0) {
        setSettings((prev: any) => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error("Failed to load settings", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateSettings(settings);
      setMessage("Settings synchronized successfully.");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setMessage("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-[400px]"><Loader2 className="animate-spin text-blue-500" /></div>;

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Configure your automation engine and workspace preferences.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Android Emulator Section */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-6">
            <Smartphone className="w-5 h-5 text-purple-500" />
            <h2 className="text-xl font-bold text-white">Device Orchestration</h2>
          </div>
          
          <div className="flex items-center justify-between p-4 rounded-xl bg-black/40 border border-gray-800">
            <div>
              <p className="font-bold text-white">Android Emulator (Docker)</p>
              <p className="text-xs text-gray-500">Route all social media interactions through the dedicated Android Docker container.</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer"
                checked={settings.USE_ANDROID_EMULATOR === "true"}
                onChange={(e) => setSettings({ ...settings, USE_ANDROID_EMULATOR: e.target.checked ? "true" : "false" })}
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          <p className="mt-3 text-[10px] text-amber-500/80 italic">Note: Requires 'android-emulator' service to be running in docker-compose.</p>
        </div>

        {/* Workspace Section */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-6">
            <Globe className="w-5 h-5 text-blue-500" />
            <h2 className="text-xl font-bold text-white">Workspace Preferences</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">AI Intelligence Model</label>
              <select
                value={settings.OPENROUTER_MODEL || "google/gemini-flash-1.5"}
                onChange={(e) => setSettings({ ...settings, OPENROUTER_MODEL: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
              >
                <option value="google/gemini-flash-1.5">Gemini Flash 1.5 (Vision Fast)</option>
                <option value="google/gemini-pro-1.5">Gemini Pro 1.5 (Vision Ultra)</option>
                <option value="openai/gpt-4o-mini">GPT-4o Mini (Vision Compact)</option>
                <option value="openai/gpt-4o">GPT-4o (Vision Power)</option>
                <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet (Elite)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">OpenRouter API Key</label>
              <input
                type="password"
                value={settings.OPENROUTER_API_KEY || ""}
                onChange={(e) => setSettings({ ...settings, OPENROUTER_API_KEY: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                placeholder="sk-or-v1-..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Default Timezone</label>
              <select
                value={settings.TIMEZONE}
                onChange={(e) => setSettings({ ...settings, TIMEZONE: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
              >
                <option value="UTC">UTC (Universal)</option>
                <option value="America/New_York">New York (EST)</option>
                <option value="Europe/London">London (GMT)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Security & System */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-6">
            <Shield className="w-5 h-5 text-emerald-500" />
            <h2 className="text-xl font-bold text-white">System Guard</h2>
          </div>
          
          <div className="flex items-center justify-between p-4 rounded-xl bg-black/40 border border-gray-800">
            <div>
              <p className="font-bold text-white">Auto-Pause on Error</p>
              <p className="text-xs text-gray-500">Automatically pause campaigns if 3 consecutive failures occur.</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer"
                checked={settings.AUTO_PAUSE === "true"}
                onChange={(e) => setSettings({ ...settings, AUTO_PAUSE: e.target.checked ? "true" : "false" })}
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm font-medium text-emerald-400">{message}</div>
          <button 
            type="submit" 
            disabled={saving}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all flex items-center gap-2"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save All Settings
          </button>
        </div>
      </form>
    </div>
  );
}
