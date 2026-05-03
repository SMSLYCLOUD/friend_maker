"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Users, BarChart3, Settings, Rocket, Info, LogIn, UserPlus } from "lucide-react";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { clearAuthSession, isAuthenticated } from "@/lib/auth";

const publicLinks = [
  { name: "Home", href: "/", icon: Home },
  { name: "About", href: "/about", icon: Info },
];

const protectedLinks = [
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Accounts", href: "/accounts", icon: Users },
  { name: "Campaigns", href: "/campaigns", icon: Rocket },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, [pathname]);

  const links = authenticated
    ? [...publicLinks, ...protectedLinks]
    : [...publicLinks, { name: "Login", href: "/login", icon: LogIn }];

  return (
    <div className="flex h-full w-64 flex-col border-r border-gray-200 bg-white p-4">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="h-8 w-8 rounded-lg bg-blue-600 shadow-sm" />
        <span className="text-xl font-bold text-gray-900">SocialGrowth<span className="text-blue-600">AI</span></span>
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {links.map((link) => {
          const LinkIcon = link.icon;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                {
                  "bg-gray-100 text-gray-900": pathname === link.href,
                  "text-gray-600 hover:bg-gray-50 hover:text-gray-900": pathname !== link.href,
                }
              )}
            >
              <LinkIcon className="w-5 h-5" />
              {link.name}
            </Link>
          );
        })}
      </nav>
      {authenticated && (
        <button
          onClick={() => {
            clearAuthSession();
            window.location.href = "/login";
          }}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          Sign out
        </button>
      )}
    </div>
  );
}
