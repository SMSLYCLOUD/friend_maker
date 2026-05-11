"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Users, BarChart3, Settings, Rocket, LogIn, UserPlus, Zap, LogOut } from "lucide-react";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { clearAuthSession, isAuthenticated } from "@/lib/auth";

const protectedLinks = [
  { name: "Dashboard", href: "/dashboard", icon: BarChart3, color: "text-blue-400" },
  { name: "Accounts", href: "/accounts", icon: Users, color: "text-purple-400" },
  { name: "Campaigns", href: "/campaigns", icon: Rocket, color: "text-amber-400" },
  { name: "Settings", href: "/settings", icon: Settings, color: "text-emerald-400" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, [pathname]);

  const links = authenticated
    ? protectedLinks
    : [
        { name: "Register", href: "/register", icon: UserPlus },
        { name: "Login", href: "/login", icon: LogIn }
      ];

  return (
    <div className="flex h-full w-64 flex-col glass border-r border-white/5 bg-black/40 p-6">
      <div className="mb-10 flex items-center gap-3 px-2">
        <div className="relative">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-violet-600 glow-blue animate-pulse-slow" />
          <Zap className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tracking-tight text-white">SocialGrowth</span>
          <span className="text-[10px] font-bold uppercase tracking-widest text-blue-500">Premium AI</span>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-2">
        {links.map((link) => {
          const LinkIcon = link.icon;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={clsx(
                "group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                {
                  "bg-white/10 text-white shadow-lg border border-white/5": pathname === link.href,
                  "text-gray-400 hover:bg-white/5 hover:text-gray-200": pathname !== link.href,
                }
              )}
            >
              <LinkIcon className={clsx("w-5 h-5 transition-transform group-hover:scale-110", link.color || "text-gray-400")} />
              {link.name}
              {pathname === link.href && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
              )}
            </Link>
          );
        })}
      </nav>

      {authenticated && (
        <div className="mt-auto pt-6 border-t border-white/5">
          <button
            onClick={() => {
              clearAuthSession();
              window.location.href = "/login";
            }}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-gray-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
          >
            <LogOut className="h-5 w-5" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
