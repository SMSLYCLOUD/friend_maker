"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setAuthSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");

    if (!username || !password) {
      setError("Username and password are required.");
      return;
    }

    setAuthSession(username);
    const nextPath = typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("next") || "/dashboard"
      : "/dashboard";
    router.push(nextPath);
  };

  return (
    <div className="mx-auto w-full max-w-md rounded-xl border border-gray-800 bg-gray-900 p-8">
      <h1 className="text-3xl font-bold text-white">Sign in</h1>
      <p className="mt-2 text-sm text-gray-400">Simple login flow (no OTP/email step).</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="mb-1 block text-sm text-gray-300" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            name="username"
            required
            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-300" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
          />
        </div>
        <button type="submit" className="w-full rounded-md bg-blue-600 py-2 font-medium text-white hover:bg-blue-500">
          Sign in
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <p className="mt-6 text-sm text-gray-400">
        No account?{" "}
        <Link className="text-blue-400 hover:text-blue-300" href="/register">
          Register
        </Link>
      </p>
    </div>
  );
}
