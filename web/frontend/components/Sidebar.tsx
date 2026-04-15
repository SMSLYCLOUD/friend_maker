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
    : [...publicLinks, { name: "Register", href: "/register", icon: UserPlus }, { name: "Login", href: "/login", icon: LogIn }];

  return (
    <div className="flex h-full w-64 flex-col border-r border-gray-800 bg-gray-950 p-4">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="h-8 w-8 rounded-lg bg-blue-600" />
        <span className="text-xl font-bold">SocialGrowthAI</span>
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {links.map((link) => {
          const LinkIcon = link.icon;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-gray-800 hover:text-white",
                {
                  "bg-gray-800 text-white": pathname === link.href,
                  "text-gray-400": pathname !== link.href,
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
          className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white"
        >
          Sign out
        </button>
      )}
    </div>
  );
}
