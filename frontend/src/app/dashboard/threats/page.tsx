"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Shield,
  FileCode,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Bot,
  Lightbulb,
} from "lucide-react";
import { cn, severityBadge, severityColor } from "@/lib/utils";
import type { Finding } from "@/lib/api";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

// Demo findings for the threats view
const demoFindings: Finding[] = [
  {
    id: "f1",
    scan_id: "scan-1",
    title: "SQL Injection in User Authentication",
    description:
      "The login endpoint concatenates user input directly into SQL queries without parameterization, allowing an attacker to bypass authentication or extract sensitive data.",
    severity: "critical",
    category: "vulnerability",
    confidence: 0.95,
    file_path: "src/auth/login_handler.py",
    line_start: 42,
    line_end: 47,
    code_snippet:
      'query = f"SELECT * FROM users WHERE username=\'{username}\' AND password=\'{password}\'"',
    cwe_id: "CWE-89",
    cve_id: null,
    owasp_category: "A03:2021 Injection",
    mitre_technique: "T1190",
    agent_name: "code_intelligence",
    reasoning:
      "Direct string interpolation of user input into SQL query without any sanitization or parameterized query usage. This is a textbook SQL injection vulnerability.",
    recommendation:
      "Use parameterized queries with SQLAlchemy ORM or prepared statements. Example: session.query(User).filter_by(username=username).first()",
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
  {
    id: "f2",
    scan_id: "scan-1",
    title: "Hardcoded AWS Secret Access Key",
    description:
      "AWS Secret Access Key found hardcoded in configuration file. This credential provides programmatic access to AWS services.",
    severity: "critical",
    category: "secret",
    confidence: 0.98,
    file_path: "config/aws_config.py",
    line_start: 15,
    line_end: 15,
    code_snippet: 'AWS_SECRET_KEY = "AKIA[REDACTED]..."',
    cwe_id: "CWE-798",
    cve_id: null,
    owasp_category: null,
    mitre_technique: "T1078",
    agent_name: "secrets_detection",
    reasoning:
      "High-entropy string matching AWS Secret Access Key pattern (AKIA prefix). This is a confirmed credential leak.",
    recommendation:
      "Remove the hardcoded key, rotate the credential immediately, and use AWS Secrets Manager or environment variables instead.",
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
  {
    id: "f3",
    scan_id: "scan-1",
    title: "Missing Authorization Check on Admin Endpoint",
    description:
      "The /api/admin/users endpoint does not verify the caller has admin privileges before returning the full user list.",
    severity: "high",
    category: "vulnerability",
    confidence: 0.88,
    file_path: "src/api/admin_routes.py",
    line_start: 28,
    line_end: 35,
    code_snippet: "@app.get('/api/admin/users')\nasync def list_users():\n    return db.query(User).all()",
    cwe_id: "CWE-862",
    cve_id: null,
    owasp_category: "A01:2021 Broken Access Control",
    mitre_technique: null,
    agent_name: "api_security",
    reasoning:
      "No authentication decorator or middleware protecting admin endpoint. Any authenticated user can access the full user list.",
    recommendation:
      "Add @require_admin decorator and verify user role before processing the request.",
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
  {
    id: "f4",
    scan_id: "scan-1",
    title: "Terraform S3 Bucket Public Access",
    description:
      "S3 bucket is configured with public read access, potentially exposing sensitive data to the internet.",
    severity: "high",
    category: "misconfiguration",
    confidence: 0.92,
    file_path: "terraform/storage.tf",
    line_start: 12,
    line_end: 18,
    code_snippet: 'acl = "public-read"',
    cwe_id: "CWE-732",
    cve_id: null,
    owasp_category: "A05:2021 Security Misconfiguration",
    mitre_technique: null,
    agent_name: "cloud_security",
    reasoning:
      "S3 bucket ACL set to public-read without explicit justification. Combined with no S3 Block Public Access settings.",
    recommendation:
      'Set acl = "private" and enable S3 Block Public Access at the account and bucket level.',
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
  {
    id: "f5",
    scan_id: "scan-1",
    title: "Race Condition in Payment Processing",
    description:
      "The payment deduction and balance check are not atomic, allowing a user to submit concurrent requests to overdraw their balance.",
    severity: "high",
    category: "logic_error",
    confidence: 0.72,
    file_path: "src/payments/process.py",
    line_start: 89,
    line_end: 102,
    code_snippet: null,
    cwe_id: "CWE-362",
    cve_id: null,
    owasp_category: null,
    mitre_technique: null,
    agent_name: "business_logic",
    reasoning:
      "Balance check (read) and deduction (write) are separate DB operations without a lock or transaction. TOCTOU race condition.",
    recommendation:
      "Use SELECT ... FOR UPDATE or a serializable transaction to make balance check + deduction atomic.",
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
  {
    id: "f6",
    scan_id: "scan-1",
    title: "Docker Container Running as Root",
    description:
      "Dockerfile does not specify a non-root USER directive. The application will run as root inside the container.",
    severity: "medium",
    category: "misconfiguration",
    confidence: 0.90,
    file_path: "Dockerfile",
    line_start: 1,
    line_end: 12,
    code_snippet: null,
    cwe_id: "CWE-250",
    cve_id: null,
    owasp_category: null,
    mitre_technique: null,
    agent_name: "container_security",
    reasoning:
      "No USER directive found in Dockerfile. Container processes will run with UID 0 (root).",
    recommendation:
      "Add a non-root user: RUN addgroup --system app && adduser --system --group app\nUSER app",
    citations: null,
    is_fixed: false,
    is_false_positive: false,
    created_at: new Date().toISOString(),
  },
];

export default function ThreatsPage() {
  const [findings, setFindings] = useState<Finding[]>(demoFindings);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filterSeverity, setFilterSeverity] = useState("");

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filtered = filterSeverity
    ? findings.filter((f) => f.severity === filterSeverity)
    : findings;

  const severityCounts = findings.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-xl font-bold text-gray-100">Threat Findings</h1>
        <p className="text-sm text-gray-500 mt-1">
          {findings.length} findings across all scans
        </p>
      </motion.div>

      {/* Severity Filters */}
      <motion.div
        variants={itemVariants}
        className="flex items-center gap-2 flex-wrap"
      >
        <button
          onClick={() => setFilterSeverity("")}
          className={cn(
            "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            !filterSeverity
              ? "bg-white/10 text-gray-200"
              : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
          )}
        >
          All ({findings.length})
        </button>
        {["critical", "high", "medium", "low"].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilterSeverity(sev)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              filterSeverity === sev
                ? severityBadge(sev)
                : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
            )}
          >
            {sev.charAt(0).toUpperCase() + sev.slice(1)} (
            {severityCounts[sev] || 0})
          </button>
        ))}
      </motion.div>

      {/* Findings List */}
      <div className="space-y-2">
        {filtered.map((finding) => {
          const isOpen = expanded.has(finding.id);
          return (
            <motion.div
              key={finding.id}
              variants={itemVariants}
              className="glass-card overflow-hidden"
            >
              {/* Header Row */}
              <button
                onClick={() => toggle(finding.id)}
                className="w-full p-4 flex items-center gap-4 text-left hover:bg-white/[0.02] transition-colors"
              >
                <AlertTriangle
                  className={cn("w-5 h-5 flex-shrink-0", severityColor(finding.severity))}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={severityBadge(finding.severity)}>
                      {finding.severity}
                    </span>
                    <h3 className="text-sm font-medium text-gray-200 truncate">
                      {finding.title}
                    </h3>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                    {finding.file_path && (
                      <span className="flex items-center gap-1 font-mono">
                        <FileCode className="w-3 h-3" />
                        {finding.file_path}
                        {finding.line_start && `:${finding.line_start}`}
                      </span>
                    )}
                    {finding.cwe_id && (
                      <span className="text-cyber-cyan">{finding.cwe_id}</span>
                    )}
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

              {/* Expanded Details */}
              {isOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="px-4 pb-4 border-t border-white/5"
                >
                  <div className="pt-4 space-y-4">
                    {/* Description */}
                    <div>
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">
                        Description
                      </h4>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {finding.description}
                      </p>
                    </div>

                    {/* Code Snippet */}
                    {finding.code_snippet && (
                      <div>
                        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">
                          Vulnerable Code
                        </h4>
                        <pre className="p-3 rounded-lg bg-surface-900 border border-white/5 text-xs font-mono text-gray-300 overflow-x-auto">
                          {finding.code_snippet}
                        </pre>
                      </div>
                    )}

                    {/* Reasoning */}
                    {finding.reasoning && (
                      <div>
                        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1 flex items-center gap-1">
                          <Brain className="w-3 h-3" /> Agent Reasoning
                        </h4>
                        <p className="text-sm text-gray-400 italic">
                          {finding.reasoning}
                        </p>
                      </div>
                    )}

                    {/* Recommendation */}
                    {finding.recommendation && (
                      <div className="p-3 rounded-lg bg-cyber-green/5 border border-cyber-green/10">
                        <h4 className="text-xs font-semibold text-cyber-green uppercase mb-1 flex items-center gap-1">
                          <Lightbulb className="w-3 h-3" /> Recommendation
                        </h4>
                        <p className="text-sm text-gray-300">
                          {finding.recommendation}
                        </p>
                      </div>
                    )}

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2">
                      {finding.owasp_category && (
                        <span className="px-2 py-1 rounded text-[10px] bg-orange-500/10 text-orange-400 border border-orange-500/20">
                          {finding.owasp_category}
                        </span>
                      )}
                      {finding.mitre_technique && (
                        <span className="px-2 py-1 rounded text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20">
                          MITRE {finding.mitre_technique}
                        </span>
                      )}
                      {finding.cwe_id && (
                        <span className="px-2 py-1 rounded text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                          {finding.cwe_id}
                        </span>
                      )}
                    </div>
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

function Brain(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396" />
      <path d="M19.938 10.5a4 4 0 0 1 .585.396" />
      <path d="M6 18a4 4 0 0 1-1.967-.516" />
      <path d="M19.967 17.484A4 4 0 0 1 18 18" />
    </svg>
  );
}
