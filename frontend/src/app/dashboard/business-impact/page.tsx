"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  DollarSign, RefreshCw, AlertTriangle, Shield, Building2,
  Database, Clock, Scale, TrendingUp, ChevronDown,
} from "lucide-react";
import { api } from "@/lib/api";
import type { BusinessImpactData, Repository } from "@/lib/api";

const SEV = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#06b6d4" };
const RATING_COLOR: Record<string, string> = {
  CRITICAL: "#ef4444", HIGH: "#f97316", MEDIUM: "#f59e0b", LOW: "#10b981",
};

const fmt = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

function RiskGauge({ rating, total }: { rating: string; total: number }) {
  const color = RATING_COLOR[rating] ?? "#6b7280";
  return (
    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
      className="bg-surface-900/60 border border-white/5 rounded-2xl p-6 text-center">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Total Financial Risk</div>
      <div className="text-4xl font-bold mb-1" style={{ color }}>{fmt(total)}</div>
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold mt-2"
        style={{ background: `${color}22`, color }}>
        <AlertTriangle className="w-3 h-3" /> {rating}
      </div>
    </motion.div>
  );
}

function CostBreakdown({ data }: { data: BusinessImpactData }) {
  const s = data.summary;
  const items = [
    { label: "Breach Cost", value: s.breach_cost_total, icon: Shield, color: "#ef4444" },
    { label: "Downtime Cost", value: s.downtime_cost_total, icon: Clock, color: "#f59e0b" },
    { label: "Record Exposure", value: s.record_exposure_total, icon: Database, color: "#6366f1" },
    { label: "Regulatory Fines", value: s.regulatory_exposure_total, icon: Scale, color: "#a855f7" },
  ];
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="bg-surface-900/60 border border-white/5 rounded-2xl p-5">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Cost Breakdown</h3>
      <div className="space-y-3">
        {items.map(({ label, value, icon: Icon, color }) => (
          <div key={label}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2 text-sm">
                <Icon className="w-3.5 h-3.5" style={{ color }} />
                <span className="text-gray-300">{label}</span>
              </div>
              <span className="text-sm font-mono font-bold" style={{ color }}>{fmt(value)}</span>
            </div>
            <div className="bg-white/5 rounded-full h-1.5 overflow-hidden">
              <motion.div className="h-full rounded-full" style={{ background: color }}
                initial={{ width: 0 }} animate={{ width: `${(value / max) * 100}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }} />
            </div>
          </div>
        ))}
      </div>
      {s.chain_amplification_factor > 1.0 && (
        <div className="mt-4 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 flex-shrink-0" />
          Attack chain amplification: ×{s.chain_amplification_factor.toFixed(2)}
        </div>
      )}
    </div>
  );
}

function RegulatoryTable({ data }: { data: BusinessImpactData }) {
  if (!data.regulatory_exposure.length) return null;
  return (
    <div className="bg-surface-900/60 border border-white/5 rounded-2xl p-5">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Scale className="w-3.5 h-3.5" /> Regulatory Exposure
      </h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-white/5">
            <th className="text-left py-2 font-medium">Framework</th>
            <th className="text-right py-2 font-medium">Max Fine</th>
            <th className="text-right py-2 font-medium">Exposure</th>
            <th className="text-right py-2 font-medium">Threats</th>
          </tr>
        </thead>
        <tbody>
          {data.regulatory_exposure.map((r) => (
            <tr key={r.framework} className="border-b border-white/5">
              <td className="py-2 text-white font-medium">{r.framework}</td>
              <td className="py-2 text-right text-gray-400 font-mono">{fmt(r.max_fine)}</td>
              <td className="py-2 text-right font-mono font-bold text-amber-400">{fmt(r.estimated_exposure)}</td>
              <td className="py-2 text-right text-gray-500">{r.relevant_threat_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ThreatImpactTable({ data }: { data: BusinessImpactData }) {
  const [expanded, setExpanded] = useState(false);
  const items = expanded ? data.threat_impacts : data.threat_impacts.slice(0, 8);
  return (
    <div className="bg-surface-900/60 border border-white/5 rounded-2xl p-5">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
        Per-Threat Impact ({data.threat_impacts.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-white/5">
              <th className="text-left py-2 font-medium">Threat</th>
              <th className="text-left py-2 font-medium">Severity</th>
              <th className="text-right py-2 font-medium">Breach</th>
              <th className="text-right py-2 font-medium">Downtime</th>
              <th className="text-right py-2 font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.threat_id} className="border-b border-white/5 hover:bg-white/5">
                <td className="py-2 text-white truncate max-w-[200px]">{t.title}</td>
                <td className="py-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                    style={{ background: `${SEV[t.severity as keyof typeof SEV] ?? "#6b7280"}22`,
                      color: SEV[t.severity as keyof typeof SEV] ?? "#6b7280" }}>
                    {t.severity}
                  </span>
                </td>
                <td className="py-2 text-right font-mono text-gray-400">{fmt(t.breach_cost)}</td>
                <td className="py-2 text-right font-mono text-gray-400">{fmt(t.downtime_cost)} ({t.downtime_hours}h)</td>
                <td className="py-2 text-right font-mono font-bold text-red-400">{fmt(t.total_impact)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.threat_impacts.length > 8 && (
        <button onClick={() => setExpanded(!expanded)}
          className="mt-2 flex items-center gap-1 text-xs text-cyber-cyan hover:text-white transition-colors mx-auto">
          <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
          {expanded ? "Show less" : `Show all ${data.threat_impacts.length}`}
        </button>
      )}
    </div>
  );
}

export default function BusinessImpactPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [data, setData] = useState<BusinessImpactData | null>(null);
  const [loading, setLoading] = useState(false);
  const [revenue, setRevenue] = useState("10000000");
  const [industry, setIndustry] = useState("saas");
  const [records, setRecords] = useState("100000");

  useEffect(() => {
    api.listRepositories().then((r) => { setRepos(r); if (r.length) setSelectedRepo(r[0].full_name); });
  }, []);

  const compute = async () => {
    if (!selectedRepo) return;
    setLoading(true);
    const result = await api.computeBusinessImpact(selectedRepo, {
      annual_revenue: parseFloat(revenue) || 10_000_000,
      industry,
      estimated_records: parseInt(records) || 100_000,
      compliance_frameworks: ["GDPR", "HIPAA", "PCI_DSS", "SOC2"],
    });
    setData(result);
    setLoading(false);
  };

  useEffect(() => { if (selectedRepo) compute(); }, [selectedRepo]);

  return (
    <div className="flex flex-col h-full bg-surface-950 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
            <DollarSign className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Business Impact Engine</h1>
            <p className="text-xs text-gray-500">Dollar-value risk quantification · IBM breach cost methodology</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-surface-900 border border-white/10 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-400/50">
            {repos.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}</option>)}
          </select>
          <button onClick={compute} disabled={loading}
            className="p-2 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Config bar */}
      <div className="flex items-center gap-4 px-6 py-3 border-b border-white/5 flex-shrink-0 flex-wrap">
        <div className="flex items-center gap-2">
          <Building2 className="w-3.5 h-3.5 text-gray-500" />
          <select value={industry} onChange={(e) => setIndustry(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none">
            {["fintech","healthcare","e-commerce","saas","enterprise"].map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3.5 h-3.5 text-gray-500" />
          <input type="number" value={revenue} onChange={(e) => setRevenue(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white w-32 focus:outline-none" placeholder="Revenue" />
        </div>
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-gray-500" />
          <input type="number" value={records} onChange={(e) => setRecords(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white w-28 focus:outline-none" placeholder="Records" />
        </div>
        <button onClick={compute} disabled={loading}
          className="px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-emerald-400 text-xs hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
          Recalculate
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-gray-500">Computing business impact…</p>
          </div>
        </div>
      ) : data ? (
        <div className="p-6 space-y-6">
          {/* Top row: gauge + breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RiskGauge rating={data.risk_rating} total={data.summary.total_financial_risk} />
            <CostBreakdown data={data} />
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Threats", value: data.summary.threat_count, color: "#6366f1" },
              { label: "Critical", value: data.summary.critical_threats, color: "#ef4444" },
              { label: "High-Value Assets", value: data.summary.high_value_assets, color: "#f59e0b" },
              { label: "Attack Chains", value: data.summary.attack_chain_count, color: "#a855f7" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-surface-900/60 border border-white/5 rounded-xl p-4">
                <div className="text-xs text-gray-500 mb-1">{label}</div>
                <div className="text-2xl font-bold" style={{ color }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RegulatoryTable data={data} />
            <ThreatImpactTable data={data} />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-600">
          <div className="text-center">
            <DollarSign className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p className="text-sm">Select a repository to compute business impact</p>
          </div>
        </div>
      )}
    </div>
  );
}
