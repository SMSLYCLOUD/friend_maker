"use client";
import { useEffect, useState } from "react";
import { fetchSettings, updateSettings, fetchGlobalSettings, updateGlobalSettings, fetchBotImages, uploadBotImage, deleteBotImage, getImageUrl } from "@/lib/api";
import { Save, Smartphone, Shield, Globe, Loader2, MessageCircle, ArrowLeft, ImagePlus, Trash2, X } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({
    WORKSPACE_NAME: "SocialGrowthAI Team",
    TIMEZONE: "UTC",
    AUTO_PAUSE: "true"
  });
  const [globalSettings, setGlobalSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [botImages, setBotImages] = useState<{filename: string; url: string}[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [userData, globalData, imgData] = await Promise.all([
        fetchSettings(),
        fetchGlobalSettings().catch(() => ({})),
        fetchBotImages().catch(() => ({ images: [] }))
      ]);
      if (Object.keys(userData).length > 0) {
        setSettings((prev: any) => ({ ...prev, ...userData }));
      }
      if (Object.keys(globalData).length > 0) {
        setGlobalSettings(globalData);
        setSettings((prev: any) => ({ ...prev, ...globalData }));
      }
      if (imgData.images) setBotImages(imgData.images);
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
      const userSettings = { ...settings };
      delete userSettings.TELEGRAM_BOT_TOKEN;
      delete userSettings.TELEGRAM_ALLOWED_USER_IDS;
      delete userSettings.BOT_INSTRUCTIONS;
      await Promise.all([
        updateSettings(userSettings),
        updateGlobalSettings({
          TELEGRAM_BOT_TOKEN: settings.TELEGRAM_BOT_TOKEN || "",
          TELEGRAM_ALLOWED_USER_IDS: settings.TELEGRAM_ALLOWED_USER_IDS || "",
          BOT_INSTRUCTIONS: settings.BOT_INSTRUCTIONS || ""
        })
      ]);
      setMessage("Settings synchronized successfully.");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setMessage("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleUploadImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadBotImage(file);
      const imgData = await fetchBotImages();
      if (imgData.images) setBotImages(imgData.images);
    } catch (err: any) {
      setMessage(err.message || "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteImage = async (filename: string) => {
    try {
      await deleteBotImage(filename);
      setBotImages(prev => prev.filter(i => i.filename !== filename));
    } catch (err: any) {
      setMessage(err.message || "Delete failed");
    }
  };

  if (loading) return <div className="flex items-center justify-center h-[400px]"><Loader2 className="animate-spin text-blue-500" /></div>;

  return (
    <div className="space-y-6 sm:space-y-8 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Settings</h1>
          <p className="text-sm text-gray-500 mt-1">Configure your automation engine and workspace preferences.</p>
        </div>
        <Link href="/dashboard" className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-xs font-bold text-gray-400 hover:text-white hover:bg-white/5 transition-all whitespace-nowrap touch-manipulation">
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </Link>
      </div>

      <form onSubmit={handleSave} className="space-y-6">


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
                  value={settings.OPENROUTER_MODEL || "google/gemini-2.0-flash-001"}
                  onChange={(e) => setSettings({ ...settings, OPENROUTER_MODEL: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                >
                  <optgroup label="— Free Models —">
                    <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free)</option>
                    <option value="google/gemini-2.0-flash-lite-preview-02-05:free">Gemini 2.0 Flash Lite (Free)</option>
                    <option value="deepseek/deepseek-chat:free">DeepSeek V3 (Free)</option>
                    <option value="deepseek/deepseek-r1:free">DeepSeek R1 (Free)</option>
                    <option value="mistralai/mistral-small-3.1:free">Mistral Small 3.1 (Free)</option>
                    <option value="meta-llama/llama-3.2-3b-instruct:free">Llama 3.2 3B (Free)</option>
                    <option value="qwen/qwen-2.5-72b-instruct:free">Qwen 2.5 72B (Free)</option>
                    <option value="cohere/command-r-08-2024:free">Command R (Free)</option>
                  </optgroup>
                  <optgroup label="— Paid Models —">
                    <option value="google/gemini-2.0-flash-001">Gemini 2.0 Flash</option>
                    <option value="google/gemini-2.0-flash-lite-preview-02-05">Gemini 2.0 Flash Lite</option>
                    <option value="google/gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                    <option value="openai/gpt-4o">GPT-4o</option>
                    <option value="openai/gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="openai/o3-mini">o3 Mini</option>
                    <option value="openai/o1">o1</option>
                    <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                    <option value="anthropic/claude-3-opus">Claude 3 Opus</option>
                    <option value="anthropic/claude-3-haiku">Claude 3 Haiku</option>
                    <option value="deepseek/deepseek-chat">DeepSeek V3</option>
                    <option value="deepseek/deepseek-r1">DeepSeek R1</option>
                    <option value="mistralai/mistral-large-2407">Mistral Large</option>
                    <option value="meta-llama/llama-3.1-405b-instruct">Llama 3.1 405B</option>
                    <option value="cohere/command-r-plus-08-2024">Command R+</option>
                  </optgroup>
                </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">OpenRouter API Key</label>
                <input
                  type="password"
                  value={settings.OPENROUTER_API_KEY || ""}
                  onChange={(e) => setSettings({ ...settings, OPENROUTER_API_KEY: e.target.value })}
                  className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all touch-manipulation"
                  placeholder="sk-or-v1-..."
                />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Default Timezone</label>
              <select
                value={settings.TIMEZONE}
                onChange={(e) => setSettings({ ...settings, TIMEZONE: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all touch-manipulation"
              >
                <option value="UTC">UTC (Universal)</option>
                <option value="America/New_York">New York (EST)</option>
                <option value="Europe/London">London (GMT)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Telegram Bot */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-6">
            <MessageCircle className="w-5 h-5 text-sky-500" />
            <h2 className="text-xl font-bold text-white">Telegram Bot</h2>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-black/40 border border-gray-800 mb-4">
            <div>
              <p className="font-bold text-white">Bot Status</p>
              <p className="text-xs text-gray-500">Telegram notification bot for real-time alerts.</p>
            </div>
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full ${settings.TELEGRAM_BOT_TOKEN ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500"}`} />
              <span className={`text-xs font-bold uppercase tracking-wider ${settings.TELEGRAM_BOT_TOKEN ? "text-emerald-500" : "text-red-500"}`}>
                {settings.TELEGRAM_BOT_TOKEN ? "Online" : "Offline"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="mb-1 block text-xs font-semibold text-sky-400 uppercase tracking-wider">Bot Token</label>
              <input
                type="password"
                value={settings.TELEGRAM_BOT_TOKEN || ""}
                onChange={(e) => setSettings({ ...settings, TELEGRAM_BOT_TOKEN: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-sky-600 transition-all touch-manipulation"
                placeholder="123456:ABC-DEF..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-blue-400 uppercase tracking-wider">Workspace Name</label>
              <input
                type="text"
                value={settings.WORKSPACE_NAME}
                onChange={(e) => setSettings({ ...settings, WORKSPACE_NAME: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all touch-manipulation"
                placeholder="SocialGrowthAI Team"
              />
            </div>
          </div>
        </div>

        {/* Bot Instructions */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-6">
            <MessageCircle className="w-5 h-5 text-amber-500" />
            <h2 className="text-xl font-bold text-white">Bot Instructions</h2>
          </div>
          <p className="text-xs text-gray-500 mb-4">Global behavioral rules for all AI agents — like OpenClaw skills. Example: "Never follow users with empty profiles. Always reply in Spanish. Skip accounts with less than 10 posts."</p>
          <textarea
            value={settings.BOT_INSTRUCTIONS || ""}
            onChange={(e) => setSettings({ ...settings, BOT_INSTRUCTIONS: e.target.value })}
            className="w-full rounded-lg border border-gray-800 bg-black px-4 py-3 text-white outline-none focus:ring-2 focus:ring-amber-600 transition-all min-h-[180px] text-sm font-mono touch-manipulation"
            placeholder={`# Agent Rules\n- Never interact with accounts that have no profile photo\n- Skip users who post only crypto/NFT content\n- Always include a personalized compliment in messages\n- Do not engage with accounts containing "admin" or "support" in the name\n- Wait at least 60 seconds between automated actions`}
          />

          {/* Reference Images */}
          <div className="mt-6 pt-6 border-t border-white/5">
            <div className="flex items-center gap-2 mb-4">
              <ImagePlus className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-bold text-white">Reference Images</h3>
            </div>
            <p className="text-xs text-gray-500 mb-4">Upload reference profile screenshots so the AI can visually compare targets. Upload images of the type of profile you want to target (or avoid).</p>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4 mb-4">
              {botImages.map((img) => (
                <div key={img.filename} className="relative group">
                  <img src={getImageUrl(img.filename)} alt="Reference" className="w-full h-24 rounded-xl object-cover border border-white/10" />
                  <button
                    onClick={() => handleDeleteImage(img.filename)}
                    className="absolute top-1 -right-1 h-10 w-10 rounded-full bg-red-600 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity touch-manipulation"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <label className="w-full h-24 rounded-xl border-2 border-dashed border-white/10 hover:border-purple-500/50 flex items-center justify-center cursor-pointer transition-colors touch-manipulation">
                {uploading ? (
                  <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                ) : (
                  <ImagePlus className="w-6 h-6 text-gray-500" />
                )}
                <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" className="hidden" onChange={handleUploadImage} />
              </label>
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

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="text-sm font-medium text-emerald-400">{message}</div>
          <button 
            type="submit" 
            disabled={saving}
            className="px-6 sm:px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all flex items-center gap-2 touch-manipulation w-full sm:w-auto justify-center"
          >
            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            Save All Settings
          </button>
        </div>
      </form>
    </div>
  );
}
