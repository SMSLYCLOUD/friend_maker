"use client";
import { useEffect, useState } from "react";
import { fetchSettings, updateSettings, fetchGlobalSettings, updateGlobalSettings, fetchBotImages, uploadBotImage, deleteBotImage, getImageUrl, updateEnvVars, fetchEnvVars, fetchProviderStatus, rotateProvider } from "@/lib/api";
import { Save, Smartphone, Shield, Globe, Loader2, MessageCircle, ArrowLeft, ImagePlus, Trash2, X, Zap } from "lucide-react";
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
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [providerStatus, setProviderStatus] = useState<any>(null);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [userData, globalData, imgData, envData, provData] = await Promise.all([
        fetchSettings(),
        fetchGlobalSettings().catch(() => ({})),
        fetchBotImages().catch(() => ({ images: [] })),
        fetchEnvVars().catch(() => ({})),
        fetchProviderStatus().catch(() => null)
      ]);
      if (Object.keys(userData).length > 0) {
        setSettings((prev: any) => ({ ...prev, ...userData }));
      }
      if (Object.keys(globalData).length > 0) {
        setGlobalSettings(globalData);
        setSettings((prev: any) => ({ ...prev, ...globalData }));
      }
      if (envData) {
        setSettings((prev: any) => ({ ...prev, ...envData }));
        setEnvVars(envData);
      }
      if (imgData.images) setBotImages(imgData.images);
      if (provData) setProviderStatus(provData);
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
      const envUpdate: Record<string, string> = {};
      if (settings.OPENROUTER_API_KEY) envUpdate.OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY;
      if (settings.OPENROUTER_MODEL) envUpdate.OPENROUTER_MODEL = settings.OPENROUTER_MODEL;
      if (settings.SKYVERN_INTER_TASK_DELAY) envUpdate.SKYVERN_INTER_TASK_DELAY = settings.SKYVERN_INTER_TASK_DELAY;
      // Provider env vars
      const providerKeys = [
        "SKYVERN_LLM_PROVIDERS",
        "SKYVERN_LLM_GROQ_API_KEY", "SKYVERN_LLM_GROQ_MODEL", "SKYVERN_LLM_GROQ_BASE_URL", "SKYVERN_LLM_GROQ_RPM_LIMIT",
        "SKYVERN_LLM_OPENROUTER_API_KEY", "SKYVERN_LLM_OPENROUTER_MODEL", "SKYVERN_LLM_OPENROUTER_BASE_URL", "SKYVERN_LLM_OPENROUTER_RPM_LIMIT",
        "SKYVERN_LLM_GOOGLE_API_KEY", "SKYVERN_LLM_GOOGLE_MODEL", "SKYVERN_LLM_GOOGLE_BASE_URL", "SKYVERN_LLM_GOOGLE_RPM_LIMIT",
        "SKYVERN_LLM_SAMBANOVA_API_KEY", "SKYVERN_LLM_SAMBANOVA_MODEL", "SKYVERN_LLM_SAMBANOVA_BASE_URL", "SKYVERN_LLM_SAMBANOVA_RPM_LIMIT",
        "SKYVERN_LLM_NVIDIA_API_KEY", "SKYVERN_LLM_NVIDIA_MODEL", "SKYVERN_LLM_NVIDIA_BASE_URL", "SKYVERN_LLM_NVIDIA_RPM_LIMIT",
      ];
      for (const key of providerKeys) {
        if (settings[key] !== undefined && settings[key] !== "") {
          envUpdate[key] = settings[key];
        }
      }
      if (Object.keys(envUpdate).length) {
        await updateEnvVars(envUpdate);
        setMessage("Settings saved. Backend is restarting to apply env changes (~10s)...");
      } else {
        setMessage("Settings synchronized successfully.");
      }
      setTimeout(() => setMessage(""), 5000);
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
                    <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free) - 1M ctx, multimodal</option>
                    <option value="deepseek/deepseek-r1:free">DeepSeek R1 (Free) - 128K, reasoning</option>
                    <option value="deepseek/deepseek-chat:free">DeepSeek V3 (Free) - 128K, general</option>
                    <option value="deepseek/deepseek-v4-flash:free">DeepSeek V4 Flash (Free) - 1M ctx, fast</option>
                    <option value="meta-llama/llama-4-maverick:free">Llama 4 Maverick (Free) - 1M ctx, multimodal</option>
                    <option value="meta-llama/llama-4-scout:free">Llama 4 Scout (Free) - 10M ctx</option>
                    <option value="meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B (Free) - 128K</option>
                    <option value="qwen/qwen3-235b-a22b:free">Qwen3 235B (Free) - coding, analysis</option>
                    <option value="qwen/qwen3-coder-480b-a35b:free">Qwen3 Coder 480B (Free) - 1M ctx</option>
                    <option value="mistralai/mistral-small-3.1-24b-instruct:free">Mistral Small 24B (Free)</option>
                    <option value="x-ai/grok-3-mini-beta:free">Grok 3 Mini (Free) - 131K, fast</option>
                    <option value="google/gemma-3-27b-it:free">Gemma 3 27B (Free) - 128K</option>
                    <option value="nousresearch/hermes-3-llama-3.1-70b:free">Hermes 3 70B (Free)</option>
                    <option value="nvidia/nemotron-3-super:free">Nemotron 3 Super (Free) - 1M ctx</option>
                    <option value="openai/gpt-oss-120b:free">GPT-OSS 120B (Free) - 131K</option>
                    <option value="zhipu-ai/glm-4.5-air:free">GLM 4.5 Air (Free) - 131K</option>
                    <option value="nvidia/nemotron-nano-12b-v2-vl:free">Nemotron Nano 12B VL (Free) - vision</option>
                    <option value="openrouter/free">Auto: Best Free Model (Router)</option>
                  </optgroup>
                  <optgroup label="— Paid Models —">
                    <option value="google/gemini-2.0-flash-001">Gemini 2.0 Flash - 1M ctx, cheap</option>
                    <option value="google/gemini-2.0-pro-exp-02-05">Gemini 2.0 Pro - 2M ctx</option>
                    <option value="google/gemini-1.5-pro">Gemini 1.5 Pro - 2M ctx, vision</option>
                    <option value="openai/gpt-4o-mini">GPT-4o Mini - cheap, fast</option>
                    <option value="openai/gpt-4o">GPT-4o - vision, strong all-round</option>
                    <option value="openai/gpt-4-turbo">GPT-4 Turbo - 128K</option>
                    <option value="openai/o3-mini">o3 Mini - reasoning, coding</option>
                    <option value="openai/o1">o1 - deep reasoning</option>
                    <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet - balanced</option>
                    <option value="anthropic/claude-3-opus">Claude 3 Opus - max intelligence</option>
                    <option value="anthropic/claude-3-haiku">Claude 3 Haiku - fastest Claude</option>
                    <option value="deepseek/deepseek-chat">DeepSeek V3 - 128K</option>
                    <option value="deepseek/deepseek-r1">DeepSeek R1 - reasoning</option>
                    <option value="mistralai/mistral-large-2407">Mistral Large - 128K</option>
                    <option value="meta-llama/llama-3.1-405b-instruct">Llama 3.1 405B - largest open</option>
                    <option value="cohere/command-r-plus-08-2024">Command R+ - 128K, RAG</option>
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
                {envVars.OPENROUTER_API_KEY && (
                  <p className="mt-1 text-[10px] text-emerald-400 font-mono">● active: {envVars.OPENROUTER_API_KEY}</p>
                )}
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

        {/* LLM Providers Section */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" />
              <h2 className="text-xl font-bold text-white">LLM Providers</h2>
            </div>
            {providerStatus && (
              <span className="text-xs text-gray-500 font-mono">
                {providerStatus.available_providers}/{providerStatus.total_providers} available
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mb-4">Configure multiple free LLM providers for Skyvern. When one hits rate limits, the system automatically rotates to the next available provider.</p>

          {/* Provider Status Grid */}
          {providerStatus?.providers && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
              {Object.entries(providerStatus.providers).map(([name, info]: [string, any]) => (
                <div key={name} className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-gray-800">
                  <div className="flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${info.available ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500"}`} />
                    <div>
                      <p className="text-xs font-bold text-white">{name}</p>
                      <p className="text-[10px] text-gray-500 font-mono">{info.model}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-[10px] font-bold ${info.available ? "text-emerald-400" : "text-red-400"}`}>
                      {info.available ? "READY" : `${info.cooldown_remaining}s`}
                    </p>
                    <p className="text-[10px] text-gray-600">{info.total_tasks} tasks</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Provider Config Inputs */}
          <div className="space-y-4">
            {/* Groq */}
            <div className="p-4 rounded-xl bg-black/40 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <h3 className="text-sm font-bold text-white">Groq</h3>
                <span className="text-[10px] text-emerald-400 font-mono">30 RPM, 14,400 RPD</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">API Key</label>
                  <input
                    type="password"
                    value={settings.SKYVERN_LLM_GROQ_API_KEY || ""}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_GROQ_API_KEY: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-emerald-600 transition-all"
                    placeholder="gsk_..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">Model</label>
                  <input
                    type="text"
                    value={settings.SKYVERN_LLM_GROQ_MODEL || "llama-4-scout-17b-16e-instruct"}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_GROQ_MODEL: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-emerald-600 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* OpenRouter */}
            <div className="p-4 rounded-xl bg-black/40 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <h3 className="text-sm font-bold text-white">OpenRouter</h3>
                <span className="text-[10px] text-blue-400 font-mono">20 RPM, 50 RPD</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">API Key</label>
                  <input
                    type="password"
                    value={settings.SKYVERN_LLM_OPENROUTER_API_KEY || ""}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_OPENROUTER_API_KEY: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                    placeholder="sk-or-..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">Model</label>
                  <input
                    type="text"
                    value={settings.SKYVERN_LLM_OPENROUTER_MODEL || "nvidia/nemotron-nano-12b-v2-vl:free"}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_OPENROUTER_MODEL: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Google AI Studio */}
            <div className="p-4 rounded-xl bg-black/40 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-purple-500" />
                <h3 className="text-sm font-bold text-white">Google AI Studio</h3>
                <span className="text-[10px] text-purple-400 font-mono">10 RPM, 250 RPD</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">API Key</label>
                  <input
                    type="password"
                    value={settings.SKYVERN_LLM_GOOGLE_API_KEY || ""}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_GOOGLE_API_KEY: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-600 transition-all"
                    placeholder="AIza..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">Model</label>
                  <input
                    type="text"
                    value={settings.SKYVERN_LLM_GOOGLE_MODEL || "gemini-2.5-flash"}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_GOOGLE_MODEL: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-600 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* SambaNova */}
            <div className="p-4 rounded-xl bg-black/40 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-cyan-500" />
                <h3 className="text-sm font-bold text-white">SambaNova</h3>
                <span className="text-[10px] text-cyan-400 font-mono">30 RPM</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">API Key</label>
                  <input
                    type="password"
                    value={settings.SKYVERN_LLM_SAMBANOVA_API_KEY || ""}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_SAMBANOVA_API_KEY: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-cyan-600 transition-all"
                    placeholder="..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">Model</label>
                  <input
                    type="text"
                    value={settings.SKYVERN_LLM_SAMBANOVA_MODEL || "Llama-4-Maverick-17B-128E-Instruct"}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_SAMBANOVA_MODEL: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-cyan-600 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* NVIDIA NIM */}
            <div className="p-4 rounded-xl bg-black/40 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <h3 className="text-sm font-bold text-white">NVIDIA NIM</h3>
                <span className="text-[10px] text-green-400 font-mono">40 RPM</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">API Key</label>
                  <input
                    type="password"
                    value={settings.SKYVERN_LLM_NVIDIA_API_KEY || ""}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_NVIDIA_API_KEY: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-green-600 transition-all"
                    placeholder="..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-semibold text-gray-400 uppercase">Model</label>
                  <input
                    type="text"
                    value={settings.SKYVERN_LLM_NVIDIA_MODEL || "meta/llama-4-maverick-17b-128e-instruct"}
                    onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_NVIDIA_MODEL: e.target.value })}
                    className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-green-600 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Provider Order */}
            <div>
              <label className="mb-1 block text-xs font-semibold text-amber-400 uppercase tracking-wider">Provider Order (comma-separated)</label>
              <input
                type="text"
                value={settings.SKYVERN_LLM_PROVIDERS || "Groq,OpenRouter,Google,SambaNova,NVIDIA"}
                onChange={(e) => setSettings({ ...settings, SKYVERN_LLM_PROVIDERS: e.target.value })}
                className="w-full rounded-lg border border-gray-800 bg-black px-3 py-2 text-white text-sm font-mono outline-none focus:ring-2 focus:ring-amber-600 transition-all"
                placeholder="Groq,OpenRouter,Google,SambaNova,NVIDIA"
              />
              <p className="mt-1 text-[10px] text-gray-600">Providers are tried in this order. Remove one to skip it.</p>
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
