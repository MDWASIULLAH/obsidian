"use client";

import { useState } from "react";
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
  Menu,
  X,
  LogOut,
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

function Navigation({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3 sm:p-4 space-y-1 overscroll-contain [scrollbar-width:thin] [scrollbar-color:rgba(107,114,128,.45)_transparent]">
      {navItems.map((item) => {
        const isActive = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 min-w-0",
              isActive
                ? "bg-surface-800 text-gray-100 font-medium border border-surface-700"
                : "text-gray-400 hover:text-gray-200 hover:bg-surface-800/50"
            )}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="truncate">{item.label}</span>
            {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-500 shrink-0" />}
          </Link>
        );
      })}
    </nav>
  );
}

function UserProfile({ session, compact = false }: { session: any; compact?: boolean }) {
  if (!session?.user) return null;
  return (
    <div className={cn("flex items-center gap-3", compact ? "p-3" : "mt-3 pt-3 border-t border-surface-800")}>
      <img
        src={session.user.image || `https://avatar.vercel.sh/${session.user.name || "user"}`}
        alt="GitHub profile"
        className="w-9 h-9 rounded-full border border-surface-700 bg-surface-800 shrink-0"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-100 truncate">{session.user.name || "GitHub user"}</p>
        <p className="text-xs text-gray-400 truncate">{session.user.email || ""}</p>
      </div>
      <button
        type="button"
        onClick={() => signOut({ callbackUrl: "/" })}
        className="p-2 text-gray-400 hover:text-red-300 rounded-lg hover:bg-red-500/10 transition-colors shrink-0"
        title="Sign out of GitHub"
        aria-label="Sign out"
      >
        <LogOut className="w-4 h-4" />
      </button>
    </div>
  );
}

function Sidebar({ pathname, session, mobile = false, onClose }: { pathname: string; session: any; mobile?: boolean; onClose?: () => void }) {
  return (
    <aside className={cn(
      "bg-surface-900 border-surface-800 flex flex-col min-h-0",
      mobile ? "h-full w-[min(86vw,320px)] border-r" : "hidden lg:flex lg:w-64 lg:flex-shrink-0 lg:border-r"
    )}>
      <div className="p-4 sm:p-6 border-b border-surface-800 shrink-0">
        <div className="flex items-center justify-between">
          <Link href="/dashboard" onClick={onClose} className="flex items-center gap-3 min-w-0">
            <div className="relative flex items-center justify-center w-8 h-8 rounded bg-primary-500/10 shrink-0">
              <Shield className="w-5 h-5 text-primary-500" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold tracking-tight text-gray-100">OBSIDIAN</h1>
              <p className="text-[10px] text-gray-400 tracking-widest uppercase">Security Center</p>
            </div>
          </Link>
          {mobile && (
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-100 rounded-lg hover:bg-surface-800" aria-label="Close navigation">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      <Navigation pathname={pathname} onNavigate={onClose} />

      <div className="p-3 sm:p-4 border-t border-surface-800 shrink-0">
        <div className="glass-card p-3 hidden sm:block">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-teal-500" />
            <span className="text-xs font-medium text-gray-300">Pipeline Status</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="status-dot-active" />
            <span className="text-xs text-gray-400">All systems operational</span>
          </div>
        </div>
        <UserProfile session={session} compact />
      </div>
    </aside>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession({
    required: true,
    onUnauthenticated() {
      router.push("/");
    },
  });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-surface-950 flex items-center justify-center">
        <div className="w-8 h-8 rounded-full bg-primary-500 animate-ping" />
      </div>
    );
  }

  const pageLabel = navItems.find((i) => i.href === pathname)?.label || "Dashboard";

  return (
    <div className="flex h-[100dvh] min-h-0 overflow-hidden bg-surface-950">
      <Sidebar pathname={pathname} session={session} />

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation overlay" />
          <div className="relative h-full">
            <Sidebar pathname={pathname} session={session} mobile onClose={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      <main className="flex-1 min-w-0 min-h-0 overflow-y-auto overflow-x-hidden">
        <header className="sticky top-0 z-40 border-b border-white/5 bg-surface-950/90 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-3 px-3 py-3 sm:px-6 lg:px-8 lg:py-4">
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                className="lg:hidden p-2 rounded-lg text-gray-300 hover:bg-white/5 shrink-0"
                aria-label="Open navigation"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="min-w-0">
                <h2 className="text-base sm:text-lg font-semibold text-gray-100 truncate">{pageLabel}</h2>
                <p className="text-[10px] sm:text-xs text-gray-500 truncate">Autonomous AI Security Engineering Organization</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-4 shrink-0">
              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input type="text" placeholder="Search..." className="pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:border-cyber-cyan/30 focus:ring-1 focus:ring-cyber-cyan/20 w-48 lg:w-64 transition-all" />
              </div>
              <Link href="/dashboard/settings" className="p-2 rounded-lg hover:bg-white/5 transition-colors" aria-label="Open settings">
                <Settings className="w-5 h-5 text-gray-400" />
              </Link>
            </div>
          </div>
        </header>

        <div className="p-4 sm:p-6 lg:p-8 min-w-0">{children}</div>
      </main>
    </div>
  );
}
