"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { cn } from "@/lib/utils";
import {
  Shield,
  LayoutDashboard,
  GitBranch,
  Search,
  Bot,
  Network,
  FileWarning,
  FileText,
  Settings,
  Zap,
  Cpu,
  TrendingUp,
  Swords,
  DollarSign,
  History,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/repositories", label: "Repositories", icon: GitBranch },
  { href: "/dashboard/scans", label: "Scans", icon: Search },
  { href: "/dashboard/threats", label: "Threats", icon: FileWarning },
  { href: "/dashboard/agents", label: "Agents", icon: Bot },
  { href: "/dashboard/graph", label: "Knowledge Graph", icon: Network },
  { href: "/dashboard/digital-twin", label: "Digital Twin", icon: Cpu },
  { href: "/dashboard/threat-evolution", label: "Threat Evolution", icon: TrendingUp },
  { href: "/dashboard/attack-chain", label: "Attack Chain", icon: Swords },
  { href: "/dashboard/business-impact", label: "Business Impact", icon: DollarSign },
  { href: "/dashboard/security-timeline", label: "Security Timeline", icon: History },
  { href: "/dashboard/reports", label: "Reports", icon: FileText },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession({
    required: true,
    onUnauthenticated() {
      router.push("/");
    },
  });

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-surface-950 flex items-center justify-center">
        <div className="w-8 h-8 rounded-full bg-primary-500 animate-ping" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ────────────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 border-r border-surface-800 bg-surface-900 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-surface-800">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="relative flex items-center justify-center w-8 h-8 rounded bg-primary-500/10">
              <Shield className="w-5 h-5 text-primary-500" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-gray-100">
                OBSIDIAN
              </h1>
              <p className="text-[10px] text-gray-400 tracking-widest uppercase">
                Security Center
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
                  isActive
                    ? "bg-surface-800 text-gray-100 font-medium border border-surface-700"
                    : "text-gray-400 hover:text-gray-200 hover:bg-surface-800/50"
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-500" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-surface-800">
          <div className="glass-card p-3">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-teal-500" />
              <span className="text-xs font-medium text-gray-300">
                Pipeline Status
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="status-dot-active" />
              <span className="text-xs text-gray-400">All systems operational</span>
            </div>
          </div>
          
          {/* User Profile */}
          {session?.user && (
            <div className="mt-4 pt-4 border-t border-surface-800 flex items-center gap-3">
              <img 
                src={session.user.image || `https://avatar.vercel.sh/${session.user.name}`} 
                alt="Avatar" 
                className="w-10 h-10 rounded-full border border-surface-700 bg-surface-800" 
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-100 truncate">{session.user.name}</p>
                <p className="text-xs text-gray-400 truncate">{session.user.email}</p>
              </div>
              <button 
                onClick={() => signOut({ callbackUrl: '/' })}
                className="p-1.5 text-gray-400 hover:text-gray-100 rounded-lg hover:bg-surface-800 transition-colors"
                title="Sign out"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main Content ───────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b border-white/5 bg-surface-950/80 backdrop-blur-xl">
          <div className="flex items-center justify-between px-8 py-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-100">
                {navItems.find((i) => i.href === pathname)?.label || "Dashboard"}
              </h2>
              <p className="text-xs text-gray-500">
                Autonomous AI Security Engineering Organization
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:border-cyber-cyan/30 focus:ring-1 focus:ring-cyber-cyan/20 w-64 transition-all"
                />
              </div>
              <button className="p-2 rounded-lg hover:bg-white/5 transition-colors">
                <Settings className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
