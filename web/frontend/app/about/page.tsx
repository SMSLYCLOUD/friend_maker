import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-white">About SocialGrowthAI</h1>
        <p className="mt-3 text-gray-300">
          SocialGrowthAI helps teams automate outreach workflows across social platforms with AI-assisted targeting,
          scheduling, and analytics.
        </p>
      </div>

      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h2 className="text-2xl font-semibold text-white">What this app includes</h2>
        <ul className="mt-4 list-disc space-y-2 pl-6 text-gray-300">
          <li>Campaign and account management from a unified dashboard.</li>
          <li>Automation scheduling with anti-detection behavior controls.</li>
          <li>Analytics APIs to monitor execution outcomes.</li>
        </ul>
      </section>

      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h2 className="text-2xl font-semibold text-white">Get started</h2>
        <p className="mt-3 text-gray-300">
          Create an account to access campaign workflows and connect social profiles.
        </p>
        <div className="mt-5 flex gap-3">
          <Link href="/register" className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-500">
            Create account
          </Link>
          <Link href="/login" className="rounded-lg border border-gray-700 px-4 py-2 font-medium text-white hover:bg-gray-800">
            Sign in
          </Link>
        </div>
      </section>
    </div>
  );
}
