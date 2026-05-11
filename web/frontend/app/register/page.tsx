"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setAuthSession } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");
    const confirmPassword = String(form.get("confirmPassword") || "");

    if (!username || !password || !confirmPassword) {
      setError("All fields are required.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const { register } = await import("@/lib/api");
      await register({ username, password });
      
      setAuthSession(username);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Username may already be taken.");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#05070a] p-4 font-sans selection:bg-emerald-500/30">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-emerald-600/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-teal-600/5 blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-gray-800/50 bg-[#0c0f14]/80 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white">Create account</h1>
          <p className="mt-2 text-sm text-gray-400">Join SocialGrowthAI. Start your automated journey.</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              name="username"
              required
              placeholder="e.g. growth_master"
              className="w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-white placeholder:text-gray-700 outline-none transition-all focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              minLength={8}
              placeholder="••••••••"
              className="w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-white placeholder:text-gray-700 outline-none transition-all focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              minLength={8}
              placeholder="••••••••"
              className="w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-white placeholder:text-gray-700 outline-none transition-all focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
            />
          </div>
          <button 
            type="submit" 
            className="group relative w-full overflow-hidden rounded-xl bg-emerald-600 py-3.5 font-bold text-white transition-all hover:bg-emerald-500 hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] active:scale-[0.98]"
          >
            <span className="relative z-10">Register</span>
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-lg border border-red-900/50 bg-red-900/10 p-3 text-center text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-800/50 text-center text-sm text-gray-500">
          Already have an account?{" "}
          <Link className="font-semibold text-emerald-400 transition-colors hover:text-emerald-300" href="/login">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
