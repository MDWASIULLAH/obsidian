"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity, AlertTriangle, Bot, CheckCircle2, ChevronRight, ExternalLink,
  GitBranch, Lock, RefreshCw, ScanLine, Server, Shield, Wrench, XCircle, Zap,
} from "lucide-react";
import { api, type DashboardData, type Scan } from "@/lib/api";
import { scoreColor, formatDate } from "@/lib/utils";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com").replace(/\/$/, "");
const POLL_MS = 3000;

type LiveDashboard = DashboardData & {
  scan_progress?: number;
  scan_state?: string;
  last_updated?: string | null;
};

type GitHubRepo = {
  id: string;
  name: string;
  full_name: string;
  description: string | null;
  private: boolean;
  language: string | null;
  html_url: string;
  updated_at: string;
};

const agents = [
  ["Threat Modeler", "reasoning"], ["Code Intel", "code"], ["Dependency", "lightweight"], ["Secrets", "lightweight"],
  ["API Security", "code"], ["Container", "code"], ["Cloud", "code"], ["Compliance", "lightweight"],
  ["Attack Simulation", "reasoning"], ["Auto Patcher", "code"], ["Test Generation", "code"], ["Approval", "reasoning"],
];

function StatCard({ icon: Icon, label, value, detail, tone = "cyan" }: any) {
  const tones: Record<string, string> = {
    cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
    green: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    violet: "text-violet-400 bg-violet-500/10 border-violet-500/20",
  };
  return (
    <motion.div className="glass-card-hover p-5 min-w-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-2">{label}</p>
          <p className="text-2xl sm:text-3xl font-bold text-gray-100 truncate">{value}</p>
          <p className="text-xs text-gray-500 mt-1 truncate">{detail}</p>
        </div>
        <div className={`p-2.5 rounded-lg border shrink-0 ${tones[tone] || tones.cyan}`}><Icon className="w-5 h-5" /></div>
      </div>
    </motion.div>
  );
}

