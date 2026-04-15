"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setAuthSession } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
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

    setAuthSession(username);
    router.push("/dashboard");
  };

  return (
    <div className="mx-auto w-full max-w-md rounded-xl border border-gray-800 bg-gray-900 p-8">
      <h1 className="text-3xl font-bold text-white">Create account</h1>
      <p className="mt-2 text-sm text-gray-400">Standard registration form (no email OTP verification).</p>

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
            minLength={8}
            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-300" htmlFor="confirmPassword">
            Confirm password
          </label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            required
            minLength={8}
            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-white"
          />
        </div>
        <button type="submit" className="w-full rounded-md bg-emerald-600 py-2 font-medium text-white hover:bg-emerald-500">
          Register
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <p className="mt-6 text-sm text-gray-400">
        Already have an account?{" "}
        <Link className="text-blue-400 hover:text-blue-300" href="/login">
          Sign in
        </Link>
      </p>
    </div>
  );
}
