import { Sidebar } from "../../components/Sidebar";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-black text-white font-sans selection:bg-blue-500/30">
      <Sidebar />
      <main className="flex-1 overflow-auto p-8 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/10 via-black to-black">
        {children}
      </main>
    </div>
  );
}
