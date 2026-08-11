"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  RefreshCw,
  Shield,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { api, type Scan } from "@/lib/api";
import { cn, formatDate, formatDuration, scoreColor, statusColor } from "@/lib/utils";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

const statusIcons: Record<string, any> = {
  completed: CheckCircle2,
  scanning: Loader2,
  queued: Clock,
  failed: XCircle,
};

const statusFilters = [
  { value: "", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "scanning", label: "Scanning" },
  { value: "queued", label: "Queued" },
  { value: "failed", label: "Failed" },
];

const triggerLabels: Record<string, { label: string; color: string }> = {
  push: { label: "Push", color: "text-cyber-cyan" },
  pull_request: { label: "PR", color: "text-cyber-purple" },
  manual: { label: "Manual", color: "text-cyber-yellow" },
};

const PAGE_SIZE = 20;

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const loadScans = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true);
    else setLoading(true);

    try {
      setError(null);
      const data = await api.listScans({
        status: filterStatus || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setScans(Array.isArray(data.items) ? data.items : []);
      setTotalPages(Math.max(1, data.total_pages || 1));
    } catch (err) {
      console.error("Failed to load scans", err);
      setError(err instanceof Error ? err.message : "Unable to load security scans.");
      if (!silent) setScans([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filterStatus, page]);

  useEffect(() => {
    loadScans();
  }, [loadScans]);

  // Keep queued/scanning results current without requiring a manual refresh.
  useEffect(() => {
    const timer = window.setInterval(() => loadScans(true), 5000);
    return () => window.clearInterval(timer);
  }, [loadScans]);

  const handleFilter = (status: string) => {
    setFilterStatus(status);
    setPage(1);
  };

  const hasNextPage = page < totalPages || scans.length === PAGE_SIZE;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <Shield className="w-10 h-10 text-cyber-cyan animate-pulse" />
          <span className="text-sm text-gray-500">Loading security scans…</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div
        variants={itemVariants}
        className="flex flex-col gap-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-100">Security Scans</h1>
            <p className="text-sm text-gray-500 mt-1">Full pipeline execution history</p>
          </div>
          <button
            type="button"
            onClick={() => loadScans(true)}
            disabled={refreshing}
            aria-label="Refresh scans"
            className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
          </button>
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1">
          {statusFilters.map((status) => (
            <button
              key={status.value}
              type="button"
              onClick={() => handleFilter(status.value)}
              className={cn(
                "shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border",
                filterStatus === status.value
                  ? "bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30"
                  : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-white/5"
              )}
            >
              {status.label}
            </button>
          ))}
        </div>
      </motion.div>

      {error && (
        <motion.div
          variants={itemVariants}
          className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex items-start gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-red-300">Scan data unavailable</p>
            <p className="text-xs text-gray-500 mt-1 break-words">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => loadScans()}
            className="text-xs text-red-300 hover:text-red-200 shrink-0"
          >
            Retry
          </button>
        </motion.div>
      )}

      <div className="space-y-2">
        {scans.map((scan) => {
          const normalizedStatus = String(scan.status || "queued").toLowerCase();
          const StatusIcon = statusIcons[normalizedStatus] || Clock;
          const trigger = triggerLabels[scan.trigger] || {
            label: scan.trigger || "Unknown",
            color: "text-gray-400",
          };

          return (
            <motion.a
              key={scan.id}
              variants={itemVariants}
              href={`/dashboard/scans/${scan.id}`}
              className="glass-card-hover p-4 flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-5 group block"
            >
              <div
                className={cn(
                  "p-2 rounded-lg self-start",
                  normalizedStatus === "completed"
                    ? "bg-emerald-500/10"
                    : normalizedStatus === "scanning"
                    ? "bg-cyan-500/10"
                    : normalizedStatus === "failed"
                    ? "bg-red-500/10"
                    : "bg-gray-500/10"
                )}
              >
                <StatusIcon
                  className={cn(
                    "w-5 h-5",
                    statusColor(normalizedStatus),
                    normalizedStatus === "scanning" && "animate-spin"
                  )}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                  <code className="text-sm font-mono text-gray-200">
                    {(scan.commit_sha || "unknown").slice(0, 8)}
                  </code>
                  <span className="text-xs text-gray-600">•</span>
                  <span className="text-xs text-gray-400 truncate max-w-[180px]">
                    {scan.branch || "unknown"}
                  </span>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-white/5",
                      trigger.color
                    )}
                  >
                    {trigger.label}
                  </span>
                  <span className={cn("px-2 py-0.5 rounded text-[10px] uppercase bg-white/5", statusColor(normalizedStatus))}>
                    {normalizedStatus}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-2 text-xs text-gray-500">
                  <span>{formatDate(scan.created_at)}</span>
                  {scan.duration_seconds != null && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDuration(scan.duration_seconds)}
                    </span>
                  )}
                  {scan.current_agent && normalizedStatus === "scanning" && (
                    <span className="text-cyber-cyan animate-pulse">
                      Running: {scan.current_agent}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-4">
                <div className="flex items-center gap-2">
                  {scan.critical_count > 0 && <span className="badge-critical">{scan.critical_count} crit</span>}
                  {scan.high_count > 0 && <span className="badge-high">{scan.high_count} high</span>}
                  {scan.medium_count > 0 && <span className="badge-medium">{scan.medium_count} med</span>}
                </div>

                <div className="text-right min-w-[45px]">
                  <div className={cn("text-lg font-bold font-mono", scoreColor(scan.security_score))}>
                    {scan.security_score ?? "—"}
                  </div>
                  <p className="text-[10px] text-gray-600">score</p>
                </div>

                <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
              </div>
            </motion.a>
          );
        })}
      </div>

      {!error && scans.length === 0 && (
        <motion.div variants={itemVariants} className="py-20 flex flex-col items-center text-center">
          <Shield className="w-10 h-10 text-gray-700 mb-3" />
          <p className="text-sm text-gray-400">
            {filterStatus ? `No ${filterStatus} scans found.` : "No security scans found."}
          </p>
          <p className="text-xs text-gray-600 mt-1">New pipeline executions will appear here automatically.</p>
        </motion.div>
      )}

      {(totalPages > 1 || page > 1 || hasNextPage) && (
        <motion.div variants={itemVariants} className="flex items-center justify-center gap-3 pt-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-gray-200 hover:bg-white/5 disabled:opacity-30 disabled:pointer-events-none"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <span className="text-xs text-gray-600">Page {page}{totalPages > 1 ? ` of ${totalPages}` : ""}</span>
          <button
            type="button"
            disabled={!hasNextPage}
            onClick={() => setPage((current) => current + 1)}
            className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-gray-200 hover:bg-white/5 disabled:opacity-30 disabled:pointer-events-none"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </motion.div>
      )}
    </motion.div>
  );
}
