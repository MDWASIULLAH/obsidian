"use client";

import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  History, Camera, GitBranch, Search, Shield, Zap, TrendingUp, TrendingDown,
  AlertTriangle, CheckCircle, Calendar, RefreshCw, Maximize2, ShieldAlert
} from "lucide-react";
import { api } from "@/lib/api";
import type { Repository, TimelineSnapshotSummary, PostureTrendResponse, TimelineDiffResponse } from "@/lib/api";

const fmtDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

function TrendChart({ trend }: { trend: PostureTrendResponse }) {
  const points = [...trend.data_points].reverse();
  const maxScore = 100;
  
  if (points.length < 2) {
    return (
      <div className="h-40 flex items-center justify-center text-gray-500 text-sm">
        Insufficient data for trend analysis. Capture more snapshots.
      </div>
    );
  }

  return (
    <div className="relative h-48 w-full mt-6 mb-2">
      <svg className="w-full h-full overflow-visible" preserveAspectRatio="none">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((val) => (
          <line key={val} x1="0" y1={`${100 - val}%`} x2="100%" y2={`${100 - val}%`}
            stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="4 4" />
        ))}
        
        {/* Line */}
        <polyline
          points={points.map((p, i) => `${(i / (points.length - 1)) * 100},${100 - (p.security_score ?? 50)}`).join(" ")}
          fill="none"
          stroke={trend.trend === "improving" ? "#10b981" : trend.trend === "degrading" ? "#ef4444" : "#f59e0b"}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {points.map((p, i) => (
          <circle key={i}
            cx={`${(i / (points.length - 1)) * 100}%`} cy={`${100 - (p.security_score ?? 50)}%`}
            r="4"
            fill="#1e1e1e"
            stroke={trend.trend === "improving" ? "#10b981" : trend.trend === "degrading" ? "#ef4444" : "#f59e0b"}
            strokeWidth="2"
            className="cursor-pointer hover:r-6 transition-all"
          >
            <title>{fmtDate(p.captured_at || "")} - Score: {p.security_score}</title>
          </circle>
        ))}
      </svg>
      <div className="absolute inset-0 flex justify-between items-end pb-[-20px] text-[10px] text-gray-500 pointer-events-none mt-full">
        <span>{fmtDate(points[0].captured_at || "")}</span>
        <span>{fmtDate(points[points.length - 1].captured_at || "")}</span>
      </div>
    </div>
  );
}

