"use client";
import { useEffect, useState } from "react";
import { fetchTemplates, createTemplate, updateTemplate, deleteTemplate } from "@/lib/api";
import { Plus, Save, Trash2, X, FileText, MessageSquare, Bot, Edit3, Loader2, Copy, Check } from "lucide-react";

type Template = {
  id: string;
  user_id: string;
  name: string;
  template_type: string;
  content: string;
  platform: string | null;
  is_default: number;
  created_at: number;
  updated_at: number;
};

const TYPE_META: Record<string, { label: string; color: string; icon: typeof FileText; description: string }> = {
  bot_instruction: { label: "Bot Instruction", color: "emerald", icon: Bot, description: "Global rules applied to all campaigns" },
  ai_instruction: { label: "AI Instruction", color: "blue", icon: FileText, description: "Campaign-specific AI behavior" },
  message_template: { label: "Message Template", color: "purple", icon: MessageSquare, description: "DM / comment / reply templates" },
};

const TYPE_COLORS: Record<string, string> = {
  emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  blue: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  purple: "border-purple-500/30 bg-purple-500/10 text-purple-400",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Template | null>(null);
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    template_type: "ai_instruction",
    content: "",
    platform: "",
    is_default: false,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await fetchTemplates();
      setTemplates(data);
    } catch (err) {
      console.error("Failed to load templates", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = filter === "all" ? templates : templates.filter(t => t.template_type === filter);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", template_type: "ai_instruction", content: "", platform: "", is_default: false });
    setShowForm(true);
  };

  const openEdit = (t: Template) => {
    setEditing(t);
    setForm({
      name: t.name,
      template_type: t.template_type,
      content: t.content,
      platform: t.platform || "",
      is_default: !!t.is_default,
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.content.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await updateTemplate(editing.id, {
          name: form.name,
          content: form.content,
          template_type: form.template_type,
          platform: form.platform || null,
          is_default: form.is_default,
        });
      } else {
        await createTemplate({
          name: form.name,
          content: form.content,
          template_type: form.template_type,
          platform: form.platform || undefined,
          is_default: form.is_default,
        });
      }
      setShowForm(false);
      await loadTemplates();
    } catch (err) {
      console.error("Failed to save template", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this template?")) return;
    try {
      await deleteTemplate(id);
      await loadTemplates();
    } catch (err) {
      console.error("Failed to delete template", err);
    }
  };

  const handleCopy = async (t: Template) => {
    try {
      await navigator.clipboard.writeText(t.content);
      setCopiedId(t.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for HTTP (clipboard API requires HTTPS)
      const ta = document.createElement("textarea");
      ta.value = t.content;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopiedId(t.id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Templates</h1>
          <p className="text-sm text-gray-400 mt-1">Reusable prompt and message templates</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white hover:bg-blue-700 shadow-lg shadow-blue-900/20 transition-all touch-manipulation"
        >
          <Plus className="w-4 h-4" /> New Template
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {["all", "bot_instruction", "ai_instruction", "message_template"].map(type => {
          const meta = TYPE_META[type];
          const isActive = filter === type;
          return (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all touch-manipulation ${
                isActive
                  ? type === "all"
                    ? "bg-white/10 text-white border border-white/20"
                    : TYPE_COLORS[TYPE_META[type]?.color || "blue"]
                  : "bg-gray-900/40 text-gray-400 border border-gray-800 hover:border-gray-700"
              }`}
            >
              {type === "all" ? "All" : meta?.label || type}
              <span className="ml-2 text-xs opacity-60">
                {type === "all" ? templates.length : templates.filter(t => t.template_type === type).length}
              </span>
            </button>
          );
        })}
      </div>

      {/* Template grid */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-gray-800 bg-gray-900/40 p-12 text-center">
          <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No templates yet</p>
          <p className="text-sm text-gray-500 mt-1">Create your first template to reuse prompts across campaigns</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map(t => {
            const meta = TYPE_META[t.template_type] || TYPE_META.ai_instruction;
            const Icon = meta.icon;
            return (
              <div
                key={t.id}
                className="rounded-2xl border border-gray-800 bg-gray-900/40 p-5 backdrop-blur-sm hover:border-gray-700 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${TYPE_COLORS[meta.color]}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-sm">{t.name}</h3>
                      <p className="text-xs text-gray-500">{meta.label}</p>
                    </div>
                  </div>
                  {t.is_default ? (
                    <span className="text-[10px] uppercase tracking-wider bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-semibold">default</span>
                  ) : null}
                  {t.user_id === "system" ? (
                    <span className="text-[10px] uppercase tracking-wider bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-semibold">preset</span>
                  ) : null}
                </div>

                <p className="text-gray-400 text-xs line-clamp-3 mb-4 min-h-[3rem]">{t.content}</p>

                {t.platform && (
                  <span className="inline-block text-[10px] uppercase tracking-wider bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full mb-3">
                    {t.platform}
                  </span>
                )}

                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleCopy(t)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-xs hover:bg-gray-700 transition-all touch-manipulation"
                  >
                    {copiedId === t.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedId === t.id ? "Copied" : "Copy"}
                  </button>
                  {t.user_id !== "system" && (
                    <>
                      <button
                        onClick={() => openEdit(t)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-xs hover:bg-gray-700 transition-all touch-manipulation"
                      >
                        <Edit3 className="w-3 h-3" /> Edit
                      </button>
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs hover:bg-red-500/20 transition-all touch-manipulation"
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create/Edit modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-white">{editing ? "Edit Template" : "New Template"}</h2>
              <button onClick={() => setShowForm(false)} className="p-2 rounded-lg hover:bg-gray-800 transition-all touch-manipulation">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Name</label>
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. TikTok Follower Growth v1"
                  className="mt-1 w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Type</label>
                  <select
                    value={form.template_type}
                    onChange={e => setForm(f => ({ ...f, template_type: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                  >
                    <option value="bot_instruction">Bot Instruction</option>
                    <option value="ai_instruction">AI Instruction</option>
                    <option value="message_template">Message Template</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Platform (optional)</label>
                  <select
                    value={form.platform}
                    onChange={e => setForm(f => ({ ...f, platform: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all"
                  >
                    <option value="">All platforms</option>
                    <option value="tiktok">TikTok</option>
                    <option value="instagram">Instagram</option>
                    <option value="twitter">Twitter/X</option>
                    <option value="facebook">Facebook</option>
                    <option value="linkedin">LinkedIn</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Content</label>
                <textarea
                  value={form.content}
                  onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                  rows={12}
                  placeholder={form.template_type === "message_template"
                    ? "Hey {username}! Loved your recent post about {topic}..."
                    : "You are a social media growth assistant. Your goal is to..."}
                  className="mt-1 w-full rounded-lg border border-gray-800 bg-black px-3 py-3 text-white outline-none focus:ring-2 focus:ring-blue-600 transition-all font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">{form.content.length} characters</p>
              </div>

              <label className="flex items-center gap-2 cursor-pointer touch-manipulation">
                <input
                  type="checkbox"
                  checked={form.is_default}
                  onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))}
                  className="rounded border-gray-700 bg-black text-blue-600 focus:ring-blue-600"
                />
                <span className="text-sm text-gray-300">Set as default (auto-selected for new campaigns)</span>
              </label>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim() || !form.content.trim()}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-900/20 transition-all touch-manipulation"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="rounded-xl border border-gray-700 px-6 py-3 text-sm font-medium text-gray-300 hover:bg-gray-800 transition-all touch-manipulation"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
