"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronUp,
  FileCode,
  Lightbulb,
  RefreshCw,
} from "lucide-react";
import { api, type Finding } from "@/lib/api";
import { cn, severityBadge, severityColor } from "@/lib/utils";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export default function ThreatsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filterSeverity, setFilterSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listFindings({
          severity: filterSeverity || undefined,
          page_size: 100,
        });
        setFindings(data.items);
      } catch (err: any) {
        setError(err.message || "Unable to load findings");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filterSeverity]);

  const severityCounts = useMemo(
    () =>
      findings.reduce(
        (acc, finding) => {
          acc[finding.severity] = (acc[finding.severity] || 0) + 1;
          return acc;
        },
        {} as Record<string, number>,
      ),
    [findings],
  );

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <h1 className="text-xl font-bold text-gray-100">Threat Findings</h1>
        <p className="text-sm text-gray-500 mt-1">
          {loading ? "Loading live findings" : `${findings.length} findings from completed scans`}
        </p>
      </motion.div>

      <motion.div variants={itemVariants} className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilterSeverity("")}
          className={cn(
            "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            !filterSeverity
              ? "bg-white/10 text-gray-200"
              : "text-gray-500 hover:text-gray-300 hover:bg-white/5",
          )}
        >
          All
        </button>
        {["critical", "high", "medium", "low"].map((severity) => (
          <button
            key={severity}
            onClick={() => setFilterSeverity(severity)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              filterSeverity === severity
                ? severityBadge(severity)
                : "text-gray-500 hover:text-gray-300 hover:bg-white/5",
            )}
          >
            {severity.charAt(0).toUpperCase() + severity.slice(1)}
            {severityCounts[severity] ? ` (${severityCounts[severity]})` : ""}
          </button>
        ))}
      </motion.div>

      {loading && (
        <div className="glass-card p-8 flex items-center gap-3 text-gray-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Loading findings from OBSIDIAN backend...
        </div>
      )}

      {error && (
        <div className="glass-card p-6 border-red-500/30 text-sm text-red-200">
          {error}
        </div>
      )}

      {!loading && !error && findings.length === 0 && (
        <div className="glass-card p-8 text-sm text-gray-400">
          No findings are stored yet. Install the GitHub App, authorize repositories, and let the webhook pipeline process an event.
        </div>
      )}

      <div className="space-y-2">
        {findings.map((finding) => {
          const isOpen = expanded.has(finding.id);
          return (
            <motion.div key={finding.id} variants={itemVariants} className="glass-card overflow-hidden">
              <button
                onClick={() => toggle(finding.id)}
                className="w-full p-4 flex items-center gap-4 text-left hover:bg-white/[0.02] transition-colors"
              >
                <AlertTriangle className={cn("w-5 h-5 flex-shrink-0", severityColor(finding.severity))} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={severityBadge(finding.severity)}>{finding.severity}</span>
                    <h3 className="text-sm font-medium text-gray-200 truncate">{finding.title}</h3>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                    {finding.file_path && (
                      <span className="flex items-center gap-1 font-mono">
                        <FileCode className="w-3 h-3" />
                        {finding.file_path}
                        {finding.line_start ? `:${finding.line_start}` : ""}
                      </span>
                    )}
                    {finding.cwe_id && <span className="text-cyber-cyan">{finding.cwe_id}</span>}
                    <span className="flex items-center gap-1">
                      <Bot className="w-3 h-3" />
                      {finding.agent_name}
                    </span>
                  </div>
                </div>
                <div className="text-xs font-mono text-gray-500">
                  {(finding.confidence * 100).toFixed(0)}%
                </div>
                {isOpen ? (
                  <ChevronUp className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                )}
              </button>

              {isOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="px-4 pb-4 border-t border-white/5"
                >
                  <div className="pt-4 space-y-4">
                    <div>
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">Description</h4>
                      <p className="text-sm text-gray-300 leading-relaxed">{finding.description}</p>
                    </div>

                    {finding.code_snippet && (
                      <div>
                        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">Evidence</h4>
                        <pre className="p-3 rounded-lg bg-surface-900 border border-white/5 text-xs font-mono text-gray-300 overflow-x-auto">
                          {finding.code_snippet}
                        </pre>
                      </div>
                    )}

                    {finding.reasoning && (
                      <div>
                        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">Agent Reasoning</h4>
                        <p className="text-sm text-gray-400 italic">{finding.reasoning}</p>
                      </div>
                    )}

                    {finding.recommendation && (
                      <div className="p-3 rounded-lg bg-cyber-green/5 border border-cyber-green/10">
                        <h4 className="text-xs font-semibold text-cyber-green uppercase mb-1 flex items-center gap-1">
                          <Lightbulb className="w-3 h-3" /> Recommendation
                        </h4>
                        <p className="text-sm text-gray-300">{finding.recommendation}</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
