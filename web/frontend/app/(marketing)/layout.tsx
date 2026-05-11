import Link from "next/link";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 selection:bg-blue-500/30">
      <nav className="fixed top-0 w-full z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="font-bold text-xl tracking-tighter text-gray-900">
            SocialGrowth<span className="text-blue-600">AI</span>
          </div>
          <div className="flex gap-6 text-sm font-medium text-gray-600 items-center">
            <Link href="/" className="hover:text-gray-900 transition-colors">Home</Link>
            <Link href="/enterprise" className="hover:text-gray-900 transition-colors">Enterprise</Link>
            <Link href="/login" className="bg-gray-900 text-white px-4 py-1.5 rounded-full hover:bg-gray-800 transition-colors">Sign In</Link>
          </div>
        </div>
      </nav>
      {children}
    </div>
  );
}
