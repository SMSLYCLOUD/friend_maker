"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Users, BarChart3, Settings, Rocket } from "lucide-react";
import clsx from "clsx";

const links = [
  { name: "Home", href: "/", icon: Home },
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Accounts", href: "/accounts", icon: Users },
  { name: "Campaigns", href: "/campaigns", icon: Rocket },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

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
    </div>
  );
}