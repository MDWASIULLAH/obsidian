"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ────────────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 border-r border-white/5 bg-surface-950/80 backdrop-blur-xl flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-white/5">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="relative">
              <Shield className="w-8 h-8 text-cyber-cyan" />
              <div className="absolute inset-0 w-8 h-8 bg-cyber-cyan/20 rounded-full blur-lg group-hover:bg-cyber-cyan/30 transition-all" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-glow-cyan">SENTINEL</span>{" "}
                <span className="text-gray-400 font-light">AI X</span>
              </h1>
              <p className="text-[10px] text-gray-500 tracking-widest uppercase">
                Security Engineering
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
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
                    ? "bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyber-cyan shadow-[0_0_6px_rgba(0,240,255,0.5)]" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-white/5">
          <div className="glass-card p-3">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-cyber-green" />
              <span className="text-xs font-medium text-gray-300">
                Pipeline Status
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="status-dot-active" />
              <span className="text-xs text-gray-400">All systems operational</span>
            </div>
          </div>
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