function DiffViewer({ diff }: { diff: TimelineDiffResponse }) {
  const getIcon = (d: number, inv = false) => {
    if (d === 0) return <span className="text-gray-500">-</span>;
    const good = inv ? d < 0 : d > 0;
    return d > 0 ? (
      <TrendingUp className={`w-4 h-4 ${good ? 'text-emerald-400' : 'text-red-400'}`} />
    ) : (
      <TrendingDown className={`w-4 h-4 ${good ? 'text-emerald-400' : 'text-red-400'}`} />
    );
  };

  const getDeltaStr = (d: number) => d > 0 ? `+${d}` : `${d}`;
  const getDeltaColor = (d: number, inv = false) => {
    if (d === 0) return "text-gray-500";
    const good = inv ? d < 0 : d > 0;
    return good ? "text-emerald-400" : "text-red-400";
  };

  return (
    <div className="bg-surface-900 border border-white/5 rounded-xl p-6">
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <Maximize2 className="w-4 h-4 text-purple-400" /> Snapshot Comparison
      </h3>
      <div className="grid grid-cols-3 gap-4 mb-4 text-xs font-mono text-gray-400 border-b border-white/5 pb-2">
        <div>Metric</div>
        <div className="text-right">{fmtDate(diff.snapshot_a.captured_at!)} (A)</div>
        <div className="text-right">{fmtDate(diff.snapshot_b.captured_at!)} (B)</div>
      </div>

      <div className="space-y-3 text-sm">
        {[
          { label: "Security Score", stat: diff.security_score, inv: false },
          { label: "Risk Score", stat: diff.risk_score, inv: true, isFloat: true },
          { label: "Total Threats", stat: diff.total_threats, inv: true },
          { label: "Critical Findings", stat: diff.critical_findings, inv: true },
          { label: "Total Assets", stat: diff.total_assets, inv: false },
          { label: "Attack Chains", stat: diff.attack_chain_count, inv: true },
        ].map((m) => (
          <div key={m.label} className="grid grid-cols-3 gap-4 items-center">
            <div className="text-gray-300 font-medium">{m.label}</div>
            <div className="text-right text-gray-400 font-mono">
              {m.isFloat ? Number(m.stat.before).toFixed(2) : m.stat.before}
            </div>
            <div className="text-right font-mono flex items-center justify-end gap-2">
              <span className="text-gray-400">{m.isFloat ? Number(m.stat.after).toFixed(2) : m.stat.after}</span>
              <span className={`flex items-center gap-1 w-12 justify-end text-xs ${getDeltaColor(m.stat.delta, m.inv)}`}>
                {m.stat.delta !== 0 && getDeltaStr(m.isFloat ? Number(Number(m.stat.delta).toFixed(2)) : m.stat.delta)}
                {getIcon(m.stat.delta, m.inv)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SecurityTimelinePage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [timeline, setTimeline] = useState<TimelineSnapshotSummary[]>([]);
  const [trend, setTrend] = useState<PostureTrendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [capturing, setCapturing] = useState(false);
  
  const [selectedSnapshots, setSelectedSnapshots] = useState<string[]>([]);
  const [diff, setDiff] = useState<TimelineDiffResponse | null>(null);

  useEffect(() => {
    api.listRepositories().then((r) => { setRepos(r); if (r.length) setSelectedRepo(r[0].full_name); });
  }, []);

  const loadData = async () => {
    if (!selectedRepo) return;
    setLoading(true);
    try {
      const [tl, tr] = await Promise.all([
        api.getSecurityTimeline(selectedRepo, 50),
        api.getPostureTrend(selectedRepo, 30)
      ]);
      setTimeline(tl);
      setTrend(tr);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [selectedRepo]);

  const handleCapture = async () => {
    if (!selectedRepo) return;
    setCapturing(true);
    try {
      await api.captureSecuritySnapshot(selectedRepo, "manual");
      await loadData();
    } finally {
      setCapturing(false);
    }
  };

  const toggleSnapshot = (id: string) => {
    setSelectedSnapshots(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  useEffect(() => {
    if (selectedSnapshots.length === 2) {
      // Diff them (older is A, newer is B)
      const a = timeline.find(t => t.id === selectedSnapshots[0])!;
      const b = timeline.find(t => t.id === selectedSnapshots[1])!;
      const oldId = new Date(a.captured_at).getTime() < new Date(b.captured_at).getTime() ? a.id : b.id;
      const newId = oldId === a.id ? b.id : a.id;
      
      api.diffSecuritySnapshots(oldId, newId).then(setDiff);
    } else {
      setDiff(null);
    }
  }, [selectedSnapshots, timeline]);

  return (
    <div className="flex flex-col h-full bg-surface-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
            <History className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Security Timeline</h1>
            <p className="text-xs text-gray-500">Historical snapshots, diffs, and repository posture evolution</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-surface-900 border border-white/10 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-purple-400/50">
            {repos.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}</option>)}
          </select>
          <button onClick={loadData} disabled={loading}
            className="p-2 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button onClick={handleCapture} disabled={capturing}
            className="flex items-center gap-2 px-3 py-2 bg-purple-500/20 border border-purple-500/30 rounded-lg text-purple-400 text-sm hover:bg-purple-500/30 transition-colors disabled:opacity-50">
            <Camera className={`w-4 h-4 ${capturing ? "animate-spin" : ""}`} />
            Capture Snapshot
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Timeline Sidebar */}
        <div className="w-80 border-r border-white/5 bg-surface-950 flex flex-col">
          <div className="p-4 border-b border-white/5">
            <h3 className="text-sm font-semibold text-white mb-1">Snapshots</h3>
            <p className="text-xs text-gray-500">Select two to compare structural drift</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {timeline.map((t) => {
              const isSelected = selectedSnapshots.includes(t.id);
              return (
                <button key={t.id} onClick={() => toggleSnapshot(t.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    isSelected 
                      ? "bg-purple-500/10 border-purple-500/30" 
                      : "bg-surface-900 border-white/5 hover:border-white/20 hover:bg-white/5"
                  }`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-mono text-gray-400">{fmtDate(t.captured_at)}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                      t.trigger === "manual" ? "bg-blue-500/20 text-blue-400" : "bg-emerald-500/20 text-emerald-400"
                    }`}>
                      {t.trigger}
                    </span>
                  </div>
                  <div className="flex gap-4">
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase">Score</div>
                      <div className="text-lg font-bold" style={{ color: t.security_score >= 80 ? "#10b981" : t.security_score >= 50 ? "#f59e0b" : "#ef4444" }}>
                        {t.security_score}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase">Risk</div>
                      <div className="text-lg font-bold text-gray-300">{t.risk_score.toFixed(1)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 uppercase">Threats</div>
                      <div className="text-lg font-bold text-red-400">{t.total_threats}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto bg-surface-900/30 p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            
            {/* Diff Viewer (if 2 selected) */}
            <AnimatePresence>
              {diff && (
                <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
                  <DiffViewer diff={diff} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Posture Trend */}
            {trend && (
              <div className="bg-surface-900 border border-white/5 rounded-xl p-6">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-emerald-400" /> 30-Day Posture Trend
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">Repository security health evolution</p>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-right">
                      <div className="text-xs text-gray-500 uppercase">Trend</div>
                      <div className={`text-sm font-bold capitalize ${
                        trend.trend === "improving" ? "text-emerald-400" : trend.trend === "degrading" ? "text-red-400" : "text-amber-400"
                      }`}>
                        {trend.trend}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500 uppercase">Score Shift</div>
                      <div className={`text-sm font-mono font-bold ${
                        trend.score_delta > 0 ? "text-emerald-400" : trend.score_delta < 0 ? "text-red-400" : "text-gray-400"
                      }`}>
                        {trend.score_delta > 0 ? `+${trend.score_delta}` : trend.score_delta}
                      </div>
                    </div>
                  </div>
                </div>
                
                <TrendChart trend={trend} />
                
              </div>
            )}
            
            {!diff && timeline.length > 0 && (
              <div className="flex items-center justify-center p-12 text-center text-gray-500">
                <div>
                  <History className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>Select two snapshots from the timeline to compare structural and security drift.</p>
                </div>
              </div>
            )}
            
          </div>
        </div>
      </div>
    </div>
  );
}
