"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setAuthSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");

    if (!username || !password) {
      setError("Username and password are required.");
      return;
    }

    try {
      const { login } = await import("@/lib/api");
      await login({ username, password });
      
      setAuthSession(username);
      const nextPath = typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("next") || "/dashboard"
        : "/dashboard";
      router.push(nextPath);
    } catch (err: any) {
      setError(err.message || "Invalid username or password.");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#05070a] p-4 font-sans selection:bg-blue-500/30">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/5 blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-gray-800/50 bg-[#0c0f14]/80 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white">Sign in</h1>
          <p className="mt-2 text-sm text-gray-400">Welcome back. Enter your credentials to continue.</p>
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
              placeholder="e.g. jules_ai"
              className="w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-white placeholder:text-gray-700 outline-none transition-all focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10"
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
              placeholder="••••••••"
              className="w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-white placeholder:text-gray-700 outline-none transition-all focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10"
            />
          </div>
          <button 
            type="submit" 
            className="group relative w-full overflow-hidden rounded-xl bg-blue-600 py-3.5 font-bold text-white transition-all hover:bg-blue-500 hover:shadow-[0_0_20px_rgba(37,99,235,0.4)] active:scale-[0.98]"
          >
            <span className="relative z-10">Sign in</span>
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-lg border border-red-900/50 bg-red-900/10 p-3 text-center text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-800/50 text-center text-sm text-gray-500">
          No account?{" "}
          <Link className="font-semibold text-blue-400 transition-colors hover:text-blue-300" href="/register">
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}
