"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  GitBranch,
  Bot,
  Wrench,
  TestTube,
  TrendingUp,
  Clock,
  ChevronRight,
  Activity,
  RefreshCw,
  ExternalLink,
  Server,
  CheckCircle2,
  XCircle,
  Info,
  Zap,
  Lock,
  ScanLine,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { api, type DashboardData, type Scan } from "@/lib/api";
import { scoreColor, formatDate } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
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

function StatCard({ icon: Icon, label, value, detail, tone = "cyan" }: any) {
  const tones: Record<string, string> = {
    cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
    green: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    violet: "text-violet-400 bg-violet-500/10 border-violet-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  };
  return (
    <motion.div variants={itemVariants} className="glass-card-hover p-5 min-w-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-2">{label}</p>
          <p className="text-2xl sm:text-3xl font-bold text-gray-100 truncate">{value}</p>
          {detail && <p className="text-xs text-gray-500 mt-1 truncate">{detail}</p>}
        </div>
        <div className={`p-2.5 rounded-lg border shrink-0 ${tones[tone] || tones.cyan}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </motion.div>
  );
}

function SecurityScore({ score }: { score: number }) {
  const safeScore = Math.max(0, Math.min(100, Number.isFinite(score) ? score : 0));
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (safeScore / 100) * circumference;
  const label = safeScore >= 80 ? "Excellent" : safeScore >= 60 ? "Good" : safeScore >= 40 ? "Needs Attention" : "Critical Risk";

  return (
    <motion.div variants={itemVariants} className="glass-card p-6 h-full flex flex-col items-center justify-center">
      <div className="w-full flex items-center justify-between mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider">Security Score</h3>
        <Shield className="w-4 h-4 text-cyan-400" />
      </div>
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(51,65,85,.7)" strokeWidth="8" />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={safeScore >= 60 ? "#14b8a6" : "#ef4444"}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${scoreColor(safeScore)}`}>{safeScore}</span>
          <span className="text-[10px] text-gray-500">/100</span>
        </div>
      </div>
      <p className="text-sm text-gray-300 mt-3">{label}</p>
      <p className="text-xs text-gray-600 mt-1 text-center">Average repository security posture</p>
    </motion.div>
  );
}

function SeverityDistribution({ distribution }: { distribution: Record<string, number> }) {
  const items = [
    { key: "critical", label: "Critical", className: "bg-red-500" },
    { key: "high", label: "High", className: "bg-orange-500" },
    { key: "medium", label: "Medium", className: "bg-amber-500" },
    { key: "low", label: "Low", className: "bg-blue-500" },
    { key: "info", label: "Info", className: "bg-slate-500" },
  ];
  const total = Math.max(1, Object.values(distribution || {}).reduce((a, b) => a + (Number(b) || 0), 0));

  return (
    <motion.div variants={itemVariants} className="glass-card p-6 h-full">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider">Severity Distribution</h3>
        <AlertTriangle className="w-4 h-4 text-amber-400" />
      </div>
      <div className="space-y-4">
        {items.map((item) => {
          const count = Number(distribution?.[item.key] || 0);
          const pct = (count / total) * 100;
          return (
            <div key={item.key}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${item.className}`} />
                  <span className="text-xs text-gray-400">{item.label}</span>
                </div>
                <span className="text-xs font-mono text-gray-300">{count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div className={`h-full rounded-full ${item.className}`} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.7 }} />
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

function RecentScans({ scans }: { scans: Scan[] }) {
  return (
    <motion.div variants={itemVariants} className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xs text-gray-500 uppercase tracking-wider">Recent Scans</h3>
          <p className="text-[11px] text-gray-600 mt-1">Latest security analysis activity</p>
        </div>
        <a href="/dashboard/scans" className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
          View all <ChevronRight className="w-3 h-3" />
        </a>
      </div>
      {scans.length === 0 ? (
        <div className="rounded-lg border border-white/5 bg-white/[0.02] py-10 text-center">
          <ScanLine className="w-8 h-8 text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-400">No scans available</p>
          <p className="text-xs text-gray-600 mt-1">Connect the backend and push to a tracked repository to start scanning.</p>
        </div>
      ) : (
        <div className="space-y-1">
          {scans.slice(0, 6).map((scan) => (
            <a key={scan.id} href={`/dashboard/scans/${scan.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors group">
              <span className={`w-2 h-2 rounded-full shrink-0 ${scan.status === "completed" ? "bg-emerald-400" : scan.status === "failed" ? "bg-red-400" : "bg-amber-400 animate-pulse"}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{scan.commit_sha?.slice(0, 8) || "Unknown commit"} <span className="text-gray-500 ml-1">{scan.branch || "default"}</span></p>
                <p className="text-[11px] text-gray-600 mt-0.5">{scan.created_at ? formatDate(scan.created_at) : "No timestamp"}</p>
              </div>
              <div className="flex items-center gap-2 text-xs shrink-0">
                {scan.critical_count > 0 && <span className="text-red-400">C:{scan.critical_count}</span>}
                {scan.high_count > 0 && <span className="text-orange-400">H:{scan.high_count}</span>}
                <span className={`font-mono ${scoreColor(scan.security_score || 0)}`}>{scan.security_score ?? 0}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-700 group-hover:text-gray-400" />
            </a>
          ))}
        </div>
      )}
    </motion.div>
  );
}

function SystemStatus({ backendOnline, githubOnline }: { backendOnline: boolean; githubOnline: boolean }) {
  const items = [
    { label: "Web application", ok: true, detail: "Vercel" },
    { label: "GitHub integration", ok: githubOnline, detail: githubOnline ? "Connected" : "Unavailable" },
    { label: "Security API", ok: backendOnline, detail: backendOnline ? "Connected" : "Not configured" },
    { label: "Live telemetry", ok: backendOnline, detail: backendOnline ? "Available" : "Waiting for API" },
  ];
  return (
    <motion.div variants={itemVariants} className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider">System Status</h3>
        <Server className="w-4 h-4 text-cyan-400" />
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.02]">
            {item.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-gray-600" />}
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-300">{item.label}</p>
              <p className="text-[10px] text-gray-600">{item.detail}</p>
            </div>
            <span className={`text-[10px] uppercase tracking-wider ${item.ok ? "text-emerald-400" : "text-gray-600"}`}>{item.ok ? "Online" : "Offline"}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function GitHubRepositories({ repos }: { repos: GitHubRepo[] }) {
  return (
    <motion.div variants={itemVariants} className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xs text-gray-500 uppercase tracking-wider">GitHub Repositories</h3>
          <p className="text-[11px] text-gray-600 mt-1">Repositories available to OBSIDIAN</p>
        </div>
        <a href="/dashboard/repositories" className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1">Manage <ChevronRight className="w-3 h-3" /></a>
      </div>
      {repos.length === 0 ? (
        <div className="py-8 text-center border border-white/5 rounded-lg bg-white/[0.02]">
          <GitBranch className="w-7 h-7 text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-400">No repositories loaded</p>
          <p className="text-xs text-gray-600 mt-1">Open Repositories to reconnect GitHub access.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {repos.slice(0, 6).map((repo) => (
            <a key={repo.id} href={repo.html_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/5 transition-colors">
              <GitBranch className="w-4 h-4 text-gray-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-gray-200 truncate">{repo.name}</p>
                <p className="text-[10px] text-gray-600 truncate">{repo.language || "Unknown language"}</p>
              </div>
              {repo.private ? <Lock className="w-3.5 h-3.5 text-amber-400" /> : <ExternalLink className="w-3.5 h-3.5 text-gray-600" />}
            </a>
          ))}
        </div>
      )}
    </motion.div>
  );
}

const agents = [
  ["Threat Modeler", "reasoning"], ["Code Intel", "code"], ["Dependency", "lightweight"], ["Secrets", "lightweight"],
  ["API Security", "code"], ["Container", "code"], ["Cloud", "code"], ["Compliance", "lightweight"],
  ["Attack Simulation", "reasoning"], ["Auto Patcher", "code"], ["Test Generation", "code"], ["Approval", "reasoning"],
];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [githubOnline, setGithubOnline] = useState(false);
  const [liveFindings, setLiveFindings] = useState<any[]>([]);
  const { data: session } = useSession();

  async function loadDashboard() {
    setRefreshing(true);
    try {
      if (API_URL) {
        try {
          const dashboard = await api.getDashboard();
          setData(dashboard);
          setBackendOnline(true);
        } catch (error) {
          console.error("Security API unavailable:", error);
          setBackendOnline(false);
        }
      } else {
        setBackendOnline(false);
      }

      try {
        const response = await fetch("/api/github/repos", { cache: "no-store" });
        if (response.ok) {
          const json = await response.json();
          const loaded = Array.isArray(json.repos) ? json.repos : [];
          setRepos(loaded);
          setGithubOnline(true);
        } else {
          setGithubOnline(false);
        }
      } catch (error) {
        console.error("GitHub repositories unavailable:", error);
        setGithubOnline(false);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, [session]);

  useEffect(() => {
    if (!API_URL || typeof window === "undefined") return;
    const wsUrl = API_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:") + "/api/v1/ws/dashboard";
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "live_finding") setLiveFindings((prev) => [message.data, ...prev].slice(0, 5));
        } catch {}
      };
    } catch {}
    return () => ws?.close();
  }, []);

  const displayData = useMemo<DashboardData>(() => data || {
    total_repositories: repos.length,
    active_scans: 0,
    total_findings: 0,
    critical_findings: 0,
    average_security_score: 0,
    patches_generated: 0,
    tests_generated: 0,
    recent_scans: [],
    severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  }, [data, repos.length]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Shield className="w-10 h-10 text-cyan-400 animate-pulse mx-auto mb-4" />
          <p className="text-sm text-gray-400">Loading security overview...</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6 w-full min-w-0">
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100">Security Overview</h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">Complete security posture, repository activity and agent status</p>
        </div>
        <button onClick={loadDashboard} disabled={refreshing} className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-xs text-gray-300 hover:bg-white/10 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
        </button>
      </motion.div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4">
        <StatCard icon={GitBranch} label="Repositories" value={displayData.total_repositories} detail={githubOnline ? "GitHub connected" : "GitHub unavailable"} />
        <StatCard icon={AlertTriangle} label="Total Findings" value={displayData.total_findings} detail={`${displayData.critical_findings} critical`} tone="red" />
        <StatCard icon={Wrench} label="Patches Generated" value={displayData.patches_generated} detail={`${displayData.tests_generated} tests generated`} tone="green" />
        <StatCard icon={Bot} label="Active Scans" value={displayData.active_scans} detail={backendOnline ? "Security API connected" : "Backend not configured"} tone="violet" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        <div className="lg:col-span-3"><SecurityScore score={Math.round(displayData.average_security_score)} /></div>
        <div className="lg:col-span-3"><SeverityDistribution distribution={displayData.severity_distribution} /></div>
        <div className="lg:col-span-6"><RecentScans scans={displayData.recent_scans || []} /></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2">
          <motion.div variants={itemVariants} className="glass-card p-6 h-full">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs text-gray-500 uppercase tracking-wider">Security Agents</h3>
                <p className="text-[11px] text-gray-600 mt-1">Autonomous analysis and remediation pipeline</p>
              </div>
              <Zap className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2">
              {agents.map(([name, tier]) => (
                <div key={name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:border-cyan-500/20 transition-colors">
                  <div className="flex items-center gap-2 mb-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /><span className="text-xs text-gray-300 truncate">{name}</span></div>
                  <p className="text-[10px] text-gray-600 uppercase">{tier}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
        <SystemStatus backendOnline={backendOnline} githubOnline={githubOnline} />
      </div>

      <GitHubRepositories repos={repos} />

      <motion.div variants={itemVariants} className="glass-card p-6 border-cyan-500/10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xs text-gray-500 uppercase tracking-wider flex items-center gap-2"><Activity className="w-4 h-4 text-cyan-400" /> Live Agent Telemetry</h3>
            <p className="text-[11px] text-gray-600 mt-1">Real-time findings emitted by the security agent backend</p>
          </div>
          <span className={`text-[10px] uppercase tracking-wider ${backendOnline ? "text-emerald-400" : "text-gray-600"}`}>{backendOnline ? "Connected" : "Not connected"}</span>
        </div>
        {liveFindings.length === 0 ? (
          <div className="py-8 text-center rounded-lg border border-white/5 bg-white/[0.02]">
            <Activity className="w-7 h-7 text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400">No live findings</p>
            <p className="text-xs text-gray-600 mt-1">{backendOnline ? "Waiting for agent events..." : "Set NEXT_PUBLIC_API_URL in Vercel to enable backend telemetry."}</p>
          </div>
        ) : (
          <div className="space-y-2">{liveFindings.map((finding, index) => (
            <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5">
              <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${finding.severity === "critical" ? "bg-red-500" : finding.severity === "high" ? "bg-orange-500" : "bg-amber-500"}`} />
              <div className="min-w-0"><p className="text-sm text-gray-200 truncate">{finding.title || "Security finding"}</p><p className="text-[11px] text-gray-600 mt-1">{finding.repo || "Unknown repository"}</p></div>
            </div>
          ))}</div>
        )}
      </motion.div>

      {!backendOnline && (
        <motion.div variants={itemVariants} className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <Info className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div><p className="text-xs font-medium text-amber-300">Security backend is not connected to this Vercel deployment.</p><p className="text-[11px] text-gray-500 mt-1">The overview remains usable and GitHub data is loaded independently. To enable real findings, scans, scores, patches and live telemetry, configure NEXT_PUBLIC_API_URL in Vercel with your deployed backend URL.</p></div>
        </motion.div>
      )}
    </motion.div>
  );
}
