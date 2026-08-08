"use client";

import { useEffect, useState } from "react";
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
} from "lucide-react";
import { useSession } from "next-auth/react";
import { api, type DashboardData, type Scan } from "@/lib/api";
import {
  formatDate,
  formatDuration,
  scoreColor,
  scoreGradient,
  statusColor,
  severityBadge,
} from "@/lib/utils";

// ── Animation Variants ─────────────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

// ── Stat Card Component ────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  trend?: string;
  color: string;
}) {
  return (
    <motion.div variants={itemVariants} className="glass-card-hover p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className="text-2xl font-bold text-gray-100">{value}</p>
          {trend && (
            <p className="text-xs text-teal-500 mt-1 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              {trend}
            </p>
          )}
        </div>
        <div
          className="p-2.5 rounded-lg"
          style={{ background: `${color}15`, border: `1px solid ${color}30` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
    </motion.div>
  );
}

// ── Security Score Gauge ───────────────────────────────────

function SecurityScoreGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 58;
  const offset = circumference - (score / 100) * circumference;

  return (
    <motion.div
      variants={itemVariants}
      className="glass-card p-6 flex flex-col items-center justify-center"
    >
      <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">
        Security Score
      </h3>
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 -rotate-90" viewBox="0 0 128 128">
          {/* Background ring */}
          <circle
            cx="64"
            cy="64"
            r="58"
            fill="none"
            stroke="rgba(30,41,59,0.8)"
            strokeWidth="8"
          />
          {/* Score ring */}
          <circle
            cx="64"
            cy="64"
            r="58"
            fill="none"
            stroke="url(#scoreGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000"
          />
          <defs>
            <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop
                offset="0%"
                stopColor={score >= 60 ? "#14b8a6" : "#ef4444"}
              />
              <stop
                offset="100%"
                stopColor={score >= 60 ? "#10b981" : "#f97316"}
              />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${scoreColor(score)}`}>
            {score}
          </span>
          <span className="text-xs text-gray-500">/100</span>
        </div>
      </div>
      <p className="text-sm text-gray-400 mt-3">
        {score >= 80
          ? "Excellent"
          : score >= 60
          ? "Good"
          : score >= 40
          ? "Needs Attention"
          : "Critical Risk"}
      </p>
    </motion.div>
  );
}

// ── Severity Distribution ──────────────────────────────────

function SeverityChart({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0) || 1;
  const items = [
    { key: "critical", label: "Critical", color: "#ef4444" },
    { key: "high", label: "High", color: "#f97316" },
    { key: "medium", label: "Medium", color: "#f59e0b" },
    { key: "low", label: "Low", color: "#3b82f6" },
    { key: "info", label: "Info", color: "#94a3b8" },
  ];

  return (
    <motion.div variants={itemVariants} className="glass-card p-6">
      <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">
        Severity Distribution
      </h3>
      <div className="space-y-3">
        {items.map((item) => {
          const count = distribution[item.key] || 0;
          const pct = (count / total) * 100;
          return (
            <div key={item.key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-gray-400">{item.label}</span>
                </div>
                <span className="text-xs font-mono text-gray-300">{count}</span>
              </div>
              <div className="progress-bar">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: item.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

// ── Recent Scans Table ─────────────────────────────────────

function RecentScans({ scans }: { scans: Scan[] }) {
  return (
    <motion.div variants={itemVariants} className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider">
          Recent Scans
        </h3>
        <a
          href="/dashboard/scans"
          className="text-xs text-cyber-cyan hover:text-cyber-cyan/80 flex items-center gap-1"
        >
          View all <ChevronRight className="w-3 h-3" />
        </a>
      </div>
      <div className="space-y-2">
        {scans.length === 0 ? (
          <div className="text-center py-8">
            <Activity className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No scans yet</p>
            <p className="text-xs text-gray-600 mt-1">
              Push to a tracked repository to trigger a scan
            </p>
          </div>
        ) : (
          scans.map((scan) => (
            <a
              key={scan.id}
              href={`/dashboard/scans/${scan.id}`}
              className="flex items-center gap-4 p-3 rounded-lg hover:bg-white/5 transition-colors group"
            >
              <div
                className={`status-dot ${
                  scan.status === "completed"
                    ? "status-dot-active"
                    : scan.status === "failed"
                    ? "status-dot-failed"
                    : "status-dot-scanning"
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 font-medium truncate">
                  {scan.commit_sha.slice(0, 8)}
                  <span className="text-gray-500 ml-2 font-normal">
                    {scan.branch}
                  </span>
                </p>
                <p className="text-xs text-gray-500">{formatDate(scan.created_at)}</p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                {scan.critical_count > 0 && (
                  <span className="badge-critical">{scan.critical_count}</span>
                )}
                {scan.high_count > 0 && (
                  <span className="badge-high">{scan.high_count}</span>
                )}
                <span className={`font-mono ${scoreColor(scan.security_score)}`}>
                  {scan.security_score}
                </span>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
            </a>
          ))
        )}
      </div>
    </motion.div>
  );
}

