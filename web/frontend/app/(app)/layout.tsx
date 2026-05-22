import { Sidebar } from "../../components/Sidebar";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-black text-white font-sans selection:bg-blue-500/30">
      <Sidebar />
      {/* Main content area with responsive padding */}
      <main className="flex-1 overflow-auto lg:overflow-hidden">
        {/* Desktop content */}
        <div className="hidden lg:block p-8 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/10 via-black to-black">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </div>
        
        {/* Mobile content */}
        <div className="lg:hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/10 via-black to-black">
          <div className="p-4 md:p-6 max-w-4xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
