"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Filter,
  ChevronRight,
  Clock,
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
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

const triggerLabels: Record<string, { label: string; color: string }> = {
  push: { label: "Push", color: "text-cyber-cyan" },
  pull_request: { label: "PR", color: "text-cyber-purple" },
  manual: { label: "Manual", color: "text-cyber-yellow" },
};

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadScans();
  }, [filterStatus, page]);

  async function loadScans() {
    try {
      const data = await api.listScans({
        status: filterStatus || undefined,
        page,
      });
      setScans(data.items);
      setTotalPages(data.total_pages);
    } catch (err) {
      console.error("Failed to load scans", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Shield className="w-10 h-10 text-cyber-cyan animate-pulse" />
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
      {/* Header + Filters */}
      <motion.div
        variants={itemVariants}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-xl font-bold text-gray-100">Security Scans</h1>
          <p className="text-sm text-gray-500 mt-1">
            Full pipeline execution history
          </p>
        </div>
        <div className="flex items-center gap-2">
          {["", "completed", "scanning", "queued", "failed"].map((status) => (
            <button
              key={status}
              onClick={() => { setFilterStatus(status); setPage(1); }}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                filterStatus === status
                  ? "bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
              )}
            >
              {status || "All"}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Scans List */}
      <div className="space-y-2">
        {scans.map((scan) => {
          const StatusIcon = statusIcons[scan.status] || Clock;
          const trigger = triggerLabels[scan.trigger] || { label: scan.trigger, color: "text-gray-400" };

          return (
            <motion.a
              key={scan.id}
              variants={itemVariants}
              href={`/dashboard/scans/${scan.id}`}
              className="glass-card-hover p-4 flex items-center gap-5 group block"
            >
              {/* Status Icon */}
              <div
                className={cn(
                  "p-2 rounded-lg",
                  scan.status === "completed"
                    ? "bg-emerald-500/10"
                    : scan.status === "scanning"
                    ? "bg-cyan-500/10"
                    : scan.status === "failed"
                    ? "bg-red-500/10"
                    : "bg-gray-500/10"
                )}
              >
                <StatusIcon
                  className={cn(
                    "w-5 h-5",
                    statusColor(scan.status),
                    scan.status === "scanning" && "animate-spin"
                  )}
                />
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <code className="text-sm font-mono text-gray-200">
                    {scan.commit_sha.slice(0, 8)}
                  </code>
                  <span className="text-xs text-gray-600">•</span>
                  <span className="text-xs text-gray-400">{scan.branch}</span>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] font-semibold uppercase",
                      trigger.color,
                      "bg-white/5"
                    )}
                  >
                    {trigger.label}
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                  <span>{formatDate(scan.created_at)}</span>
                  {scan.duration_seconds && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDuration(scan.duration_seconds)}
                    </span>
                  )}
                  {scan.current_agent && (
                    <span className="text-cyber-cyan animate-pulse">
                      Running: {scan.current_agent}
                    </span>
                  )}
                </div>
              </div>

              {/* Severity Badges */}
              <div className="flex items-center gap-2">
                {scan.critical_count > 0 && (
                  <span className="badge-critical">{scan.critical_count} crit</span>
                )}
                {scan.high_count > 0 && (
                  <span className="badge-high">{scan.high_count} high</span>
                )}
                {scan.medium_count > 0 && (
                  <span className="badge-medium">{scan.medium_count} med</span>
                )}
              </div>

              {/* Score */}
              <div className="text-right">
                <div className={cn("text-lg font-bold font-mono", scoreColor(scan.security_score))}>
                  {scan.security_score || "—"}
                </div>
                <p className="text-[10px] text-gray-600">score</p>
              </div>

              <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
            </motion.a>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <motion.div variants={itemVariants} className="flex justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={cn(
                "w-8 h-8 rounded-lg text-xs font-medium transition-all",
                page === p
                  ? "bg-cyber-cyan/20 text-cyber-cyan"
                  : "text-gray-500 hover:bg-white/5"
              )}
            >
              {p}
            </button>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