function SecurityScore({ score, progress, state }: { score: number; progress: number; state: string }) {
  const scanning = ["queued", "indexing", "scanning", "patching", "testing", "reviewing"].includes(state);
  const display = scanning ? Math.max(0, Math.min(100, progress)) : Math.max(0, Math.min(100, score));
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (display / 100) * circumference;
  const label = scanning ? `Scan ${state}` : state === "completed" ? (display >= 80 ? "Excellent" : display >= 60 ? "Good" : display >= 40 ? "Needs Attention" : "Critical Risk") : "Not assessed";

  return (
    <motion.div className="glass-card p-6 h-full flex flex-col items-center justify-center">
      <div className="w-full flex items-center justify-between mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider">Security Score</h3>
        <Shield className="w-4 h-4 text-cyan-400" />
      </div>
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(51,65,85,.7)" strokeWidth="8" />
          <circle cx="60" cy="60" r="54" fill="none" stroke={scanning ? "#06b6d4" : display >= 60 ? "#14b8a6" : "#ef4444"} strokeWidth="8" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className="transition-all duration-700" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${scanning ? "text-cyan-400" : scoreColor(display)}`}>{display}</span>
          <span className="text-[10px] text-gray-500">{scanning ? "% progress" : "/100"}</span>
        </div>
      </div>
      <p className={`text-sm mt-3 capitalize ${scanning ? "text-cyan-300 animate-pulse" : "text-gray-300"}`}>{label}</p>
      <p className="text-xs text-gray-600 mt-1 text-center">{scanning ? "Live pipeline progress" : "Latest completed repository security assessment"}</p>
    </motion.div>
  );
}

function SeverityDistribution({ distribution }: { distribution: Record<string, number> }) {
  const items = [
    ["critical", "Critical", "bg-red-500"], ["high", "High", "bg-orange-500"],
    ["medium", "Medium", "bg-amber-500"], ["low", "Low", "bg-blue-500"], ["info", "Info", "bg-slate-500"],
  ];
  const total = Math.max(1, Object.values(distribution || {}).reduce((a, b) => a + (Number(b) || 0), 0));
  return (
    <motion.div className="glass-card p-6 h-full">
      <div className="flex items-center justify-between mb-5"><h3 className="text-xs text-gray-500 uppercase tracking-wider">Severity Distribution</h3><AlertTriangle className="w-4 h-4 text-amber-400" /></div>
      <div className="space-y-4">
        {items.map(([key, label, color]) => {
          const count = Number(distribution?.[key] || 0); const pct = (count / total) * 100;
          return <div key={key}><div className="flex items-center justify-between mb-1.5"><div className="flex items-center gap-2"><span className={`w-2 h-2 rounded-full ${color}`} /><span className="text-xs text-gray-400">{label}</span></div><span className="text-xs font-mono text-gray-300">{count}</span></div><div className="h-1.5 rounded-full bg-white/5 overflow-hidden"><motion.div className={`h-full rounded-full ${color}`} animate={{ width: `${pct}%` }} /></div></div>;
        })}
      </div>
    </motion.div>
  );
}

function RecentScans({ scans }: { scans: Scan[] }) {
  return (
    <motion.div className="glass-card p-6 h-full">
      <div className="flex items-center justify-between mb-4"><div><h3 className="text-xs text-gray-500 uppercase tracking-wider">Recent Scans</h3><p className="text-[11px] text-gray-600 mt-1">Live security analysis activity</p></div><a href="/dashboard/scans" className="text-xs text-cyan-400 flex items-center gap-1">View all <ChevronRight className="w-3 h-3" /></a></div>
      {scans.length === 0 ? <div className="rounded-lg border border-white/5 py-10 text-center"><ScanLine className="w-8 h-8 text-gray-600 mx-auto mb-3" /><p className="text-sm text-gray-400">Waiting for first scan</p><p className="text-xs text-gray-600 mt-1">The first dashboard visit starts a real repository scan automatically.</p></div> : <div className="space-y-1">{scans.slice(0, 7).map((scan) => <a key={scan.id} href={`/dashboard/scans/${scan.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors"><span className={`w-2 h-2 rounded-full shrink-0 ${scan.status === "completed" ? "bg-emerald-400" : scan.status === "failed" ? "bg-red-400" : "bg-cyan-400 animate-pulse"}`} /><div className="flex-1 min-w-0"><p className="text-sm text-gray-200 truncate">{scan.commit_sha?.slice(0, 8) || "Unknown"} <span className="text-gray-500 ml-1">{scan.branch || "default"}</span></p><p className="text-[11px] text-gray-600 mt-0.5">{scan.created_at ? formatDate(scan.created_at) : "—"}</p></div><div className="text-right shrink-0"><p className="text-[10px] uppercase text-gray-500">{scan.status}</p><p className={`text-xs font-mono ${scoreColor(scan.security_score || 0)}`}>{scan.status === "completed" ? scan.security_score : `${scan.total_findings || 0} findings`}</p></div><ChevronRight className="w-4 h-4 text-gray-700" /></a>)}</div>}
    </motion.div>
  );
}

function SystemStatus({ backendOnline, githubOnline, scanState }: { backendOnline: boolean; githubOnline: boolean; scanState: string }) {
  const items = [
    ["Web application", true, "Vercel"], ["GitHub integration", githubOnline, githubOnline ? "Connected" : "Unavailable"],
    ["Security API", backendOnline, backendOnline ? "Connected" : "Unavailable"], ["Scan pipeline", backendOnline && scanState !== "failed", backendOnline ? scanState : "Waiting for API"],
  ];
  return <motion.div className="glass-card p-6"><div className="flex items-center justify-between mb-4"><h3 className="text-xs text-gray-500 uppercase tracking-wider">System Status</h3><Server className="w-4 h-4 text-cyan-400" /></div><div className="space-y-2">{items.map(([label, ok, detail]) => <div key={String(label)} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.02]">{ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}<div className="flex-1 min-w-0"><p className="text-xs text-gray-300">{label}</p><p className="text-[10px] text-gray-600 capitalize">{detail}</p></div><span className={`text-[10px] uppercase ${ok ? "text-emerald-400" : "text-red-400"}`}>{ok ? "Online" : "Offline"}</span></div>)}</div></motion.div>;
}

function GitHubRepositories({ repos, error, onRetry }: { repos: GitHubRepo[]; error: string | null; onRetry: () => void }) {
  return <motion.div className="glass-card p-6"><div className="flex items-center justify-between mb-4"><div><h3 className="text-xs text-gray-500 uppercase tracking-wider">GitHub Repositories</h3><p className="text-[11px] text-gray-600 mt-1">Live repositories available to OBSIDIAN</p></div><a href="/dashboard/repositories" className="text-xs text-cyan-400 flex items-center gap-1">Manage <ChevronRight className="w-3 h-3" /></a></div>{repos.length === 0 ? <div className="py-8 text-center border border-white/5 rounded-lg"><GitBranch className="w-7 h-7 text-gray-600 mx-auto mb-2" /><p className="text-sm text-gray-400">{error ? "GitHub access needs attention" : "No repositories found"}</p><p className="text-xs text-gray-600 mt-1">{error === "AUTH_REQUIRED" || error === "GITHUB_TOKEN_INVALID" ? "Sign in again with GitHub to restore repository access." : error ? "GitHub could not be reached. Try again." : "Your GitHub account currently has no accessible repositories."}</p>{error && <button onClick={onRetry} className="mt-4 inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-xs text-gray-300 hover:bg-white/10"><RefreshCw className="w-3.5 h-3.5" /> Retry GitHub</button>}</div> : <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">{repos.slice(0, 9).map((repo) => <a key={repo.id} href={repo.html_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/5"><GitBranch className="w-4 h-4 text-gray-500 shrink-0" /><div className="min-w-0 flex-1"><p className="text-xs font-medium text-gray-200 truncate">{repo.full_name}</p><p className="text-[10px] text-gray-600 truncate">{repo.language || "Unknown language"}</p></div>{repo.private ? <Lock className="w-3.5 h-3.5 text-amber-400" /> : <ExternalLink className="w-3.5 h-3.5 text-gray-600" />}</a>)}</div>}</motion.div>;
}

