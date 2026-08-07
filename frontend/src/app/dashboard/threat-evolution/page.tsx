"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle, Shield, Clock,
  ChevronRight, X, RefreshCw, Filter, Zap, Target, BarChart3,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  ThreatTimelineSummary, ThreatTimeline, ThreatTrajectory,
  ExploitabilityRanking, Repository,
} from "@/lib/api";

// ─── Severity colour map ──────────────────────────────────────────
const SEV_COLORS: Record<string, string> = {
  critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#06b6d4", info: "#6b7280",
};

const TREND_ICON: Record<string, React.ReactNode> = {
  escalating: <TrendingUp className="w-4 h-4 text-red-400" />,
  improving: <TrendingDown className="w-4 h-4 text-emerald-400" />,
  stable: <Minus className="w-4 h-4 text-gray-400" />,
  dormant: <Minus className="w-4 h-4 text-gray-600" />,
};

// ─── Stats Cards ──────────────────────────────────────────────────
function StatsCards({ timelines, rankings }: {
  timelines: ThreatTimelineSummary[];
  rankings: ExploitabilityRanking[];
}) {
  const escalating = timelines.filter((t) => t.trend === "escalating").length;
  const critical = timelines.filter((t) => t.severity === "critical").length;
  const topUrgency = rankings[0]?.urgency_score ?? 0;
  const cards = [
    { label: "Total Threats", value: timelines.length, color: "#6366f1", icon: Shield },
    { label: "Escalating", value: escalating, color: "#ef4444", icon: TrendingUp },
    { label: "Critical", value: critical, color: "#f97316", icon: AlertTriangle },
    { label: "Top Urgency", value: topUrgency.toFixed(2), color: "#06b6d4", icon: Zap },
  ];
  return (
    <div className="grid grid-cols-4 gap-4 p-6">
      {cards.map(({ label, value, color, icon: Icon }) => (
        <motion.div key={label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="bg-surface-900/60 border border-white/5 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
          <div className="text-2xl font-bold" style={{ color }}>{value}</div>
        </motion.div>
      ))}
    </div>
  );
}

// ─── Timeline Sparkline ───────────────────────────────────────────
function Sparkline({ snapshots }: { snapshots: { score: number | null }[] }) {
  if (snapshots.length < 2) return <div className="w-20 h-6" />;
  const scores = snapshots.map((s) => s.score ?? 0);
  const max = Math.max(...scores, 1);
  const w = 80;
  const h = 24;
  const points = scores
    .map((s, i) => `${(i / (scores.length - 1)) * w},${h - (s / max) * h}`)
    .join(" ");
  const lastColor = scores[scores.length - 1] > scores[0] ? "#ef4444" : "#10b981";
  return (
    <svg width={w} height={h} className="flex-shrink-0">
      <polyline points={points} fill="none" stroke={lastColor} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────
function DetailPanel({
  timeline, trajectory, onClose
}: {
  timeline: ThreatTimeline | null;
  trajectory: ThreatTrajectory | null;
  onClose: () => void;
}) {
  if (!timeline) return null;
  const sevColor = SEV_COLORS[timeline.metadata?.severity as string ?? "medium"] ?? "#6b7280";

  return (
    <motion.div
      initial={{ x: 360, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 360, opacity: 0 }}
      transition={{ type: "spring", damping: 20 }}
      className="w-96 flex-shrink-0 border-l border-white/5 bg-surface-950/90 backdrop-blur-xl overflow-y-auto"
    >
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <h3 className="font-semibold text-sm text-white truncate max-w-[280px]">
          {(timeline.metadata?.title as string) ?? timeline.threat_id}
        </h3>
        <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-5">
        {/* Scores */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Trend", value: timeline.trend, color: timeline.trend === "escalating" ? "#ef4444" : "#10b981" },
            { label: "Velocity", value: timeline.velocity.toFixed(3), color: timeline.velocity > 0 ? "#ef4444" : "#06b6d4" },
            { label: "Snapshots", value: timeline.snapshot_count, color: "#6366f1" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white/5 rounded-lg p-2 text-center">
              <div className="text-lg font-bold" style={{ color }}>{value}</div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</div>
            </div>
          ))}
        </div>

        {/* Snapshot timeline */}
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Clock className="w-3 h-3" /> Snapshot History
          </h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {timeline.snapshots.map((s) => (
              <div key={s.id} className="flex items-center gap-2 text-xs py-1 px-2 rounded hover:bg-white/5">
                <div className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: SEV_COLORS[s.severity] ?? "#6b7280" }} />
                <span className="text-gray-300">{s.severity}</span>
                <span className="text-gray-600 ml-auto text-[10px]">
                  {s.captured_at ? new Date(s.captured_at).toLocaleDateString() : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Predictions */}
        {trajectory && trajectory.predictions.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <Target className="w-3 h-3" /> LLM Predictions
            </h4>
            {trajectory.predictions.map((pred, i) => (
              <div key={i} className="bg-white/5 rounded-lg p-3 space-y-2 text-xs">
                {typeof pred.predicted_peak_severity === "string" && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Peak Severity</span>
                    <span className="font-medium" style={{ color: SEV_COLORS[pred.predicted_peak_severity] }}>
                      {pred.predicted_peak_severity}
                    </span>
                  </div>
                )}
                {typeof pred.weaponisation_probability_30d === "number" && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Weaponisation 30d</span>
                    <span className="text-red-400 font-medium">{(pred.weaponisation_probability_30d * 100).toFixed(0)}%</span>
                  </div>
                )}
                {typeof pred.remediation_deadline === "string" && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Remediate By</span>
                    <span className="text-amber-400 font-medium">{pred.remediation_deadline}</span>
                  </div>
                )}
                {typeof pred.reasoning === "string" && (
                  <p className="text-gray-400 text-[11px] mt-1 border-t border-white/5 pt-2">
                    {pred.reasoning}
                  </p>
                )}
              </div>
            ))}
            <div className="flex items-center gap-1 mt-1 text-[10px] text-gray-600">
              <BarChart3 className="w-3 h-3" />
              Model: {trajectory.model ?? "unknown"} · Confidence: {(trajectory.confidence * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Exploitability Rankings Table ────────────────────────────────
function RankingsTable({ rankings, onSelect }: {
  rankings: ExploitabilityRanking[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="border-t border-white/5">
      <div className="px-6 py-3 border-b border-white/5 flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-white">Exploitability Rankings</h3>
        <span className="text-xs text-gray-500 ml-auto">Sorted by urgency score</span>
      </div>
      <div className="max-h-48 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-white/5">
              <th className="text-left px-6 py-2 font-medium">#</th>
              <th className="text-left px-2 py-2 font-medium">Threat</th>
              <th className="text-left px-2 py-2 font-medium">Severity</th>
              <th className="text-left px-2 py-2 font-medium">Trend</th>
              <th className="text-right px-6 py-2 font-medium">Urgency</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((r, i) => (
              <tr key={r.threat_id}
                onClick={() => onSelect(r.threat_id)}
                className="border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
              >
                <td className="px-6 py-2 text-gray-600">{i + 1}</td>
                <td className="px-2 py-2 text-white truncate max-w-[200px]">{r.title ?? r.threat_id}</td>
                <td className="px-2 py-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                    style={{ background: `${SEV_COLORS[r.severity ?? "low"]}22`, color: SEV_COLORS[r.severity ?? "low"] }}>
                    {r.severity}
                  </span>
                </td>
                <td className="px-2 py-2">{TREND_ICON[r.trend] ?? TREND_ICON.stable}</td>
                <td className="px-6 py-2 text-right font-mono font-bold"
                  style={{ color: r.urgency_score > 0.8 ? "#ef4444" : r.urgency_score > 0.5 ? "#f59e0b" : "#06b6d4" }}>
                  {r.urgency_score.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────
export default function ThreatEvolutionPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [timelines, setTimelines] = useState<ThreatTimelineSummary[]>([]);
  const [rankings, setRankings] = useState<ExploitabilityRanking[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<ThreatTimeline | null>(null);
  const [selectedTrajectory, setSelectedTrajectory] = useState<ThreatTrajectory | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r);
      if (r.length > 0) setSelectedRepo(r[0].full_name);
    });
  }, []);

  useEffect(() => {
    if (!selectedRepo) return;
    setLoading(true);
    setSelectedTimeline(null);
    setSelectedTrajectory(null);
    Promise.all([
      api.listThreatTimelines(selectedRepo),
      api.getExploitabilityRankings(selectedRepo),
    ]).then(([tl, rk]) => {
      setTimelines(tl);
      setRankings(rk);
    }).finally(() => setLoading(false));
  }, [selectedRepo]);

  const handleSelectThreat = useCallback(async (threatId: string) => {
    if (!selectedRepo) return;
    const [tl, tr] = await Promise.all([
      api.getThreatTimeline(selectedRepo, threatId),
      api.getThreatPrediction(threatId).catch(() => null),
    ]);
    setSelectedTimeline(tl);
    setSelectedTrajectory(tr);
  }, [selectedRepo]);

  const filtered = timelines.filter((t) => {
    if (!filter) return true;
    return t.severity === filter || t.trend === filter;
  });

  return (
    <div className="flex flex-col h-full bg-surface-950">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <TrendingUp className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Threat Evolution Engine</h1>
            <p className="text-xs text-gray-500">Track how threats mutate · Predict future attack trajectories</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-surface-900 border border-white/10 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-amber-400/50">
            {repos.map((r) => (
              <option key={r.id} value={r.full_name}>{r.full_name}</option>
            ))}
          </select>
          <button onClick={() => { setLoading(true); Promise.all([api.listThreatTimelines(selectedRepo), api.getExploitabilityRankings(selectedRepo)]).then(([tl, rk]) => { setTimelines(tl); setRankings(rk); }).finally(() => setLoading(false)); }}
            disabled={loading}
            className="p-2 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Stats */}
      {!loading && <StatsCards timelines={timelines} rankings={rankings} />}

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Threat list */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Filter bar */}
          <div className="flex items-center gap-3 px-6 py-2.5 border-b border-white/5">
            <Filter className="w-3.5 h-3.5 text-gray-500" />
            <select value={filter} onChange={(e) => setFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-amber-400/50">
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="escalating">Escalating</option>
              <option value="improving">Improving</option>
            </select>
            <span className="ml-auto text-xs text-gray-600">{filtered.length} threats</span>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-10 h-10 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-600 text-sm">
                <div className="text-center">
                  <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p>No threats tracked yet</p>
                  <p className="text-xs mt-1">Run a security scan to populate threat evolution data</p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {filtered.map((t) => (
                  <button key={t.threat_id} onClick={() => handleSelectThreat(t.threat_id)}
                    className="w-full text-left px-6 py-3 hover:bg-white/5 transition-colors flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: SEV_COLORS[t.severity ?? "low"] }} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white font-medium truncate">{t.title ?? t.threat_id}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0"
                          style={{ background: `${SEV_COLORS[t.severity ?? "low"]}22`, color: SEV_COLORS[t.severity ?? "low"] }}>
                          {t.severity}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-0.5 text-[10px] text-gray-500">
                        {t.cwe && <span>CWE: {t.cwe}</span>}
                        {t.mitre && <span>MITRE: {t.mitre}</span>}
                        <span>{t.snap_count} snapshots</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {TREND_ICON[t.trend] ?? TREND_ICON.stable}
                      <span className="text-xs font-mono" style={{ color: t.velocity > 0 ? "#ef4444" : "#06b6d4" }}>
                        {t.velocity > 0 ? "+" : ""}{t.velocity.toFixed(3)}
                      </span>
                      <ChevronRight className="w-4 h-4 text-gray-700" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Rankings */}
          {rankings.length > 0 && (
            <RankingsTable rankings={rankings} onSelect={handleSelectThreat} />
          )}
        </div>

        {/* Detail panel */}
        <AnimatePresence>
          {selectedTimeline && (
            <DetailPanel
              timeline={selectedTimeline}
              trajectory={selectedTrajectory}
              onClose={() => { setSelectedTimeline(null); setSelectedTrajectory(null); }}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
