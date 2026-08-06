"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Download,
  Calendar,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  BarChart3,
  PieChart,
} from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { api, type Report } from "@/lib/api";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReports() {
    try {
      const data = await api.listReports();
      setReports(data);
    } catch (err) {
      console.error("Failed to load reports", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      const newReport = await api.generateReport();
      setReports((prev) => [newReport, ...prev]);
    } catch (err) {
      console.error("Failed to generate report", err);
    } finally {
      setGenerating(false);
    }
  }

  const statusConfig = {
    approved: {
      label: "Approved",
      icon: CheckCircle2,
      color: "text-cyber-green",
      bg: "bg-emerald-500/10",
    },
    blocked: {
      label: "Blocked",
      icon: AlertTriangle,
      color: "text-cyber-red",
      bg: "bg-red-500/10",
    },
    pending: {
      label: "Pending",
      icon: Clock,
      color: "text-gray-400",
      bg: "bg-gray-500/10",
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div
        variants={itemVariants}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-xl font-bold text-gray-100">Security Reports</h1>
          <p className="text-sm text-gray-500 mt-1">
            Comprehensive security assessment reports with deployment decisions
          </p>
        </div>
        <button 
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 bg-cyber-cyan/10 border border-cyber-cyan/20 text-cyber-cyan rounded-lg text-sm font-medium hover:bg-cyber-cyan/20 transition-all disabled:opacity-50"
        >
          {generating ? <Clock className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
          {generating ? "Generating..." : "Generate Report"}
        </button>
      </motion.div>

      {/* Summary Cards */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div className="glass-card p-4 text-center">
          <p className="text-2xl font-bold text-gray-100">{reports.length}</p>
          <p className="text-xs text-gray-500 mt-1">Total Reports</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-2xl font-bold text-cyber-green">
            {reports.filter((r) => r.status === "approved").length}
          </p>
          <p className="text-xs text-gray-500 mt-1">Approved</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-2xl font-bold text-cyber-red">
            {reports.filter((r) => r.status === "blocked").length}
          </p>
          <p className="text-xs text-gray-500 mt-1">Blocked</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p
            className={cn(
              "text-2xl font-bold",
              reports.length > 0 ? scoreColor(
                Math.round(
                  reports.reduce((a, r) => a + r.score, 0) / reports.length
                )
              ) : "text-gray-500"
            )}
          >
            {reports.length > 0 ? Math.round(
              reports.reduce((a, r) => a + r.score, 0) / reports.length
            ) : "—"}
          </p>
          <p className="text-xs text-gray-500 mt-1">Avg Score</p>
        </div>
      </motion.div>

      {/* Reports List */}
      <div className="space-y-3">
        {reports.map((report) => {
          const status = statusConfig[report.status];
          const StatusIcon = status.icon;

          return (
            <motion.div
              key={report.id}
              variants={itemVariants}
              className="glass-card-hover p-5 group cursor-pointer"
            >
              <div className="flex items-center gap-5">
                {/* Icon */}
                <div className="p-3 rounded-lg bg-white/5 border border-white/5 group-hover:border-cyber-cyan/20 transition-all">
                  <FileText className="w-6 h-6 text-gray-400 group-hover:text-cyber-cyan transition-colors" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-200 group-hover:text-white transition-colors">
                    {report.name}
                  </h3>
                  <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                    <span>{report.repository}</span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(report.date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                {/* Metrics */}
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <p className={cn("text-lg font-bold font-mono", scoreColor(report.score))}>
                      {report.score}
                    </p>
                    <p className="text-[10px] text-gray-600">Score</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-gray-300">{report.findings}</p>
                    <p className="text-[10px] text-gray-600">Findings</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-cyber-green">{report.patches}</p>
                    <p className="text-[10px] text-gray-600">Patches</p>
                  </div>
                </div>

                {/* Status */}
                <div
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg",
                    status.bg
                  )}
                >
                  <StatusIcon className={cn("w-4 h-4", status.color)} />
                  <span className={cn("text-xs font-medium", status.color)}>
                    {status.label}
                  </span>
                </div>

                {/* Download */}
                <button className="p-2 rounded-lg hover:bg-white/5 transition-colors opacity-0 group-hover:opacity-100">
                  <Download className="w-4 h-4 text-gray-500 hover:text-gray-300" />
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