// ── Main Dashboard Page ────────────────────────────────────

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [liveFindings, setLiveFindings] = useState<any[]>([]);

  const { data: session } = useSession();

  useEffect(() => {
    // Setup WebSocket for Live Agent Telemetry
    const ws = new WebSocket("ws://localhost:8000/api/v1/ws/dashboard");
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "live_finding") {
          setLiveFindings((prev) => [message.data, ...prev].slice(0, 5)); // Keep last 5
        }
      } catch (err) {
        console.error("WS Message Error:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const dashboard = await api.getDashboard();
        
        // Fetch real GitHub stats if session is available
        if (session?.user) {
          try {
            const userId = (session as any).userId;
            if (userId) {
              const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
              const res = await fetch(`${API_URL}/api/v1/auth/github-stats?user_id=${userId}`);
              if (res.ok) {
                const stats = await res.json();
                dashboard.total_repositories = stats.repo_count;
              }
            }
          } catch (e) {
            console.error("Failed to fetch real GitHub stats:", e);
          }
        }
        
        setData(dashboard);
      } catch (err) {
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [session]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <Shield className="w-12 h-12 text-cyber-cyan animate-pulse mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* ── Stat Cards ──────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={GitBranch}
          label="Repositories"
          value={data.total_repositories}
          color="#00f0ff"
        />
        <StatCard
          icon={AlertTriangle}
          label="Total Findings"
          value={data.total_findings}
          trend={data.critical_findings > 0 ? `${data.critical_findings} critical` : undefined}
          color="#ff3366"
        />
        <StatCard
          icon={Wrench}
          label="Patches Generated"
          value={data.patches_generated}
          color="#00ff88"
        />
        <StatCard
          icon={Bot}
          label="Active Scans"
          value={data.active_scans}
          color="#8b5cf6"
        />
      </div>

      {/* ── Score + Severity + Scans ────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3">
          <SecurityScoreGauge score={Math.round(data.average_security_score)} />
        </div>
        <div className="lg:col-span-3">
          <SeverityChart distribution={data.severity_distribution} />
        </div>
        <div className="lg:col-span-6">
          <RecentScans scans={data.recent_scans} />
        </div>
      </div>

      {/* ── Agent Grid ──────────────────────────────────── */}
      <motion.div variants={itemVariants} className="glass-card p-6">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">
          Security Agents
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { name: "Threat Modeler", icon: "🎯", tier: "reasoning" },
            { name: "Code Intel", icon: "🔍", tier: "code" },
            { name: "Dependency", icon: "📦", tier: "lightweight" },
            { name: "Secrets", icon: "🔐", tier: "lightweight" },
            { name: "API Security", icon: "🌐", tier: "code" },
            { name: "Container", icon: "🐳", tier: "code" },
            { name: "Cloud", icon: "☁️", tier: "code" },
            { name: "Compliance", icon: "📋", tier: "lightweight" },
            { name: "Attack Sim", icon: "⚔️", tier: "reasoning" },
            { name: "Auto Patcher", icon: "🔧", tier: "code" },
            { name: "Test Gen", icon: "🧪", tier: "code" },
            { name: "Approval", icon: "✅", tier: "reasoning" },
          ].map((agent) => (
            <div
              key={agent.name}
              className="p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:border-cyber-cyan/20 transition-all group cursor-pointer"
            >
              <div className="text-xl mb-1">{agent.icon}</div>
              <p className="text-xs font-medium text-gray-300 group-hover:text-gray-100 transition-colors">
                {agent.name}
              </p>
              <p className="text-[10px] text-gray-600 mt-0.5">{agent.tier}</p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Live Agent Telemetry ──────────────────────────── */}
      <motion.div variants={itemVariants} className="glass-card p-6 border-primary-500/20">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs text-gray-500 uppercase tracking-wider flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
            Live Agent Telemetry
          </h3>
          <span className="text-[10px] text-gray-400 font-mono">Listening on WSS...</span>
        </div>
        
        {liveFindings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <Activity className="w-6 h-6 mb-2 opacity-50" />
            <p className="text-sm">Waiting for agent telemetry streams...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {liveFindings.map((finding, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-start gap-4 p-3 rounded-lg bg-surface-900 border border-surface-800"
              >
                <div className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${
                  finding.severity === 'critical' ? 'bg-red-500' :
                  finding.severity === 'high' ? 'bg-orange-500' :
                  finding.severity === 'medium' ? 'bg-amber-500' : 'bg-blue-500'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-100 font-medium truncate">{finding.title}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs font-mono text-gray-400">{finding.repo}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(finding.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