export default function DashboardPage() {
  const [data, setData] = useState<LiveDashboard | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [githubOnline, setGithubOnline] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadDashboard = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const dashboard = await api.getDashboard() as LiveDashboard;
      setData(dashboard);
      setBackendOnline(true);
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Security API unavailable:", error);
      setBackendOnline(false);
    } finally {
      setLoading(false);
      if (manual) setRefreshing(false);
    }
  }, []);

  const loadRepos = useCallback(async () => {
    try {
      const response = await fetch("/api/github/repos", { cache: "no-store" });
      const json = await response.json().catch(() => ({}));
      if (!response.ok) {
        setRepos([]);
        setRepoError(typeof json.error === "string" ? json.error : `HTTP_${response.status}`);
        setGithubOnline(false);
        return;
      }
      const nextRepos = Array.isArray(json.repos) ? json.repos : [];
      setRepos(nextRepos);
      setRepoError(null);
      setGithubOnline(true);
    } catch (error) {
      console.error("GitHub repositories unavailable:", error);
      setRepos([]);
      setRepoError("NETWORK_ERROR");
      setGithubOnline(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    loadRepos();
    const dashboardTimer = window.setInterval(() => loadDashboard(), POLL_MS);
    const repoTimer = window.setInterval(loadRepos, 15000);
    return () => { window.clearInterval(dashboardTimer); window.clearInterval(repoTimer); };
  }, [loadDashboard, loadRepos]);

  const displayData = useMemo<LiveDashboard>(() => data || {
    total_repositories: repos.length, active_scans: 0, total_findings: 0, critical_findings: 0,
    average_security_score: 0, patches_generated: 0, tests_generated: 0, recent_scans: [],
    severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 }, scan_progress: 0, scan_state: "idle",
  }, [data, repos.length]);

  // GitHub is the source of truth for repository visibility. The backend may
  // legitimately report zero before the first repository is scanned.
  const repositoryCount = repos.length > 0 ? repos.length : displayData.total_repositories;

  if (loading) return <div className="flex items-center justify-center min-h-[60vh]"><div className="text-center"><Shield className="w-10 h-10 text-cyan-400 animate-pulse mx-auto mb-4" /><p className="text-sm text-gray-400">Loading live security overview…</p></div></div>;

  const state = displayData.scan_state || "idle";
  const active = displayData.active_scans > 0;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 w-full min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div><h1 className="text-xl sm:text-2xl font-bold text-gray-100">Security Overview</h1><p className="text-xs sm:text-sm text-gray-500 mt-1">Live security posture, repository activity and scan pipeline status</p></div>
        <div className="flex items-center gap-3"><span className="text-[10px] text-gray-600">{lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : "Live"}</span><button onClick={() => { loadDashboard(true); loadRepos(); }} disabled={refreshing} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-xs text-gray-300 hover:bg-white/10 disabled:opacity-50"><RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh</button></div>
      </div>

      {active && <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 flex items-center gap-3"><Activity className="w-4 h-4 text-cyan-400 animate-pulse" /><div className="flex-1"><p className="text-xs text-cyan-200">Security scan in progress</p><p className="text-[10px] text-gray-500 mt-0.5">{state} · {displayData.scan_progress || 0}% pipeline progress · overview updates automatically</p></div><a href="/dashboard/scans" className="text-xs text-cyan-400">Open scans</a></div>}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4">
        <StatCard icon={GitBranch} label="Repositories" value={repositoryCount} detail={githubOnline ? `${repos.length} from GitHub` : "GitHub unavailable"} />
        <StatCard icon={AlertTriangle} label="Total Findings" value={displayData.total_findings} detail={`${displayData.critical_findings} critical`} tone="red" />
        <StatCard icon={Wrench} label="Patches Generated" value={displayData.patches_generated} detail={`${displayData.tests_generated} tests generated`} tone="green" />
        <StatCard icon={Bot} label="Active Scans" value={displayData.active_scans} detail={active ? `Live: ${state}` : "No active scan"} tone="violet" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        <div className="lg:col-span-3"><SecurityScore score={Math.round(displayData.average_security_score)} progress={displayData.scan_progress || 0} state={state} /></div>
        <div className="lg:col-span-3"><SeverityDistribution distribution={displayData.severity_distribution} /></div>
        <div className="lg:col-span-6"><RecentScans scans={displayData.recent_scans || []} /></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2 glass-card p-6"><div className="flex items-center justify-between mb-4"><div><h3 className="text-xs text-gray-500 uppercase tracking-wider">Security Agents</h3><p className="text-[11px] text-gray-600 mt-1">Autonomous analysis and remediation pipeline</p></div><Zap className="w-4 h-4 text-cyan-400" /></div><div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2">{agents.map(([name, tier]) => <div key={name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5"><div className="flex items-center gap-2 mb-1.5"><span className={`w-1.5 h-1.5 rounded-full ${backendOnline ? "bg-emerald-400" : "bg-gray-600"}`} /><span className="text-xs text-gray-300 truncate">{name}</span></div><p className="text-[10px] text-gray-600 uppercase">{tier}</p></div>)}</div></div>
        <SystemStatus backendOnline={backendOnline} githubOnline={githubOnline} scanState={state} />
      </div>

      <GitHubRepositories repos={repos} error={repoError} onRetry={loadRepos} />

      <div className="glass-card p-6 border-cyan-500/10"><div className="flex items-center justify-between mb-4"><div><h3 className="text-xs text-gray-500 uppercase tracking-wider flex items-center gap-2"><Activity className="w-4 h-4 text-cyan-400" /> Live Scan Telemetry</h3><p className="text-[11px] text-gray-600 mt-1">This overview polls the real backend every 3 seconds.</p></div><span className={`text-[10px] uppercase ${backendOnline ? "text-emerald-400" : "text-red-400"}`}>{backendOnline ? "Connected" : "Offline"}</span></div><div className="grid grid-cols-2 sm:grid-cols-4 gap-3"><div className="rounded-lg border border-white/5 bg-white/[0.02] p-3"><p className="text-[10px] text-gray-600 uppercase">Pipeline</p><p className="text-sm text-gray-200 mt-1 capitalize">{state}</p></div><div className="rounded-lg border border-white/5 bg-white/[0.02] p-3"><p className="text-[10px] text-gray-600 uppercase">Progress</p><p className="text-sm text-cyan-300 mt-1">{displayData.scan_progress || 0}%</p></div><div className="rounded-lg border border-white/5 bg-white/[0.02] p-3"><p className="text-[10px] text-gray-600 uppercase">Findings</p><p className="text-sm text-gray-200 mt-1">{displayData.total_findings}</p></div><div className="rounded-lg border border-white/5 bg-white/[0.02] p-3"><p className="text-[10px] text-gray-600 uppercase">Backend</p><p className="text-sm text-emerald-300 mt-1">{backendOnline ? "Online" : "Offline"}</p></div></div></div>
    </motion.div>
  );
}
