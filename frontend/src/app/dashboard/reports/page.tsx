"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  FileText, Download, Calendar, AlertTriangle, CheckCircle2, Clock, BarChart3, RefreshCw,
} from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { api, type Report } from "@/lib/api";

const containerVariants = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const itemVariants = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.35 } } };

function downloadReport(report: Report) {
  const payload = {
    ...report,
    generated_at: new Date().toISOString(),
    product: "OBSIDIAN Security Center",
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${report.name.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase() || "obsidian-report"}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function loadReports() {
    setError("");
    try {
      const data = await api.listReports();
      setReports(data);
    } catch (err: any) {
      setError(err?.message || "Unable to load reports from the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadReports(); }, []);

  async function handleGenerate() {
    setGenerating(true);
    setError("");
    try {
      const newReport = await api.generateReport();
      setReports((prev) => [newReport, ...prev.filter((report) => report.id !== newReport.id)]);
    } catch (err: any) {
      setError(err?.message || "Unable to generate report.");
    } finally {
      setGenerating(false);
    }
  }

  const statusConfig: Record<string, { label: string; icon: any; color: string; bg: string }> = {
    approved: { label: "Approved", icon: CheckCircle2, color: "text-cyber-green", bg: "bg-emerald-500/10" },
    blocked: { label: "Blocked", icon: AlertTriangle, color: "text-cyber-red", bg: "bg-red-500/10" },
    pending: { label: "Pending", icon: Clock, color: "text-gray-400", bg: "bg-gray-500/10" },
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Security Reports</h1>
          <p className="text-sm text-gray-500 mt-1">Reports generated from persisted OBSIDIAN security data.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadReports} disabled={loading} className="p-2 rounded-lg border border-white/10 text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-40" title="Refresh reports">
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
          <button onClick={handleGenerate} disabled={generating} className="flex items-center justify-center gap-2 px-4 py-2 bg-cyber-cyan/10 border border-cyber-cyan/20 text-cyber-cyan rounded-lg text-sm font-medium hover:bg-cyber-cyan/20 transition-all disabled:opacity-50">
            {generating ? <Clock className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            {generating ? "Generating..." : "Generate Report"}
          </button>
        </div>
      </motion.div>

      {error && <div className="glass-card p-4 border-red-500/30 text-sm text-red-200">{error}</div>}

      <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="glass-card p-4 text-center"><p className="text-2xl font-bold text-gray-100">{reports.length}</p><p className="text-xs text-gray-500 mt-1">Total Reports</p></div>
        <div className="glass-card p-4 text-center"><p className="text-2xl font-bold text-cyber-green">{reports.filter((r) => r.status === "approved").length}</p><p className="text-xs text-gray-500 mt-1">Approved</p></div>
        <div className="glass-card p-4 text-center"><p className="text-2xl font-bold text-cyber-red">{reports.filter((r) => r.status === "blocked").length}</p><p className="text-xs text-gray-500 mt-1">Blocked</p></div>
        <div className="glass-card p-4 text-center"><p className={cn("text-2xl font-bold", reports.length ? scoreColor(Math.round(reports.reduce((a, r) => a + r.score, 0) / reports.length)) : "text-gray-500")}>{reports.length ? Math.round(reports.reduce((a, r) => a + r.score, 0) / reports.length) : "—"}</p><p className="text-xs text-gray-500 mt-1">Avg Score</p></div>
      </motion.div>

      {loading ? (
        <div className="glass-card py-16 text-center text-gray-500"><RefreshCw className="w-7 h-7 mx-auto mb-3 animate-spin" />Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="glass-card py-16 text-center"><FileText className="w-10 h-10 text-gray-700 mx-auto mb-3" /><p className="text-sm text-gray-400">No reports generated yet.</p><p className="text-xs text-gray-600 mt-1">Run a real repository scan first, then generate a report.</p></div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => {
            const status = statusConfig[report.status] || statusConfig.pending;
            const StatusIcon = status.icon;
            return (
              <motion.div key={report.id} variants={itemVariants} className="glass-card-hover p-4 sm:p-5">
                <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="p-3 rounded-lg bg-white/5 border border-white/5 shrink-0"><FileText className="w-5 h-5 text-gray-400" /></div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-gray-200 truncate">{report.name}</h3>
                      <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-gray-500"><span className="truncate max-w-[240px]">{report.repository}</span><span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(report.date).toLocaleDateString()}</span></div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-5 sm:gap-8 text-center shrink-0"><div><p className={cn("text-lg font-bold font-mono", scoreColor(report.score))}>{report.score}</p><p className="text-[10px] text-gray-600">Score</p></div><div><p className="text-lg font-bold text-gray-300">{report.findings}</p><p className="text-[10px] text-gray-600">Findings</p></div><div><p className="text-lg font-bold text-cyber-green">{report.patches}</p><p className="text-[10px] text-gray-600">Patches</p></div></div>
                  <div className="flex items-center gap-2 shrink-0"><div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-lg", status.bg)}><StatusIcon className={cn("w-4 h-4", status.color)} /><span className={cn("text-xs font-medium", status.color)}>{status.label}</span></div><button onClick={() => downloadReport(report)} className="p-2 rounded-lg border border-white/5 hover:bg-white/5" title="Download report JSON"><Download className="w-4 h-4 text-gray-500 hover:text-gray-300" /></button></div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
