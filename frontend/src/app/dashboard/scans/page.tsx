"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, ChevronRight, Clock, Loader2, Play, RefreshCw, Shield, XCircle } from "lucide-react";
import { api, type Scan } from "@/lib/api";
import { cn, formatDate, formatDuration, scoreColor, statusColor } from "@/lib/utils";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com").replace(/\/$/, "");
const PAGE_SIZE = 20;
const statusFilters = ["", "completed", "indexing", "scanning", "patching", "testing", "reviewing", "queued", "failed"];
const statusIcons: Record<string, any> = { completed: CheckCircle2, scanning: Loader2, indexing: Loader2, patching: Loader2, testing: Loader2, reviewing: Loader2, queued: Clock, failed: XCircle };
const activeStatuses = new Set(["queued", "indexing", "scanning", "patching", "testing", "reviewing"]);

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [repositories, setRepositories] = useState<Array<{ id: string; full_name: string }>>([]);
  const [repoId, setRepoId] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [scanMessage, setScanMessage] = useState("");

  const loadRepositories = useCallback(async () => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${API_BASE}/api/v1/repositories?t=${Date.now()}`, { cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error(`Repository API returned ${response.status}`);
      const data = await response.json();
      const source = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
      const items = source.map((repo: any) => ({ id: String(repo.id), full_name: repo.full_name || repo.name || String(repo.id) }));
      setRepositories(items);
      if (!repoId && items[0]?.id) setRepoId(items[0].id);
    } finally { window.clearTimeout(timer); }
  }, [repoId]);

  const loadScans = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true); else setLoading(true);
    try {
      const data = await api.listScans({ status: status || undefined, page, page_size: PAGE_SIZE });
      setScans(Array.isArray(data.items) ? data.items : []);
      setTotalPages(Math.max(1, data.total_pages || 1));
      setError("");
    } catch (err: any) {
      setError(err?.message || "Unable to load security scans.");
      if (!silent) setScans([]);
    } finally { setLoading(false); setRefreshing(false); }
  }, [status, page]);

  useEffect(() => { loadRepositories().catch((err) => setError(err?.name === "AbortError" ? "Repository API timed out." : err?.message || "Unable to load repositories.")); }, [loadRepositories]);
  useEffect(() => { loadScans(); }, [loadScans]);
  useEffect(() => {
    const timer = window.setInterval(() => loadScans(true), 2000);
    return () => window.clearInterval(timer);
  }, [loadScans]);

  async function startRealScan() {
    if (!repoId) { setScanMessage("Add a repository first."); return; }
    setStarting(true); setScanMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/scans/real`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ repository_id: repoId }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `Scan API returned ${response.status}`);
      setScanMessage(`Live scan queued: ${String(body.id).slice(0, 8)} — repository indexing will continue in the background.`);
      setStatus(""); setPage(1); await loadScans(true);
    } catch (err: any) { setScanMessage(err?.message || "Unable to start real scan."); }
    finally { setStarting(false); }
  }

  if (loading) return <div className="flex items-center justify-center h-[60vh]"><div className="flex flex-col items-center gap-3"><Shield className="w-10 h-10 text-cyber-cyan animate-pulse" /><span className="text-sm text-gray-500">Connecting to live security pipeline…</span></div></div>;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div><h1 className="text-xl font-bold text-gray-100">Security Scans</h1><p className="text-sm text-gray-500 mt-1">Real repository content → indexing → security agents → findings → fixes → tests.</p></div>
        <div className="flex flex-col sm:flex-row gap-2">
          {repositories.length > 0 && <select value={repoId} onChange={(e) => setRepoId(e.target.value)} className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-gray-300 min-w-[220px]">{repositories.map((repo) => <option key={repo.id} value={repo.id}>{repo.full_name}</option>)}</select>}
          <button onClick={startRealScan} disabled={starting || !repoId} className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30 hover:bg-cyber-cyan/20 disabled:opacity-40">{starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}{starting ? "Starting…" : "Run Real Scan"}</button>
          <button onClick={() => loadScans(true)} disabled={refreshing} className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-white/5"><RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} /></button>
        </div>
      </div>

      {scanMessage && <div className="rounded-lg border border-cyber-cyan/20 bg-cyber-cyan/5 px-4 py-3 text-xs text-cyber-cyan">{scanMessage}</div>}
      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 flex gap-3 text-xs text-red-300"><AlertTriangle className="w-4 h-4 shrink-0" />{error}</div>}

      <div className="flex gap-2 overflow-x-auto pb-1">{statusFilters.map((value) => <button key={value} onClick={() => { setStatus(value); setPage(1); }} className={cn("shrink-0 px-3 py-1.5 rounded-lg text-xs border", status === value ? "bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30" : "text-gray-500 border-transparent hover:bg-white/5")}>{value || "All"}</button>)}</div>

      <div className="space-y-2">
        {scans.map((scan) => {
          const normalized = String(scan.status || "queued").toLowerCase();
          const Icon = statusIcons[normalized] || Clock;
          const active = activeStatuses.has(normalized);
          return <motion.a key={scan.id} href={`/dashboard/scans/${scan.id}`} className="glass-card-hover p-4 flex flex-col sm:flex-row sm:items-center gap-4 group">
            <div className={cn("p-2 rounded-lg self-start", normalized === "completed" ? "bg-emerald-500/10" : normalized === "failed" ? "bg-red-500/10" : "bg-cyan-500/10")}><Icon className={cn("w-5 h-5", statusColor(normalized), active && "animate-spin")} /></div>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2"><code className="text-sm font-mono text-gray-200">{(scan.commit_sha || "unknown").slice(0, 8)}</code><span className="text-xs text-gray-600">•</span><span className="text-xs text-gray-400">{scan.branch || "unknown"}</span><span className="px-2 py-0.5 rounded text-[10px] uppercase bg-white/5 text-gray-400">{scan.trigger || "unknown"}</span><span className={cn("px-2 py-0.5 rounded text-[10px] uppercase bg-white/5", statusColor(normalized))}>{normalized}</span></div>
              <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500"><span>{formatDate(scan.created_at)}</span>{scan.duration_seconds != null && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{formatDuration(scan.duration_seconds)}</span>}{active && <span className="text-cyber-cyan animate-pulse">LIVE · {scan.current_agent || normalized}</span>}</div>
            </div>
            <div className="flex items-center justify-between sm:justify-end gap-4"><div className="flex gap-2">{scan.critical_count > 0 && <span className="badge-critical">{scan.critical_count} crit</span>}{scan.high_count > 0 && <span className="badge-high">{scan.high_count} high</span>}{scan.medium_count > 0 && <span className="badge-medium">{scan.medium_count} med</span>}</div><div className="text-right min-w-[45px]"><div className={cn("text-lg font-bold font-mono", scoreColor(scan.security_score))}>{scan.security_score ?? "—"}</div><p className="text-[10px] text-gray-600">score</p></div><ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400" /></div>
          </motion.a>;
        })}
      </div>

      {!error && scans.length === 0 && <div className="py-20 text-center"><Shield className="w-10 h-10 text-gray-700 mx-auto mb-3" /><p className="text-sm text-gray-400">No scans found.</p><p className="text-xs text-gray-600 mt-1">Select a repository and use Run Real Scan.</p></div>}
      {(totalPages > 1 || page > 1) && <div className="flex items-center justify-center gap-4 pt-2"><button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="text-xs text-gray-400 disabled:opacity-30">Previous</button><span className="text-xs text-gray-600">Page {page} of {totalPages}</span><button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="text-xs text-gray-400 disabled:opacity-30">Next</button></div>}
    </motion.div>
  );
}
